# v0.2.37 Tour Settings Hotfix

## Behoben

- Einstellungen konnten nicht geöffnet werden, weil `SettingsWidget._start_tour_now` fehlte.
- Der Button „Tour jetzt starten“ sendet jetzt korrekt `tour_requested`.
- `MainWindow` verbindet dieses Signal weiterhin mit `start_tour()`.
- Onboarding-Text in den Einstellungen spricht nun konsistent von App-Tour statt Wizard.

## Beibehalten

- Globale UI-Skalierung aus v0.2.36.
- Tour-MVP.
- NibFormat / Nib / PenNibSetup Workflow aus v0.2.35.
