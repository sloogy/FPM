"""v0.3.05 end-to-end LifePlanner release-chain tests."""
from __future__ import annotations

import base64
import json
import stat
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app_info import APP_VERSION
from tools.build_lifeplanner_module import (
    build_module,
    build_unsigned_release_module,
    module_asset_name,
)
from tools.lifeplanner_host_contract import install_module, verify_module
from tools.runtime_artifact import canonical_json, create_attestation


def _keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return base64.b64encode(private_raw).decode(), base64.b64encode(public_raw).decode()


def _runtime(tmp_path: Path, platform: str) -> Path:
    root = tmp_path / platform / "FountainPenManager"
    (root / "_internal").mkdir(parents=True)
    binary = root / ("FountainPenManager.exe" if platform == "windows-x86_64" else "FountainPenManager")
    binary.write_bytes(b"verified runtime binary\n")
    if platform == "linux-x86_64":
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    (root / "_internal" / "runtime.bin").write_bytes(b"runtime dependency")
    return root


def _attest(tmp_path: Path, runtime: Path, platform: str, private_b64: str):
    manifest = tmp_path / platform / "runtime-artifact.json"
    signature = tmp_path / platform / "runtime-artifact.json.sig"
    data, signature_bytes, public_b64 = create_attestation(
        runtime_dir=runtime,
        platform=platform,
        private_key_b64=private_b64,
    )
    manifest.write_bytes(canonical_json(data))
    signature.write_bytes(signature_bytes)
    return manifest, signature, public_b64


def _build(tmp_path: Path, platform: str, private_b64: str, public_b64: str) -> Path:
    runtime = _runtime(tmp_path, platform)
    manifest, signature, attested_public = _attest(tmp_path, runtime, platform, private_b64)
    assert attested_public == public_b64
    output = tmp_path / "modules" / module_asset_name("fpm", APP_VERSION, platform)
    return build_module(
        runtime_dir=runtime,
        runtime_name="FountainPenManager",
        platform=platform,
        artifact_manifest=manifest,
        artifact_signature=signature,
        public_key_b64=public_b64,
        output=output,
        requires_host=">=0.5.0",
        private_key_b64=private_b64,
    )


@pytest.mark.parametrize("platform", ["windows-x86_64", "linux-x86_64"])
def test_real_module_build_signature_and_host_install(tmp_path, platform):
    private_b64, public_b64 = _keypair()
    module = _build(tmp_path, platform, private_b64, public_b64)
    assert module.name == module_asset_name("fpm", APP_VERSION, platform)

    component = verify_module(
        module,
        public_key_b64=public_b64,
        expected_id="fpm",
        expected_version=APP_VERSION,
        expected_platform=platform,
    )
    assert component["source_artifact"]["platform"] == platform
    assert component["source_artifact"]["tree_sha256"]
    assert component["signing_key_id"] == component["source_artifact"]["signing_key_id"]

    target = install_module(
        module,
        install_root=tmp_path / "host",
        public_key_b64=public_b64,
        expected_id="fpm",
        expected_version=APP_VERSION,
        expected_platform=platform,
    )
    executable = target / "FountainPenManager" / (
        "FountainPenManager.exe" if platform == "windows-x86_64" else "FountainPenManager"
    )
    assert executable.is_file()


@pytest.mark.parametrize("platform", ["windows-x86_64", "linux-x86_64"])
@pytest.mark.parametrize("release_tag", [f"v{APP_VERSION}", f"v{APP_VERSION}-rc.2"])
def test_unsigned_release_module_matches_lifeplanner_manual_install_contract(
    tmp_path, platform, release_tag
):
    runtime = _runtime(tmp_path, platform)
    module = build_unsigned_release_module(
        runtime_dir=runtime,
        runtime_name="FountainPenManager",
        platform=platform,
        release_tag=release_tag,
        output=tmp_path / "modules" / module_asset_name("fpm", APP_VERSION, platform),
        requires_host=">=0.5.0",
    )

    with zipfile.ZipFile(module) as archive:
        assert "component.json.sig" not in archive.namelist()
    with pytest.raises(ValueError, match="component.json.sig"):
        verify_module(module, expected_platform=platform)

    component = verify_module(
        module,
        allow_unsigned=True,
        expected_id="fpm",
        expected_version=APP_VERSION,
        expected_platform=platform,
    )
    assert component["release_tag"] == release_tag
    assert component["source_artifact"]["release_tag"] == release_tag
    assert "signing_key_id" not in component

    target = install_module(
        module,
        install_root=tmp_path / "host-prerelease",
        allow_unsigned=True,
        expected_id="fpm",
        expected_version=APP_VERSION,
        expected_platform=platform,
    )
    executable = target / "FountainPenManager" / (
        "FountainPenManager.exe"
        if platform == "windows-x86_64"
        else "FountainPenManager"
    )
    assert executable.is_file()


