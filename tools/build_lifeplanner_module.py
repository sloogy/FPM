#!/usr/bin/env python3
"""Build a LifePlanner .lpmodule from a verified, signed FPM runtime artifact.

The tool deliberately does *not* build FPM itself. It only packages an already
gated runtime bundle whose signed attestation is verified before any module is
created. This keeps the LifePlanner module on the same enterprise release path
as the standalone application.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_VERSION  # noqa: E402
from tools.release_signing import (  # noqa: E402
    key_id,
    public_key_b64_from_private,
    sign_b64,
    tree_sha256,
)
from tools.runtime_artifact import verify_attestation  # noqa: E402

PLATFORM_ASSET_SUFFIX = {
    "windows-x86_64": "Windows_x86_64",
    "linux-x86_64": "Linux_x86_64",
}


def canonical_json(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def module_asset_name(module_id: str, version: str, platform: str) -> str:
    suffix = PLATFORM_ASSET_SUFFIX[platform]
    return f"{module_id}_{version}_{suffix}.lpmodule"


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
    if (
        not runtime_name
        or Path(runtime_name).name != runtime_name
        or "\\" in runtime_name
        or ":" in runtime_name
    ):
        raise ValueError("runtime name must be a simple directory name")
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    if manifest.get("version") != APP_VERSION:
        raise ValueError(
            f"module.json version mismatch: {manifest.get('version')} != {APP_VERSION}; run tools/sync_version.py"
        )

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
            raise ValueError("module signing key does not match the trusted runtime-artifact release key")

    runtime = runtime_dir.resolve()
    if not runtime.is_dir():
        raise ValueError(f"runtime directory missing: {runtime}")

    with tempfile.TemporaryDirectory(prefix="lpmodule-") as temp_name:
        payload = Path(temp_name) / "payload"
        payload.mkdir()
        shutil.copy2(ROOT / "module.json", payload / "module.json")
        shutil.copytree(runtime, payload / runtime_name)

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
            "source_artifact": {
                "schema": artifact["schema"],
                "tree_sha256": artifact["tree_sha256"],
                "signing_key_id": artifact["signing_key_id"],
                "platform": artifact["platform"],
            },
            "signing_key_id": key_id(public_key_b64),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        metadata_bytes = canonical_json(metadata)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("component.json", metadata_bytes)
            if private_key_b64:
                archive.writestr("component.json.sig", sign_b64(metadata_bytes, private_key_b64))
            for path in sorted(payload.rglob("*"), key=lambda p: p.relative_to(payload).as_posix()):
                if path.is_file():
                    archive.write(path, Path("payload") / path.relative_to(payload))

    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--runtime-name", required=True)
    parser.add_argument("--platform", choices=sorted(PLATFORM_ASSET_SUFFIX), required=True)
    parser.add_argument("--artifact-manifest", type=Path, required=True)
    parser.add_argument("--artifact-signature", type=Path, required=True)
    parser.add_argument("--public-key-file", type=Path, required=True)
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument("--output", type=Path)
    output_group.add_argument("--output-dir", type=Path)
    parser.add_argument("--requires-host", default=">=0.5.0")
    parser.add_argument("--allow-unsigned", action="store_true")
    args = parser.parse_args()

    try:
        manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
        public_key_b64 = args.public_key_file.read_text(encoding="ascii").strip()
        key = os.environ.get("LIFEPLANNER_UPDATE_PRIVATE_KEY_B64", "").strip() or None
        if not key and not args.allow_unsigned:
            raise ValueError(
                "LIFEPLANNER_UPDATE_PRIVATE_KEY_B64 missing; release modules must be signed"
            )
        if args.output:
            output = args.output
        else:
            output = args.output_dir / module_asset_name(manifest["id"], manifest["version"], args.platform)
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
