# v0.2.36 – UI Scaling + Tour Merge

## Ziel
Die Version führt die Tour-MVP-Version mit dem v0.2.35 Nib-Setup-Workflow zusammen und behebt die UI-Skalierung auf Laptop-/HiDPI-Displays.

## Wichtig
Basis bleibt der Nib-Setup-Workflow:

- `NibFormat` = Format / Kompatibilität
- `Nib` = konkretes Feder-Exemplar
- `PenNibSetup` = Feder + Feed + Schreibgefühl im konkreten Füller

Die Tour-Version wurde nur als UI-/Onboarding-Erweiterung übernommen. Sie überschreibt nicht das Feder-Setup-Modell.

## UI-Skalierung
Neu:

- `ui/ui_scale.py`
- globale Einstellung `ui_scale_mode`
- Modi: Auto, Kompakt, Normal, Laptop groß, Sehr groß
- Stylesheet skaliert Schrift, Buttons, Eingabefelder, Tabs, Tabellen und Dialogelemente
- Eingabefelder haben Mindesthöhen, damit Text nicht mehr abgeschnitten wird
- Füller-Dialog-Tabs sind scrollbar
- Dialoggrößen werden über `scale_px()` skaliert

## Einstellungen
Neue Seite:

- Einstellungen → Darstellung
- UI-Größe speichern und sofort anwenden

## App-Tour
Übernommen aus Tour-MVP:

- `ui/tour_controller.py`
- `ui/tour_overlay.py`
- Tour beim ersten Start, wenn DB leer ist
- Tour über Hilfe und Einstellungen manuell startbar
- Tour-Reset in der Gefahrenzone

## Stabilitätsnotiz
Die alte OnboardingWizard-Datei bleibt als Fallback im Projekt, falls die Tour aus irgendeinem Grund nicht gestartet werden kann.
