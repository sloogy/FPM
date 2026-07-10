# Version 0.2.64 – Wishlist-/BudgetManager-Bridge-Hotfix

## Fixes
- Wishlist-Ansicht startet wieder: fehlende Button-Style-Imports (`BTN_SECONDARY`, `BTN_SUCCESS`, `BTN_DANGER`) ergänzt.
- Wishlist → „als gekauft übernehmen” aktualisiert nach dem erzeugten FPM-Ausgaben-Eintrag automatisch die FPM→BudgetManager-Outbox.
- Dadurch liegen Wishlist-Käufe direkt in `~/fpm_budgetmanager_bridge/fpm_to_budgetmanager.jsonl` für den BudgetManager-Import bereit.
- Fehler in der Bridge werden best-effort abgefangen und blockieren die eigentliche Wishlist-Übernahme nicht.

## Checks
- `python -m py_compile ui/wishlist_widget.py logic/budget_export_service.py`
- `python -m pytest -q tests/test_wishlist_purchase_static.py tests/test_budgetmanager_bridge_service.py`
