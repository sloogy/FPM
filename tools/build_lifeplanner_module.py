#!/usr/bin/env python3
"""Build a LifePlanner .lpmodule from a gated FPM runtime artifact.

The tool deliberately does *not* build FPM itself. Signed modules may use a
verified runtime attestation. Explicit ``--allow-unsigned`` builds package the
already-gated CI runtime without keys; those archives stay visibly unsigned
and are accepted by LifePlanner/LiveManager only after manual confirmation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_VERSION
from tools.release_signing import (
    key_id,
    public_key_b64_from_private,
    sign_b64,
    tree_sha256,
)
from tools.runtime_artifact import verify_attestation

PLATFORM_ASSET_SUFFIX = {
    "windows-x86_64": "Windows_x86_64",
    "linux-x86_64": "Linux_x86_64",
}


def canonical_json(data: dict) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def module_asset_name(module_id: str, version: str, platform: str) -> str:
    suffix = PLATFORM_ASSET_SUFFIX[platform]
    return f"{module_id}_{version}_{suffix}.lpmodule"


def _module_manifest() -> dict:
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    if manifest.get("version") != APP_VERSION:
        raise ValueError(
            f"module.json version mismatch: {manifest.get('version')} != {APP_VERSION}; "
            "run tools/sync_version.py"
        )
    return manifest


def _validate_runtime(runtime_dir: Path, runtime_name: str) -> Path:
    if (
        not runtime_name
        or Path(runtime_name).name != runtime_name
        or "\\" in runtime_name
        or ":" in runtime_name
    ):
        raise ValueError("runtime name must be a simple directory name")
    runtime = runtime_dir.resolve()
    if not runtime.is_dir():
        raise ValueError(f"runtime directory missing: {runtime}")
    return runtime


def _grant_runtime_execute_bit(payload: Path, manifest: dict, platform: str) -> None:
    """Make the declared runtime executable inside the payload.

    CI fetches the gated runtime with actions/download-artifact, which does not
    preserve Unix permissions. Without this the published Linux .lpmodule
    records the binary as 0644 and the installed module refuses to start with
    "[Errno 13] Keine Berechtigung". Read bits are mirrored into execute so the
    umask still applies and setuid/setgid/sticky are never introduced.
    """
    key = "windows_executable" if platform.startswith("windows") else "linux_executable"
    relative = str(manifest.get(key, "")).strip()
    if not relative:
        return
    target = payload / Path(relative)
    if not target.is_file():
        raise ValueError(f"declared {key} missing in payload: {relative}")
    mode = stat.S_IMODE(target.stat().st_mode)
    target.chmod(mode | ((mode & 0o444) >> 2))


def _write_module(
    *,
    manifest: dict,
    runtime: Path,
    runtime_name: str,
    platform: str,
    source_artifact: dict,
    output: Path,
    requires_host: str,
    private_key_b64: str | None,
    public_key_b64: str | None,
    release_tag: str | None = None,
) -> Path:
    with tempfile.TemporaryDirectory(prefix="lpmodule-") as temp_name:
        payload = Path(temp_name) / "payload"
        payload.mkdir()
        shutil.copy2(ROOT / "module.json", payload / "module.json")
        shutil.copytree(runtime, payload / runtime_name)
        _grant_runtime_execute_bit(payload, manifest, platform)

        metadata = {
            "schema": "lifeplanner.component.v1",
            "id": manifest["id"],
            "name": manifest.get("name", manifest["id"]),
            "version": manifest["version"],
            "kind": "module",
            "requires_host": requires_host,
            "description": manifest.get("description", ""),
            "platforms": [platform],
            "payload_sha256": tree_sha256(payload),
            "source_artifact": source_artifact,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if public_key_b64:
            metadata["signing_key_id"] = key_id(public_key_b64)
        if release_tag:
            metadata["release_tag"] = release_tag
        metadata_bytes = canonical_json(metadata)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        with zipfile.ZipFile(
            output, "w", zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.writestr("component.json", metadata_bytes)
            if private_key_b64:
                archive.writestr(
                    "component.json.sig", sign_b64(metadata_bytes, private_key_b64)
                )
            for path in sorted(
                payload.rglob("*"), key=lambda p: p.relative_to(payload).as_posix()
            ):
                if path.is_file():
                    archive.write(path, Path("payload") / path.relative_to(payload))

    return output


def build_module(
    *,
    runtime_dir: Path,
    runtime_name: str,
    platform: str,
    artifact_manifest: Path,
    artifact_signature: Path,
    public_key_b64: str,
    output: Path,
    requires_host: str,
    private_key_b64: str | None,
) -> Path:
    if platform not in PLATFORM_ASSET_SUFFIX:
        raise ValueError(f"unsupported platform: {platform}")
    runtime = _validate_runtime(runtime_dir, runtime_name)
    manifest = _module_manifest()

    artifact = verify_attestation(
        runtime_dir=runtime_dir,
        manifest_path=artifact_manifest,
        signature_path=artifact_signature,
        public_key_b64=public_key_b64,
        expected_platform=platform,
        expected_version=APP_VERSION,
    )

    if private_key_b64:
        signer_public = public_key_b64_from_private(private_key_b64)
        if signer_public != public_key_b64.strip():
            raise ValueError(
                "module signing key does not match the trusted runtime-artifact release key"
            )

    return _write_module(
        manifest=manifest,
        runtime=runtime,
        runtime_name=runtime_name,
        platform=platform,
        source_artifact={
            "schema": artifact["schema"],
            "tree_sha256": artifact["tree_sha256"],
            "signing_key_id": artifact["signing_key_id"],
            "platform": artifact["platform"],
        },
        output=output,
        requires_host=requires_host,
        private_key_b64=private_key_b64,
        public_key_b64=public_key_b64,
    )


def build_unsigned_release_module(
    *,
    runtime_dir: Path,
    runtime_name: str,
    platform: str,
    release_tag: str,
    output: Path,
    requires_host: str,
) -> Path:
    """Package a gated tagged runtime without creating or requiring keys."""
    if platform not in PLATFORM_ASSET_SUFFIX:
        raise ValueError(f"unsupported platform: {platform}")
    expected_tag = f"v{APP_VERSION}"
    valid_rc = re.fullmatch(rf"{re.escape(expected_tag)}-rc\.[1-9][0-9]*", release_tag)
    if release_tag != expected_tag and not valid_rc:
        raise ValueError(
            f"unsigned module builds require {expected_tag} or {expected_tag}-rc.N, "
            f"got: {release_tag}"
        )
    runtime = _validate_runtime(runtime_dir, runtime_name)
    manifest = _module_manifest()
    return _write_module(
        manifest=manifest,
        runtime=runtime,
        runtime_name=runtime_name,
        platform=platform,
        source_artifact={
            "schema": "fpm.runtime-artifact.unsigned-release.v1",
            "tree_sha256": tree_sha256(runtime),
            "platform": platform,
            "release_tag": release_tag,
        },
        output=output,
        requires_host=requires_host,
        private_key_b64=None,
        public_key_b64=None,
        release_tag=release_tag,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--runtime-name", required=True)
    parser.add_argument(
        "--platform", choices=sorted(PLATFORM_ASSET_SUFFIX), required=True
    )
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--artifact-signature", type=Path)
    parser.add_argument("--public-key-file", type=Path)
    parser.add_argument("--release-tag")
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument("--output", type=Path)
    output_group.add_argument("--output-dir", type=Path)
    parser.add_argument("--requires-host", default=">=0.5.0")
    parser.add_argument("--allow-unsigned", action="store_true")
    args = parser.parse_args()

    try:
        manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
        public_key_b64 = None
        key = None
        if args.allow_unsigned:
            if not args.release_tag:
                raise ValueError("--allow-unsigned requires --release-tag")
            if any(
                (args.artifact_manifest, args.artifact_signature, args.public_key_file)
            ):
                raise ValueError(
                    "unsigned release mode must not receive attestation or key arguments"
                )
        else:
            if args.release_tag:
                raise ValueError("--release-tag is only valid with --allow-unsigned")
            if not all(
                (args.artifact_manifest, args.artifact_signature, args.public_key_file)
            ):
                raise ValueError(
                    "signed runtime mode requires artifact manifest, signature and public key"
                )
            public_key_b64 = args.public_key_file.read_text(encoding="ascii").strip()
            key = (
                os.environ.get("LIFEPLANNER_UPDATE_PRIVATE_KEY_B64", "").strip() or None
            )
            if not key:
                raise ValueError(
                    "LIFEPLANNER_UPDATE_PRIVATE_KEY_B64 missing; release modules must be signed"
                )
        if args.output:
            output = args.output
        else:
            output = args.output_dir / module_asset_name(
                manifest["id"], manifest["version"], args.platform
            )
        if args.allow_unsigned:
            built = build_unsigned_release_module(
                runtime_dir=args.runtime_dir,
                runtime_name=args.runtime_name,
                platform=args.platform,
                release_tag=args.release_tag,
                output=output,
                requires_host=args.requires_host,
            )
        else:
            built = build_module(
                runtime_dir=args.runtime_dir,
                runtime_name=args.runtime_name,
                platform=args.platform,
                artifact_manifest=args.artifact_manifest,
                artifact_signature=args.artifact_signature,
                public_key_b64=public_key_b64,
                output=output,
                requires_host=args.requires_host,
                private_key_b64=key,
            )
        print(built)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"lifeplanner module build: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
