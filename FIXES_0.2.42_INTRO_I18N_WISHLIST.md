# Fixes 0.2.42 – Introduction i18n + Wishlist-Kaufübernahme

## Introduction / Tour

- App-Tour (`ui/tour_controller.py`) nutzt jetzt `t(...)` für alle sichtbaren Tour-Schritte.
- Tour-Overlay (`ui/tour_overlay.py`) nutzt übersetzte Buttons/Tooltips.
- Fallback-Onboarding-Wizard (`ui/onboarding_wizard.py`) nutzt übersetzte Titel, Texte und Buttons.
- Dashboard-Schnellstartbox nutzt übersetzte Texte.
- Übersetzungsschlüssel für Deutsch, Englisch und Französisch ergänzt.

## Wishlist → Sammlung/Ausgaben

- Kontextmenü hat jetzt ein klares Status-Untermenü.
- `gekauft` wird nicht mehr still über den Edit-Dialog gesetzt, wenn noch kein Sammlungsobjekt/Ausgabe erzeugt wurde.
- Für echte Käufe muss `Als gekauft übernehmen …` genutzt werden.
- Bereits übernommene Wishlist-Einträge erzeugen keine Duplikate mehr.
- Artikelkarte speichert jetzt auch `created_object.type/id`.
- Migration ergänzt `expenses.paper_id`, damit Papier-Übernahmen in Alt-Datenbanken nicht crashen.

## Version

- App-Version: 0.2.42
- i18n-Version: v0.2.42