def test_unsigned_module_builder_rejects_unversioned_tag(tmp_path):
    runtime = _runtime(tmp_path, "linux-x86_64")
    with pytest.raises(ValueError, match="require.*v0.3.05"):
        build_unsigned_release_module(
            runtime_dir=runtime,
            runtime_name="FountainPenManager",
            platform="linux-x86_64",
            release_tag=f"v{APP_VERSION}-beta.1",
            output=tmp_path / "rejected.lpmodule",
            requires_host=">=0.5.0",
        )


def test_module_build_refuses_runtime_modified_after_attestation(tmp_path):
    private_b64, public_b64 = _keypair()
    platform = "linux-x86_64"
    runtime = _runtime(tmp_path, platform)
    manifest, signature, _ = _attest(tmp_path, runtime, platform, private_b64)
    (runtime / "_internal" / "runtime.bin").write_bytes(b"tampered after signing")

    with pytest.raises(ValueError, match="modified after signing"):
        build_module(
            runtime_dir=runtime,
            runtime_name="FountainPenManager",
            platform=platform,
            artifact_manifest=manifest,
            artifact_signature=signature,
            public_key_b64=public_b64,
            output=tmp_path / "rejected.lpmodule",
            requires_host=">=0.5.0",
            private_key_b64=private_b64,
        )


def _rewrite_zip(source: Path, target: Path, mutate_name: str, mutate) -> None:
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == mutate_name:
                data = mutate(data)
            dst.writestr(info, data)


def test_host_rejects_component_metadata_tampering(tmp_path):
    private_b64, public_b64 = _keypair()
    module = _build(tmp_path, "windows-x86_64", private_b64, public_b64)
    tampered = tmp_path / "tampered-component.lpmodule"

    def mutate(data: bytes) -> bytes:
        obj = json.loads(data)
        obj["version"] = "9.9.9"
        return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()

    _rewrite_zip(module, tampered, "component.json", mutate)
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_module(tampered, public_key_b64=public_b64)


def test_host_rejects_payload_tampering_even_with_untouched_metadata_signature(tmp_path):
    private_b64, public_b64 = _keypair()
    module = _build(tmp_path, "linux-x86_64", private_b64, public_b64)
    tampered = tmp_path / "tampered-payload.lpmodule"
    _rewrite_zip(
        module,
        tampered,
        "payload/FountainPenManager/_internal/runtime.bin",
        lambda _data: b"payload was modified",
    )
    with pytest.raises(ValueError, match="payload hash mismatch"):
        verify_module(tampered, public_key_b64=public_b64)


def test_release_workflow_has_one_publisher_and_no_parallel_module_release():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/windows-release.yml").read_text(encoding="utf-8")
    all_workflows = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / ".github" / "workflows").glob("*.yml")
    )
    assert all_workflows.count("gh release create") == 1
    assert "Build unsigned LifePlanner modules from gated runtimes" in workflow
    assert "lifeplanner_host_contract.py" in workflow
    assert "--output-dir modules" in workflow
    assert "--allow-unsigned" in workflow
    assert "v0.3.05" not in workflow  # tag and asset names must be derived, never hard-coded here
    assert not (root / ".github/workflows/lifeplanner-module-release.yml").exists()


