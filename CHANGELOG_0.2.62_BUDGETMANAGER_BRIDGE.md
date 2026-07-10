# Version 0.2.62 – BudgetManager-Bridge

- FPM schreibt nach neuen/geänderten Ausgaben automatisch eine reviewbare JSONL-Outbox nach `~/fpm_budgetmanager_bridge/fpm_to_budgetmanager.jsonl`.
- Einstellungen → Import / Export kann BudgetManager→FPM-Vorschläge importieren.
- Importierte BudgetManager-Vorschläge werden als normale FPM-Ausgaben mit stabiler Bridge-ID in den Notizen gespeichert.
- Dubletten werden erkannt und übersprungen.
- Bestehender BudgetManager-Export bleibt erhalten und nutzt dasselbe robuste Schema.
- i18n-Texte in Deutsch, Englisch und Französisch ergänzt.

Checks:
- `python -m compileall -q logic ui database`
- `python tools/i18n_audit.py`
- `python -m pytest -q tests/test_budgetmanager_bridge_service.py`
- Funktionaler JSONL-Bridge-Smoke
