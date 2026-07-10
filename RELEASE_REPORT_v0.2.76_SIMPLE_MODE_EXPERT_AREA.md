# Release Report – FountainPen Manager v0.2.76 Simple Mode / Expert Area

## Kurzurteil

v0.2.76 ist ein DAU-/UI-Hardening auf Basis von v0.2.75. Der wichtigste offene Punkt aus dem Audit wurde umgesetzt: Die App trennt jetzt einfache Alltagsbedienung und Expertenfunktionen klarer.

## Umgesetzt

| Punkt | Status |
|---|---:|
| Einfachmodus als Standard | Erledigt |
| Expertenbereich umschaltbar | Erledigt |
| Vier klare Dashboard-Startaktionen | Erledigt |
| Settings-Option für UI-Modus | Erledigt |
| Simple-/Expert-GUI-Smoke-Test | Erledigt |
| DE/EN/FR nachgeführt | Erledigt |
| Windows-/Release-Doku auf v0.2.76 | Erledigt |

## Releasefähigkeit

| Ziel | Urteil |
|---|---|
| Source-/Portable-RC | Ja |
| Öffentlicher Final Release | Nach echtem GUI-Smoke-Test auf Linux/Windows |
| Windows-Installer | Nach Build + Installationstest |
| Updater | URL korrekt; final mit echter `latest.json` und SHA256 |

## Kritische Restgrenze

In dieser Umgebung ist PySide6 nicht installiert. Deshalb kann der GUI-Smoke-Test hier nur als vorbereitetes Tool validiert werden. Auf einer echten PySide6-Umgebung muss ausgeführt werden:

```bash
python tools/gui_smoke_test.py
```

Erwartung mit PySide6: `OK: GUI smoke test passed`.

Ohne PySide6 ist der erwartete Rückgabewert `77` mit `SKIP`.
