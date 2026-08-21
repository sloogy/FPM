"""Die Echtheit des Update-Manifests.

Warum es das braucht: ``latest.json`` traegt die SHA256-Werte aller
Release-Artefakte. Bis hierher war das Manifest selbst ungeschuetzt - wer es
austauschen kann, tauscht die Pruefsummen gleich mit, und die ganze Kette haengt
an nichts. Die abgetrennte Signatur ``latest.json.sig`` schliesst das.

Fail-closed ist der Kern: Ohne Schluessel oder Signatur gibt es kein Update.
Ein Fehler, der hier zu einem stillen "dann eben ungeprueft" wird, hebt den
gesamten Schutz auf, ohne dass jemand etwas merkt.
"""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from updater.manifest_signing import (
    ManifestSignatureError,
    PUBLIC_KEY_ENV,
    PUBLIC_KEY_FILENAME,
    SIGNATURE_SUFFIX,
    load_trusted_public_key,
    private_key_from_base64,
    public_key_base64,
    sign_manifest_bytes,
    sign_manifest_file,
    verify_manifest_signature,
)


def _privat_b64(key: Ed25519PrivateKey) -> str:
    raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    return base64.b64encode(raw).decode("ascii")


def _oeffentlich_b64(key) -> str:
    raw = key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


@pytest.fixture()
def schluesselpaar() -> tuple[str, str]:
    """Privater und oeffentlicher Schluessel, beide base64."""
    private = Ed25519PrivateKey.generate()
    return _privat_b64(private), public_key_base64(private)


MANIFEST = json.dumps({"version": "1.0.8", "assets": {}}).encode("utf-8")


# ── Prüfung ─────────────────────────────────────────────────────────────────

def test_eine_echte_signatur_wird_angenommen(schluesselpaar):
    privat, oeffentlich = schluesselpaar
    signatur = sign_manifest_bytes(MANIFEST, private_key_from_base64(privat))
    schluessel = private_key_from_base64(privat).public_key()
    verify_manifest_signature(MANIFEST, signatur, public_key=schluessel)


def test_ein_veraendertes_manifest_faellt_durch(schluesselpaar):
    """Der eigentliche Zweck: eine ausgetauschte Pruefsumme faellt auf."""
    privat, _ = schluesselpaar
    signatur = sign_manifest_bytes(MANIFEST, private_key_from_base64(privat))
    schluessel = private_key_from_base64(privat).public_key()
    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(MANIFEST + b" ", signatur, public_key=schluessel)


def test_eine_fremde_signatur_faellt_durch(schluesselpaar):
    privat, _ = schluesselpaar
    fremd = Ed25519PrivateKey.generate()
    signatur = sign_manifest_bytes(MANIFEST, fremd)
    schluessel = private_key_from_base64(privat).public_key()
    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(MANIFEST, signatur, public_key=schluessel)


@pytest.mark.parametrize(
    "unbrauchbar",
    [b"", b"kein-base64!", b"a" * 200, base64.b64encode(b"zu kurz")],
)
def test_unbrauchbare_signaturen_fallen_durch(schluesselpaar, unbrauchbar):
    privat, _ = schluesselpaar
    schluessel = private_key_from_base64(privat).public_key()
    with pytest.raises(ManifestSignatureError):
        verify_manifest_signature(MANIFEST, unbrauchbar, public_key=schluessel)


# ── Vertrauensanker ─────────────────────────────────────────────────────────

def test_ohne_schluessel_gibt_es_kein_update(monkeypatch, tmp_path):
    """Fail-closed. Ein fehlender Anker darf nicht zu "dann eben ungeprueft"
    werden - das hoebe den Schutz auf, ohne dass jemand etwas merkt."""
    import updater.manifest_signing as signing

    monkeypatch.delenv(PUBLIC_KEY_ENV, raising=False)
    monkeypatch.setattr(signing, "public_key_candidates", lambda: (tmp_path / "fehlt",))
    with pytest.raises(ManifestSignatureError):
        load_trusted_public_key()


def test_der_schluessel_aus_der_umgebung_gilt(monkeypatch, schluesselpaar):
    _, oeffentlich = schluesselpaar
    monkeypatch.setenv(PUBLIC_KEY_ENV, oeffentlich)
    assert _oeffentlich_b64(load_trusted_public_key()) == oeffentlich


