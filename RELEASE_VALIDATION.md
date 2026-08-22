# FPM v0.3.05 – Release Validation

| Validierung | Lokales Ergebnis |
|---|---:|
| `python tools/sync_version.py --check` | 0.3.05 synchron |
| `python -m compileall -q .` | bestanden |
| `python tools/import_smoke.py` | 66 Produktionsmodule; SQLAlchemy und PySide6 echt |
| Vollständige Pytest-Suite | 418 bestanden; 75,37 % Kern-Coverage |
| PyInstaller Linux-Onedir-Build | gebaut; Bundle mit isolierter Datenbank erfolgreich initialisiert |
| Kritische Updater-Coverage | 86,55 %, Mindestgate 85 % bestanden |
| `python tools/name_audit.py` | 0 undefinierte Namen, 0 ungenutzte Importe |
| `python tools/exception_audit.py` | 141 ≤ 141 breite, 35 ≤ 35 stumme, 0 nackte `except`, 0 `BaseException` |
| `python tools/db_access_audit.py` | 49 ≤ 49; vier Dateien dauerhaft query-frei |
| i18n-Audits (5) | bestanden; 2.109 Schlüssel × 3 |
| LifePlanner v0.3.05 Pipeline-Tests | 14 gezielte Tests bestanden; Build, Signatur, Tamper-Abwehr, Host-Install |
| KILLCRITIC 1000-Loop | 141.000 Checks, 0 Findings |
| Workflow-YAML | alle Workflows syntaktisch geparst |
| Plattform-Locks | Linux/Windows erzeugt, Hash-Check und Binary-only-Installationspläne bestanden |
| Ruff/Bandit | bestanden |
| PySide6-GUI-Suite und GUI-Smoke | mit realem PySide6 bestanden |
| Authenticode-Signierung | Workflow implementiert; reales Zertifikat/Tag-Artefakt extern zu verifizieren |

## Interpretation

Der Quellstand ist gehärtet und regressionsgeprüft. Die Plattform-Locks und alle lokal reproduzierbaren CI-Gates sind grün. Die offizielle Pipeline veröffentlicht weiterhin erst nach erfolgreicher Windows-/Linux-Matrix und realer Signierung.
