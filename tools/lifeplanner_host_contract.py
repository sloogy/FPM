#!/usr/bin/env python3
"""Reference verifier/installer for the LifePlanner module contract used by CI.

This is not a replacement for the LifePlanner host. It is a fail-closed contract
implementation that proves FPM's .lpmodule can be verified and installed by a
host. Signed packages require the public release key; explicitly allowed
unsigned releases follow LifePlanner/LiveManager's manual-confirmation path.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.release_signing import tree_sha256, verify_b64

COMPONENT_SCHEMA = "lifeplanner.component.v1"
MODULE_SCHEMAS = {"lifeplanner.module.v1", "lifeplanner.module.v2"}


def _validate_member(name: str, info: zipfile.ZipInfo) -> None:
    if "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe archive path: {name!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not p.parts or ":" in p.parts[0]:
        raise ValueError(f"unsafe archive path: {name!r}")
    unix_mode = info.external_attr >> 16
    if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
        raise ValueError(f"symbolic links are not allowed in module archives: {name!r}")


def _read_required(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        return archive.read(name)
    except KeyError as exc:
        raise ValueError(f"required module entry missing: {name}") from exc


def verify_module(
    module_path: Path,
    *,
    public_key_b64: str | None = None,
    allow_unsigned: bool = False,
    expected_id: str | None = None,
    expected_version: str | None = None,
    expected_platform: str | None = None,
) -> dict:
    with zipfile.ZipFile(module_path) as archive:
        for info in archive.infolist():
            _validate_member(info.filename, info)
        component_bytes = _read_required(archive, "component.json")
        try:
            signature_bytes = archive.read("component.json.sig")
        except KeyError:
            signature_bytes = None
        if signature_bytes is None:
            if not allow_unsigned:
                raise ValueError("required module entry missing: component.json.sig")
        else:
            if not public_key_b64:
                raise ValueError("signed module verification requires a public key")
            verify_b64(component_bytes, signature_bytes, public_key_b64)
        try:
            component = json.loads(component_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError("component.json is not valid UTF-8 JSON") from exc
        if component.get("schema") != COMPONENT_SCHEMA:
            raise ValueError(f"unsupported component schema: {component.get('schema')!r}")
        if component.get("kind") != "module":
            raise ValueError("component kind is not 'module'")
        if expected_id and component.get("id") != expected_id:
            raise ValueError("module id mismatch")
        if expected_version and component.get("version") != expected_version:
            raise ValueError("module version mismatch")
        platforms = component.get("platforms")
        if not isinstance(platforms, list) or len(platforms) != 1:
            raise ValueError("component must declare exactly one platform")
        if expected_platform and platforms != [expected_platform]:
            raise ValueError("module platform mismatch")

        with tempfile.TemporaryDirectory(prefix="lifeplanner-verify-") as temp_name:
            temp_root = Path(temp_name)
            payload_root = temp_root / "payload"
            for info in archive.infolist():
                if not info.filename.startswith("payload/") or info.is_dir():
                    continue
                rel = PurePosixPath(info.filename).relative_to("payload")
                target = payload_root.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            if not payload_root.is_dir():
                raise ValueError("module payload is missing")
            actual_hash = tree_sha256(payload_root)
            if actual_hash != component.get("payload_sha256"):
                raise ValueError("module payload hash mismatch; archive was modified")
            module_manifest_path = payload_root / "module.json"
            if not module_manifest_path.is_file():
                raise ValueError("payload/module.json is missing")
            module_manifest = json.loads(module_manifest_path.read_text(encoding="utf-8"))
            module_schema = module_manifest.get("schema")
            if module_schema not in MODULE_SCHEMAS:
                raise ValueError("payload module manifest schema mismatch")
            if module_schema == "lifeplanner.module.v2":
                manifest_requires_host = str(module_manifest.get("requires_host", "")).strip()
                if not manifest_requires_host:
                    raise ValueError("payload module.v2 manifest requires requires_host")
                component_requires_host = str(component.get("requires_host", "")).strip()
                if component_requires_host != manifest_requires_host:
                    raise ValueError(
                        "component requires_host does not match payload module manifest"
                    )
            if module_manifest.get("id") != component.get("id"):
                raise ValueError("payload module id does not match component metadata")
            if module_manifest.get("version") != component.get("version"):
                raise ValueError("payload module version does not match component metadata")
            platform = platforms[0]
            exe_key = "windows_executable" if platform.startswith("windows-") else "linux_executable"
            executable = module_manifest.get(exe_key)
            if not isinstance(executable, str) or not executable:
                raise ValueError(f"module manifest does not declare {exe_key}")
            exe_path = payload_root.joinpath(*PurePosixPath(executable).parts)
            if not exe_path.is_file():
                raise ValueError(f"declared module executable is missing: {executable}")

        return component


def install_module(
    module_path: Path,
    *,
    install_root: Path,
    public_key_b64: str | None = None,
    allow_unsigned: bool = False,
    expected_id: str | None = None,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    replace: bool = False,
) -> Path:
    component = verify_module(
        module_path,
        public_key_b64=public_key_b64,
        allow_unsigned=allow_unsigned,
        expected_id=expected_id,
        expected_version=expected_version,
        expected_platform=expected_platform,
    )
    target = install_root.resolve() / component["id"] / component["version"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not replace:
        raise ValueError(f"module version already installed: {target}")

    with tempfile.TemporaryDirectory(prefix="lifeplanner-install-", dir=target.parent) as temp_name:
        staging = Path(temp_name) / "staging"
        staging.mkdir()
        with zipfile.ZipFile(module_path) as archive:
            for info in archive.infolist():
                _validate_member(info.filename, info)
                if not info.filename.startswith("payload/") or info.is_dir():
                    continue
                rel = PurePosixPath(info.filename).relative_to("payload")
                dest = staging.joinpath(*rel.parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                unix_mode = info.external_attr >> 16
                if unix_mode:
                    try:
                        os.chmod(dest, unix_mode & 0o777)
                    except OSError:
                        pass
        if tree_sha256(staging) != component["payload_sha256"]:
            raise ValueError("staging payload hash mismatch")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", type=Path)
    parser.add_argument("--public-key-file", type=Path)
    parser.add_argument("--allow-unsigned", action="store_true")
    parser.add_argument("--platform")
    parser.add_argument("--id")
    parser.add_argument("--version")
    parser.add_argument("--install-root", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        public_key_b64 = (
            args.public_key_file.read_text(encoding="ascii").strip()
            if args.public_key_file
            else None
        )
        if not public_key_b64 and not args.allow_unsigned:
            raise ValueError("--public-key-file is required unless --allow-unsigned is set")
        if args.install_root:
            target = install_module(
                args.module,
                install_root=args.install_root,
                public_key_b64=public_key_b64,
                allow_unsigned=args.allow_unsigned,
                expected_id=args.id,
                expected_version=args.version,
                expected_platform=args.platform,
                replace=args.replace,
            )
            print(target)
        else:
            verify_module(
                args.module,
                public_key_b64=public_key_b64,
                allow_unsigned=args.allow_unsigned,
                expected_id=args.id,
                expected_version=args.version,
                expected_platform=args.platform,
            )
            print("LifePlanner module contract: OK")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"LifePlanner host contract: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
