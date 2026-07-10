# Release Report v0.2.64 – Wishlist-/BudgetManager-Bridge-Hotfix

## Befund
1. Die Wishlist konnte durch fehlende Style-Imports beim Öffnen abbrechen.
2. Eine Wishlist-Übernahme erzeugte zwar eine FPM-Ausgabe, schrieb aber die BudgetManager-Bridge-Outbox nicht neu. Dadurch konnte der BudgetManager keine Füller-Ausgabe aus der Wishlist importieren.

## Umsetzung
- Fehlende UI-Konstanten importiert.
- Best-effort Outbox-Sync nach erfolgreicher Wishlist-Kaufübernahme ergänzt.
- Regressionstests erweitert, damit diese Kopplung nicht wieder verloren geht.

## Ergebnis
Wishlist-Käufe erscheinen nach der Übernahme als normale FPM-Ausgaben und werden automatisch für den BudgetManager vorgeschlagen.
