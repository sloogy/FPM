#!/usr/bin/env python3
"""Create and verify signed attestations for already-gated runtime bundles."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION  # noqa: E402
from tools.release_signing import (  # noqa: E402
    key_id,
    public_key_b64_from_private,
    sign_b64,
    tree_sha256,
    verify_b64,
)

SCHEMA = "fpm.runtime-artifact.v1"
PLATFORMS = {"windows-x86_64", "linux-x86_64"}


def canonical_json(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def locate_runtime(search_root: Path, binary_name: str) -> Path:
    search_root = search_root.resolve()
    if not search_root.is_dir():
        raise ValueError(f"search root missing: {search_root}")
    direct = search_root / binary_name
    if direct.is_file():
        return search_root
    candidates = sorted(path.parent for path in search_root.rglob(binary_name) if path.is_file())
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one {binary_name} below {search_root}, found {len(candidates)}"
        )
    return candidates[0]


def create_attestation(*, runtime_dir: Path, platform: str, private_key_b64: str) -> tuple[dict, bytes, str]:
    runtime_dir = runtime_dir.resolve()
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    if not runtime_dir.is_dir():
        raise ValueError(f"runtime directory missing: {runtime_dir}")
    public_b64 = public_key_b64_from_private(private_key_b64)
    data = {
        "schema": SCHEMA,
        "app": APP_NAME,
        "version": APP_VERSION,
        "platform": platform,
        "runtime_dir_name": runtime_dir.name,
        "tree_sha256": tree_sha256(runtime_dir),
        "signing_key_id": key_id(public_b64),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    payload = canonical_json(data)
    return data, sign_b64(payload, private_key_b64), public_b64


def verify_attestation(
    *,
    runtime_dir: Path,
    manifest_path: Path,
    signature_path: Path,
    public_key_b64: str,
    expected_platform: str | None = None,
    expected_version: str | None = None,
) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    verify_b64(manifest_bytes, signature_path.read_bytes(), public_key_b64)
    try:
        data = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("runtime artifact manifest is not valid UTF-8 JSON") from exc
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unexpected runtime artifact schema: {data.get('schema')!r}")
    if data.get("app") != APP_NAME:
        raise ValueError("runtime artifact app name does not match this source tree")
    if data.get("version") != (expected_version or APP_VERSION):
        raise ValueError(
            f"runtime artifact version mismatch: {data.get('version')} != {expected_version or APP_VERSION}"
        )
    if expected_platform and data.get("platform") != expected_platform:
        raise ValueError(
            f"runtime artifact platform mismatch: {data.get('platform')} != {expected_platform}"
        )
    expected_key = key_id(public_key_b64)
    if data.get("signing_key_id") != expected_key:
        raise ValueError("runtime artifact was not signed by the expected release key")
    actual_tree = tree_sha256(runtime_dir.resolve())
    if data.get("tree_sha256") != actual_tree:
        raise ValueError("runtime artifact tree hash mismatch; artifact was modified after signing")
    return data


def _private_key_from_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"required signing key environment variable is missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    locate = sub.add_parser("locate")
    locate.add_argument("--search-root", type=Path, required=True)
    locate.add_argument("--binary", required=True)

    sign = sub.add_parser("sign")
    sign.add_argument("--runtime-dir", type=Path, required=True)
    sign.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    sign.add_argument("--manifest", type=Path, required=True)
    sign.add_argument("--signature", type=Path, required=True)
    sign.add_argument("--public-key-out", type=Path, required=True)
    sign.add_argument("--private-key-env", default="LIFEPLANNER_UPDATE_PRIVATE_KEY_B64")

    verify = sub.add_parser("verify")
    verify.add_argument("--runtime-dir", type=Path, required=True)
    verify.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--signature", type=Path, required=True)
    verify.add_argument("--public-key-file", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "locate":
            print(locate_runtime(args.search_root, args.binary))
            return 0
        if args.command == "sign":
            _data, signature, public_b64 = create_attestation(
                runtime_dir=args.runtime_dir,
                platform=args.platform,
                private_key_b64=_private_key_from_env(args.private_key_env),
            )
            manifest_bytes = canonical_json(_data)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.signature.parent.mkdir(parents=True, exist_ok=True)
            args.public_key_out.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_bytes(manifest_bytes)
            args.signature.write_bytes(signature)
            args.public_key_out.write_text(public_b64 + "\n", encoding="ascii")
            print(args.manifest)
            return 0
        if args.command == "verify":
            verify_attestation(
                runtime_dir=args.runtime_dir,
                manifest_path=args.manifest,
                signature_path=args.signature,
                public_key_b64=args.public_key_file.read_text(encoding="ascii").strip(),
                expected_platform=args.platform,
            )
            print("runtime artifact signature and tree hash: OK")
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"runtime artifact: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
