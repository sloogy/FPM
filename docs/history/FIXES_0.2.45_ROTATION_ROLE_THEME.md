# v0.2.45 – Rotation nach Rolle, Thema und Tinten-Standzeit

## Implementiert

- Füller-Datenmodell erweitert:
  - `rotation_role`
  - `rotation_theme`
- Tinten-Datenmodell erweitert:
  - `usage_tags`
- SQLite-Migration erweitert, bestehende Datenbanken bekommen die neuen Spalten automatisch.
- Füller-Dialog erweitert:
  - Rotationsrolle: EDC, Agenda, Tagebuch, Arbeit/Business, Kreativ, Brief, Sammler/Grail, Vintage, Problem/Schonbetrieb, feine Feder, breite Feder.
  - Standard-Thema als Kontext für Vorschläge.
- Tinten-Dialog erweitert:
  - Einsatz-/Themen-Tags für Rotation, z. B. EDC, Agenda, Business, Tagebuch, Kreativ, Sheen/Showcase, feine Feder, Billigpapier, pflegeleicht, Vintage-sicher.
- Rotation-Engine erweitert:
  - Explizite Füllerrolle hat Vorrang vor automatischer Feder-/Tag-Inferenz.
  - Bugfix: Füller-Tags werden jetzt als CSV-Liste gelesen, nicht als Zeichen-Set.
  - Thema/Rotation-Kontext fließt in den Score ein.
  - Tinten-`last_used` bleibt zentrale Rotationsmetrik und wird im Score transparent ausgegeben.
  - Rollen- und Themen-Delta werden getrennt gespeichert.
- Rotations-UI erweitert:
  - Temporäres Rotationsthema in der Kopfzeile.
  - Score-Erklärung zeigt jetzt `pen_days_bonus`, `ink_days_bonus`, `role_delta`, `theme_delta`, Diversitätsbonus und Familienmalus.
- Clean+Refill-Workflow korrigiert:
  - Neue Tinten werden nicht mehr alphabetisch angeboten.
  - Die Combo wird nach Engine-Score sortiert.
  - Die beste Empfehlung wird automatisch vorausgewählt.
  - Die aktuell eingefüllte Tinte wird ausgeschlossen.

## Technische Hinweise

- Keine globale UI-Monkeypatch-Änderung.
- `dev_check.py`: Syntaxcheck und lokale Importnamen OK.
- Runtime-Funktionstest mit echter DB wurde im Container nicht ausgeführt, weil SQLAlchemy/PySide6 dort nicht installiert sind.