def test_translation_key_is_really_nested_and_runtime_resolvable():
    root = Path(__file__).resolve().parents[1]
    from i18n.translator import Translator

    for lang in ("de", "en", "fr"):
        data = json.loads((root / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert "settings.lifeplanner_central_updater" not in data
        assert data["settings"]["lifeplanner_central_updater"]
        tr = Translator.instance()
        old = tr.language
        try:
            tr.set_language(lang)
            resolved = tr.t("settings.lifeplanner_central_updater")
            assert resolved != "settings.lifeplanner_central_updater"
        finally:
            tr.set_language(old)


def test_host_rejects_path_traversal_and_windows_separator_entries(tmp_path):
    private_b64, public_b64 = _keypair()
    module = _build(tmp_path, "linux-x86_64", private_b64, public_b64)
    hostile = tmp_path / "hostile-path.lpmodule"
    with zipfile.ZipFile(module) as src, zipfile.ZipFile(hostile, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info.filename))
        dst.writestr("payload/../escape.txt", b"escape")
    with pytest.raises(ValueError, match="unsafe archive path"):
        verify_module(hostile, public_key_b64=public_b64)

    hostile_windows = tmp_path / "hostile-windows-path.lpmodule"
    with zipfile.ZipFile(module) as src, zipfile.ZipFile(hostile_windows, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info.filename))
        dst.writestr("payload\\..\\escape.txt", b"escape")
    with pytest.raises(ValueError, match="unsafe archive path"):
        verify_module(hostile_windows, public_key_b64=public_b64)


def test_release_metadata_derives_tag_manifest_and_all_asset_names_from_app_version():
    root = Path(__file__).resolve().parents[1]
    from tools.release_metadata import classify_tag, metadata

    data = metadata()
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    assert manifest["version"] == APP_VERSION
    assert data["app_version"] == APP_VERSION
    assert data["release_tag"] == f"v{APP_VERSION}"
    assert APP_VERSION in data["windows_portable"]
    assert APP_VERSION in data["linux_portable"]
    assert APP_VERSION in data["windows_installer"]
    assert APP_VERSION in data["module_windows"]
    assert APP_VERSION in data["module_linux"]
    assert classify_tag(f"v{APP_VERSION}") == "production"
    assert classify_tag(f"v{APP_VERSION}-rc.1") == "release-candidate"
    assert classify_tag(f"v{APP_VERSION}-rc.27") == "release-candidate"
    for invalid in (
        f"v{APP_VERSION}-rc.0",
        f"v{APP_VERSION}-rc",
        f"v{APP_VERSION}-beta.1",
        "v9.9.9-rc.1",
    ):
        with pytest.raises(ValueError, match="does not match"):
            classify_tag(invalid)
    sync_source = (root / "tools" / "sync_version.py").read_text(encoding="utf-8")
    assert '"module.json": sync_module_manifest(check)' in sync_source


def test_release_candidate_publishes_unsigned_modules_without_update_manifest():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/windows-release.yml").read_text(
        encoding="utf-8"
    )
    assert 'release_metadata.py --validate-tag "$GITHUB_REF_NAME"' in workflow
    assert "Mark all tagged artifacts as unsigned" in workflow
    assert "UNSIGNED TEST BUILD" in workflow
    assert "--prerelease" in workflow
    assert "Build unsigned LifePlanner modules from gated runtimes" in workflow
    assert '--release-tag "$GITHUB_REF_NAME"' in workflow
    assert "Verify and host-install unsigned modules" in workflow
    assert workflow.count("--allow-unsigned") == 4
    assert '--module-windows "modules/${FPM_MODULE_WINDOWS}"' in workflow
    assert '--module-linux "modules/${FPM_MODULE_LINUX}"' in workflow
    assert 'assert "component.json.sig" not in names' in workflow
    assert "test ! -f prerelease_assets/latest.json" in workflow
    production_only = (
        "startsWith(github.ref, 'refs/tags/') && "
        "!contains(github.ref_name, '-')"
    )
    assert workflow.count(production_only) == 0
    assert workflow.count("if: ${{ !contains(github.ref_name, '-') }}") == 3


def test_stable_release_is_explicitly_unsigned_and_keyless():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/windows-release.yml").read_text(
        encoding="utf-8"
    )
    assert "UNSIGNED_RELEASE.txt" in workflow
    assert "UNSIGNED RELEASE" in workflow
    assert 'assert "component.json.sig" not in names' in workflow
    assert "WINDOWS_SIGNING_CERT_BASE64" not in workflow
    assert "WINDOWS_SIGNING_CERT_PASSWORD" not in workflow
    assert "LIFEPLANNER_UPDATE_PRIVATE_KEY_B64" not in workflow
    assert "signtool" not in workflow.lower()
