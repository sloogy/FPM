"""Der Kontrakt zwischen FPM und BudgetManager.

Warum es diesen Test zusaetzlich zu ``test_budgetmanager_bridge_service`` gibt:
Dort erzeugt FPM seine Testdaten selbst. Dadurch blieb lange unbemerkt, dass
BudgetManager Sparziele als ``fpm.savings-goal.v1`` mit Bindestrich schreibt,
waehrend FPM nur die Unterstrich-Form las - beide Seiten fuer sich gruen, die
Spiegelung kam trotzdem nie an.

Hier stehen darum **Proben aus der Gegenseite**, wortgetreu uebernommen aus
``Budgetmanager/model/lifeplanner_import_service.py``. Aendert BudgetManager
sein Format, muss diese Datei mitgeaendert werden - genau das ist der Zweck.
"""

from __future__ import annotations

import json
import re

import pytest

from logic.budget_export_service import (
    expense_to_budgetmanager_record,
    load_budgetmanager_expense_proposals,
    load_budgetmanager_savings_goals,
)

# Aus Budgetmanager/model/lifeplanner_import_service.py, _EXTERNAL_ID_RE.
# Eine ID, die hier durchfaellt, laesst BudgetManager nicht etwa diese eine
# Zeile aus - der ganze Importlauf bricht mit LifePlannerImportError ab.
BUDGETMANAGER_EXTERNAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/@+\-]{0,254}$")

# Aus Budgetmanager/model/lifeplanner_import_service.py, SCHEMA.
BUDGETMANAGER_IMPORT_SCHEMA = "budgetmanager.import.v1"


class _Expense:
    """Das, was FPM exportiert - nur die Felder, die die Bruecke liest."""

    id = 5
    item_type = "pen"
    currency = "CHF"
    total = 320.0
    amount = 320.0
    shipping = 0
    customs = 0
    purchase_date = "2026-07-04"
    description = "Pilot Custom 823"
    vendor = "Fontoplumo"
    notes = ""
    order_number = ""
    payment_method = ""
    pen_id = None
    ink_id = None
    nib_id = None
    paper_id = None


# ── FPM schreibt, BudgetManager liest ───────────────────────────────────────

def test_der_datensatz_traegt_das_schema_das_budgetmanager_erwartet():
    assert expense_to_budgetmanager_record(_Expense())["schema"] == (
        BUDGETMANAGER_IMPORT_SCHEMA
    )


def test_die_operation_ist_upsert():
    """BudgetManager wirft bei jeder anderen Operation."""
    assert expense_to_budgetmanager_record(_Expense())["operation"] == "upsert"


def test_die_externe_id_passiert_die_pruefung_der_gegenseite():
    record = expense_to_budgetmanager_record(_Expense())
    assert BUDGETMANAGER_EXTERNAL_ID_RE.fullmatch(record["external_id"])


@pytest.mark.parametrize(
    "beschreibung",
    [
        "Pilot Custom 823",          # Leerzeichen
        "Füller mit Öse",            # Umlaute
        "Sailor 1911 (großer Kolben)",  # Klammern
        "Nib #6 / M",                # Sonderzeichen
        "  ",                        # nur Leerraum
        "→ Sonderzeichen ←",         # nichts Verwertbares
    ],
)
def test_auch_ohne_datenbank_id_bleibt_die_externe_id_gueltig(beschreibung):
    """Ohne ``id`` baut FPM die externe ID aus dem Label - fruehere Fassungen
    setzten es roh ein und brachten damit den ganzen Importlauf zu Fall."""

    class Ohne(_Expense):
        id = None
        description = beschreibung
        linked_label = None

    record = expense_to_budgetmanager_record(Ohne())
    assert BUDGETMANAGER_EXTERNAL_ID_RE.fullmatch(record["external_id"]), (
        record["external_id"]
    )


