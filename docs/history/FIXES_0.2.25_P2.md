# FPM v0.2.25 – P2 Architektur-Investitionen

Basis: v0.2.24-p01-complete

## P2.1 · AppEventBus (Session-Race behoben)

**Neue Datei:** `logic/event_bus.py`

Zentraler Qt-Signal-Bus als Singleton. Löst das Session-Race-Problem:
Widget A committed → emittet Signal → alle bereits geöffneten Widgets refreshen sich.

**Signals:** pens_changed, inks_changed, nibs_changed, papers_changed, expenses_changed, all_changed

**Subscribe (in Widget-Konstruktoren):**
- DashboardWidget  → pens_changed + inks_changed
- RotationWidget   → pens_changed + inks_changed
- PenWidget        → inks_changed (Tinten-Dropdown beim Einfüllen)
- InkWidget        → inks_changed
- NibWidget        → nibs_changed
- PaperWidget      → papers_changed

**Emit (nach session.commit()):**
- PenWidget:      13 kritische Commit-Stellen → pens_changed / nibs_changed / inks_changed
- InkWidget:       6 Commit-Stellen → inks_changed
- NibWidget:       3 Commit-Stellen → nibs_changed
- PaperWidget:     3 Commit-Stellen → papers_changed
- RotationEngine:  3 Commit-Stellen → pens_changed + inks_changed

Kein Debouncing – Widgets reagieren sofort. Bei Performance-Problemen
mit großen Sammlungen ist ein 50ms-Timer-Debounce vorbereitet.

## P2.2 · schema_version

Bereits in P0 eingeführt (AppSettings key `schema_version` = "0.2.24/25").
Kein weiterer Aufwand in P2.

## P2.3 · OnboardingWizard (4-Schritt)

**Neue Datei:** `ui/onboarding_wizard.py`

Erscheint automatisch beim ersten Start wenn:
- AppSettings `onboarding_completed` ≠ "1" UND
- DB hat weder Füller noch Tinten

**4 Seiten:**
1. Willkommen + Reihenfolge-Erklärung (Tinte → Füller → Einfüllen)
2. Erste Tinte anlegen (CTA öffnet direkt InkDialog)
3. Ersten Füller anlegen (CTA öffnet direkt PenDialog)
4. Zur Füllerverwaltung → Tinte einfüllen

Nach Abschluss oder "Überspringen": AppSettings `onboarding_completed` = "1"

**Integration:**
- `main.py`: `window.show_onboarding_if_needed()` nach `window.show()`
- `main_window.py`: `show_onboarding_if_needed()` + Wizard-Signal-Handler
- `settings_widget.py`: "🚀 Onboarding zurücksetzen" Button in Resets-Gruppe

## Bewusst zurückgestellt (P3)
- Papier in Rotation
- Media-Modell (mehrere Bilder)
- Undo/EventLog
- Vollständige i18n