def test_der_eingebettete_schluessel_gilt(monkeypatch, tmp_path, schluesselpaar):
    import updater.manifest_signing as signing

    _, oeffentlich = schluesselpaar
    datei = tmp_path / PUBLIC_KEY_FILENAME
    datei.write_text(oeffentlich + "\n", encoding="ascii")
    monkeypatch.delenv(PUBLIC_KEY_ENV, raising=False)
    monkeypatch.setattr(signing, "public_key_candidates", lambda: (datei,))
    assert _oeffentlich_b64(load_trusted_public_key()) == oeffentlich


def test_ein_beschaedigter_anker_wird_nicht_stillschweigend_uebergangen(
    monkeypatch, tmp_path
):
    import updater.manifest_signing as signing

    datei = tmp_path / PUBLIC_KEY_FILENAME
    datei.write_text("keine gueltige base64\n", encoding="ascii")
    monkeypatch.delenv(PUBLIC_KEY_ENV, raising=False)
    monkeypatch.setattr(signing, "public_key_candidates", lambda: (datei,))
    with pytest.raises(ManifestSignatureError):
        load_trusted_public_key()


# ── Signieren im Release ────────────────────────────────────────────────────

def test_signieren_legt_die_datei_daneben(tmp_path, schluesselpaar):
    privat, oeffentlich = schluesselpaar
    manifest = tmp_path / "latest.json"
    manifest.write_bytes(MANIFEST)

    signatur = sign_manifest_file(
        manifest, private_key_b64=privat, expected_public_key_b64=oeffentlich
    )

    assert signatur.name == "latest.json" + SIGNATURE_SUFFIX
    schluessel = private_key_from_base64(privat).public_key()
    verify_manifest_signature(
        manifest.read_bytes(), signatur.read_bytes(), public_key=schluessel
    )


def test_ein_unpassender_privater_schluessel_bricht_den_release_ab(
    tmp_path, schluesselpaar
):
    """Sonst entstuende ein Release, das kein ausgelieferter Client annimmt."""
    _, oeffentlich = schluesselpaar
    fremd_b64 = _privat_b64(Ed25519PrivateKey.generate())

    manifest = tmp_path / "latest.json"
    manifest.write_bytes(MANIFEST)
    with pytest.raises(ManifestSignatureError):
        sign_manifest_file(
            manifest, private_key_b64=fremd_b64, expected_public_key_b64=oeffentlich
        )


# ── Der Weg durch fetch_manifest ────────────────────────────────────────────

def test_fetch_manifest_laedt_und_prueft_die_signatur(monkeypatch, schluesselpaar):
    """Die Verdrahtung: ohne sie nuetzt die beste Pruefung nichts."""
    from updater import common

    privat, oeffentlich = schluesselpaar
    manifest = json.dumps(
        {
            "version": "1.0.8",
            "release_tag": "v1.0.8",
            "channel": "stable",
            "assets": {
                "linux": {
                    "url": "https://example.invalid/a.zip",
                    "sha256": "0" * 64,
                    "type": "portable-zip",
                }
            },
        }
    ).encode("utf-8")
    signatur = sign_manifest_bytes(manifest, private_key_from_base64(privat))
    geladen: list[str] = []

    def gefaelscht(url, **_kwargs):
        geladen.append(url)
        return signatur if url.endswith(SIGNATURE_SUFFIX) else manifest

    monkeypatch.setattr(common, "_fetch_public_bytes", gefaelscht)
    monkeypatch.setenv(PUBLIC_KEY_ENV, oeffentlich)

    ergebnis = common.fetch_manifest("https://example.invalid/latest.json")

    assert ergebnis.version == "1.0.8"
    assert geladen == [
        "https://example.invalid/latest.json",
        "https://example.invalid/latest.json" + SIGNATURE_SUFFIX,
    ]


def test_fetch_manifest_lehnt_ein_manipuliertes_manifest_ab(
    monkeypatch, schluesselpaar
):
    from updater import common

    privat, oeffentlich = schluesselpaar
    echt = json.dumps({"version": "1.0.8", "assets": {}}).encode("utf-8")
    signatur = sign_manifest_bytes(echt, private_key_from_base64(privat))
    manipuliert = json.dumps({"version": "9.9.9", "assets": {}}).encode("utf-8")

    def gefaelscht(url, **_kwargs):
        return signatur if url.endswith(SIGNATURE_SUFFIX) else manipuliert

    monkeypatch.setattr(common, "_fetch_public_bytes", gefaelscht)
    monkeypatch.setenv(PUBLIC_KEY_ENV, oeffentlich)

    with pytest.raises(ManifestSignatureError):
        common.fetch_manifest("https://example.invalid/latest.json")