def test_verschiedene_labels_ergeben_verschiedene_ids():
    """Sonst wuerde das Saeubern zwei Ausgaben stillschweigend zusammenlegen."""

    def ident(text: str) -> str:
        class Ohne(_Expense):
            id = None
            description = text
            linked_label = None

        return expense_to_budgetmanager_record(Ohne())["external_id"]

    assert ident("Pilot 823") != ident("Pilot #823")


def test_die_waehrung_besteht_die_pruefung_der_gegenseite():
    """BudgetManager verlangt genau drei Grossbuchstaben."""
    record = expense_to_budgetmanager_record(_Expense())
    assert re.fullmatch(r"[A-Z]{3}", record["currency"])


def test_der_betrag_liegt_im_zulaessigen_bereich():
    """BudgetManager weist 0, negative und uebergrosse Betraege ab."""
    record = expense_to_budgetmanager_record(_Expense())
    assert 0 < float(record["amount"]) <= 999_999_999


# ── BudgetManager schreibt, FPM liest ───────────────────────────────────────

# Wortgetreu aus export_savings_goals() in
# Budgetmanager/model/lifeplanner_import_service.py.
BUDGETMANAGER_SPARZIEL = {
    "schema": "fpm.savings-goal.v1",
    "external_id": "budgetmanager:savings-goal:1",
    "source": "BudgetManager",
    "item_type": "savings_goal",
    "label": "Pilot Custom 823",
    "goal_name": "Pilot Custom 823",
    "status": "sparend",
    "target_amount": 300.0,
    "current_amount": 120.0,
    "contributed_amount": 120.0,
    "withdrawn_amount": 0.0,
    "remaining_amount": 180.0,
    "progress_percent": 40.0,
    "currency": "CHF",
    "deadline": "2026-09-01",
    "category": "Füller",
    "notes": "",
}
BUDGETMANAGER_SPARZIEL_MANIFEST = {
    "schema": "fpm.savings-goals.manifest.v1",
    "source": "BudgetManager",
    "created_at": "2026-08-21T10:00:00+00:00",
}

# Wortgetreu aus export_fpm_expense_proposals().
BUDGETMANAGER_AUSGABE = {
    "schema": "fpm.import.v1",
    "external_id": "budgetmanager:tracking:77",
    "source": "BudgetManager",
    "date": "2026-07-04",
    "amount": 42.0,
    "currency": "CHF",
    "description": "Pilot Custom",
    "category": "Füller",
}


def _jsonl(tmp_path, name, *records):
    pfad = tmp_path / name
    pfad.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records)
        + "\n",
        encoding="utf-8",
    )
    return pfad


def test_die_sparziele_der_gegenseite_kommen_an(tmp_path):
    """Der Fehler, der diesen Test veranlasst hat: Bindestrich statt Unterstrich."""
    pfad = _jsonl(
        tmp_path,
        "budgetmanager_savings_goals.jsonl",
        BUDGETMANAGER_SPARZIEL_MANIFEST,
        BUDGETMANAGER_SPARZIEL,
    )
    ziele = load_budgetmanager_savings_goals(pfad)
    assert len(ziele) == 1
    assert ziele[0].external_id == "budgetmanager:savings-goal:1"
    assert ziele[0].remaining_amount == 180.0
    assert ziele[0].progress_percent == 40.0


def test_die_aeltere_unterstrich_form_gilt_weiter(tmp_path):
    """Eine Bridge-Datei aus einer aelteren Fassung darf nicht wertlos werden."""
    alt = dict(BUDGETMANAGER_SPARZIEL, schema="fpm.savings_goal.v1")
    pfad = _jsonl(tmp_path, "budgetmanager_savings_goals.jsonl", alt)
    assert len(load_budgetmanager_savings_goals(pfad)) == 1


def test_das_manifest_zaehlt_nicht_als_sparziel(tmp_path):
    pfad = _jsonl(
        tmp_path, "budgetmanager_savings_goals.jsonl", BUDGETMANAGER_SPARZIEL_MANIFEST
    )
    assert load_budgetmanager_savings_goals(pfad) == []


