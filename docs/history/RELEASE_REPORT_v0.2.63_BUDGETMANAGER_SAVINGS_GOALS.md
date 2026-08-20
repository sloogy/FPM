# Release Report v0.2.63 – BudgetManager-Sparzielanzeige

## Umsetzung
- FPM liest `~/fpm_budgetmanager_bridge/budgetmanager_savings_goals.jsonl` als read-only Sparziel-Spiegelung.
- Dashboard zeigt verknüpfte BudgetManager-Sparziele mit Fortschritt, aktuellem Betrag, Zielbetrag, Restbetrag und Frist/Status.
- Neue Tests für die Sparziel-Spiegelung ergänzt.

## Sicherheitsentscheidung
- FPM speichert die BudgetManager-Sparziele nicht dauerhaft.
- Keine direkte BudgetManager-Datenbankkopplung.
- Die bestehende Ausgaben-Bridge bleibt unverändert reviewbar.

## Checks
- `python -m compileall -q logic ui tests`
- `python -m pytest -q tests/test_budgetmanager_bridge_service.py tests/test_release_hardening_static.py tests/test_wishlist_purchase_static.py`
- `python tools/i18n_audit.py`
- `python tools/i18n_key_wiring_audit.py`
- `python tools/i18n_visible_text_audit.py`
