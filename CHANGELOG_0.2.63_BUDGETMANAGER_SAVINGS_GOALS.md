# Version 0.2.63 – BudgetManager-Sparzielanzeige

- FPM liest verknüpfte BudgetManager-Sparziele aus `~/fpm_budgetmanager_bridge/budgetmanager_savings_goals.jsonl`.
- Dashboard zeigt diese Ziele read-only mit Fortschritt, aktuellem Stand, Zielbetrag, Restbetrag und Frist/Status.
- Keine direkte BudgetManager-Datenbankkopplung; die Bridge bleibt reviewbar und robust.

Checks:
- `python -m compileall -q logic ui tests`
- `python -m pytest -q tests/test_budgetmanager_bridge_service.py tests/test_release_hardening_static.py tests/test_wishlist_purchase_static.py`