def test_die_ausgabevorschlaege_der_gegenseite_kommen_an(tmp_path):
    pfad = _jsonl(tmp_path, "budgetmanager_to_fpm.jsonl", BUDGETMANAGER_AUSGABE)
    vorschlaege = load_budgetmanager_expense_proposals(pfad)
    assert len(vorschlaege) == 1
    assert vorschlaege[0].external_id == "budgetmanager:tracking:77"
    assert vorschlaege[0].item_type == "pen"
    assert vorschlaege[0].amount == 42.0


# ── Die Bruecke darf die Sammlung nie blockieren ────────────────────────────

def test_ein_unschreibbarer_bridge_ordner_bleibt_folgenlos(monkeypatch, caplog):
    """Der Aufruf steht hinter ``session.commit()``.

    Wuerde er werfen, liefe er in den umgebenden ``except``-Zweig der
    Oberflaeche: der Nutzer saehe eine Fehlermeldung und ein ``rollback()``, das
    nach dem Commit nichts mehr zurueckgibt. Die Ausgabe waere gespeichert und
    die Meldung trotzdem alarmierend.
    """
    from logic import budget_export_service as bridge

    def kaputt(_session):
        raise OSError("Netzlaufwerk getrennt")

    monkeypatch.setattr(bridge, "sync_default_outbox_from_session", kaputt)

    with caplog.at_level("WARNING"):
        assert bridge.sync_default_outbox_from_session_safely(object()) is None

    assert any("Bridge-Outbox" in r.message for r in caplog.records), (
        "Der Fehler verschwindet spurlos - er gehoert ins Log"
    )


def test_die_oberflaeche_ruft_ueberall_die_sichere_variante(tmp_path):
    """Eine einzelne strikte Stelle reicht, um den Fehler zurueckzuholen."""
    import re
    from pathlib import Path

    wurzel = Path(__file__).resolve().parents[1] / "ui"
    strikt = []
    for datei in wurzel.glob("*.py"):
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"sync_default_outbox_from_session(?!_safely)", zeile):
                strikt.append(f"{datei.name}:{nr}")
    assert not strikt, f"strikter Bridge-Sync in der Oberflaeche: {strikt}"


# ── Der Zustand der Bruecke ist sichtbar ────────────────────────────────────

def test_der_zustand_nennt_alle_drei_dateien(tmp_path, monkeypatch):
    """Ohne diese Anzeige ist nicht zu erkennen, ob der Austausch stattfindet -
    und vor allem nicht, welcher Ordner gerade gilt."""
    from logic.budget_export_service import bridge_zustand

    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    ordner, befunde = bridge_zustand()

    assert ordner == tmp_path
    assert len(befunde) == 3
    assert all(not b.vorhanden for b in befunde)


def test_der_zustand_zaehlt_die_eintraege(tmp_path, monkeypatch):
    from logic.budget_export_service import bridge_zustand

    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    _jsonl(tmp_path, "budgetmanager_savings_goals.jsonl",
           BUDGETMANAGER_SPARZIEL_MANIFEST, BUDGETMANAGER_SPARZIEL)
    _jsonl(tmp_path, "budgetmanager_to_fpm.jsonl", BUDGETMANAGER_AUSGABE)

    _, befunde = bridge_zustand()
    nach_name = {b.name: b for b in befunde}

    assert nach_name["Sparziele → FPM"].eintraege == 1
    assert nach_name["BudgetManager → FPM"].eintraege == 1
    # Die dritte gibt es noch nicht - das ist etwas anderes als leer.
    assert not nach_name["FPM → BudgetManager"].vorhanden


def test_eine_kaputte_zeile_sprengt_die_anzeige_nicht(tmp_path, monkeypatch):
    from logic.budget_export_service import bridge_zustand

    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    (tmp_path / "budgetmanager_to_fpm.jsonl").write_text(
        "kein json\n", encoding="utf-8")

    _, befunde = bridge_zustand()
    nach_name = {b.name: b for b in befunde}
    assert nach_name["BudgetManager → FPM"].vorhanden
    assert nach_name["BudgetManager → FPM"].eintraege == 0
