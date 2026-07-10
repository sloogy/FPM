# v0.2.52 – Wishlist-Kaufübernahme Fix

## Behoben

- Wunschfüller, die als gekauft übernommen werden, erscheinen zuverlässig in der aktiven Füllerliste.
- Der Füller-Tab hört nun auch auf externe `pens_changed`-Signale und aktualisiert sich, wenn ein Füller außerhalb des Füller-Moduls erzeugt wird.
- Die Wishlist-Übernahme setzt bei neu erzeugten Füllern explizit sichtbare/aktive Standardwerte:
  - `is_active=True`
  - `availability_status="available"`
  - `rotation_blocked=False`
  - `rotation_role="writer"`
- Wird im Wishlist-Bearbeiten-Dialog der Status `gekauft` gewählt, läuft nun derselbe nachvollziehbare Übernahme-Workflow wie über „Als gekauft übernehmen“.
- Reine Statuswechsel auf `gekauft` ohne Sammlung/Ausgabe werden vermieden.
- Übernahmen emittieren nun zielgenaue Events für Füller, Tinten, Federn, Papier und Ausgaben.

## Regressionstest

- Statische Regressionstests ergänzt, damit Wishlist→Füller-Übernahme, PenWidget-Refresh und der Bearbeiten-Dialog-Workflow nicht erneut auseinanderlaufen.
