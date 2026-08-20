# FountainPen Manager v0.3.00 – Release Validation

| Prüfung | Ergebnis |
|---|---:|
| Versionssynchronisierung | bestanden |
| Python-Kompilierung | bestanden |
| Automatisierte Tests | 275 bestanden |
| Coverage-Gate | 54,35 %, Mindestwert 50 % bestanden |
| GUI-Smoke-Test | bestanden |
| Ruff kritische Regeln | bestanden |
| Bandit mittel/hoch | 0 Findings |
| Windows-Pfadprüfung | bestanden |
| i18n-Audit | 2.093 Schlüssel × 3 Sprachen |
| i18n-Qualität/Wiring/Runtime/Visible | bestanden |
| KILLCRITIC | 116 Invarianten × 1.000 = 116.000 Checks, 0 Findings |
| Visuelle Offscreen-Stichproben | Dashboard, Einstellungen und Wizard bestanden |

## Visuelle Stichproben

- Dashboard: 1.024 × 640 Pixel, zweispaltige Kacheln und sichtbare Öffnen-Aktionen.
- Einstellungen: 800 × 600 Pixel, kompakte Navigation und erreichbare Onboarding-Aktionen.
- Einrichtungsassistent: 752 × 584 Pixel nutzbare Fläche, Inhalt und Navigation vollständig erreichbar.

## Einschränkungen

Qt-Offscreen-Tests ersetzen keine nativen Windows-/Linux-Prüfungen mit realem Desktop-Theme, Betriebssystem-DPI und Mehrmonitorwechsel. Die Gesamt-Coverage besteht den Gate, kritische Updater-, Regel- und Rotationsfehlerpfade benötigen künftig mehr Verhaltenstests.
