# Manueller GUI-Smoke-Test v0.2.77

Dieser Test ist Pflicht vor einem öffentlichen Release, weil reine Unit-Tests keine Qt-Interaktion auf Windows/Linux ersetzen.

## Vorbereitung

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

Für einen sauberen Test kann ein temporärer Datenordner gesetzt werden:

```bash
FPM_DATA_DIR=/tmp/fpm-smoke-data python main.py
```


## Automatischer Kurztest

Vor dem manuellen Test kann zusätzlich ausgeführt werden:

```bash
python tools/gui_smoke_test.py
```

Rückgabecode `77` bedeutet: PySide6/Qt ist in dieser Umgebung nicht installiert; dann ist der manuelle GUI-Test auf einem echten Zielsystem erforderlich.

## Pflichtcheck

1. App startet ohne zweites Hauptfenster und ohne Traceback.
2. App startet im Einfachmodus: sichtbar sind Dashboard, Füller, Tinten, Rotation, Hilfe und Einstellungen.
3. Die vier Dashboard-Aktionen sind sichtbar: Füller eintragen, Tinte eintragen, Füller befüllen, Reinigung eintragen.
4. Expertenbereich über den Seitenleisten-Button aktivieren: alle Gruppen erscheinen wieder.
5. `Ctrl+1` bis `Ctrl+9` und `Alt+1` bis `Alt+5` öffnen im Expertenmodus die erwarteten Module.
6. Zurück in den Einfachmodus wechseln: Expertenmodule werden wieder ausgeblendet.
7. Neue Datenbank anlegen oder leere Testdatenbank verwenden.
8. Füller anlegen: Marke, Modell, Füllsystem, Federdaten speichern.
9. Tinte anlegen: Marke, Name, Farbe, Füllstand speichern.
10. Füller mit Tinte befüllen.
11. Rotation öffnen und Vorschläge generieren.
12. Befüllung reinigen und optional direkt neu befüllen.
13. Expertenmodus aktivieren, Regel-Ansicht öffnen; mindestens eine Regel aktivieren/deaktivieren.
14. Sprache auf Englisch wechseln, App neu starten, Rotation/Regeltexte prüfen.
15. Sprache auf Französisch wechseln, App neu starten, Rotation/Regeltexte prüfen.
16. Wishlist-Eintrag anlegen und in Ausgabe übertragen.
17. Ausgaben öffnen, Eintrag prüfen, CSV-Export testen.
18. Einstellungen öffnen, UI-Skalierung ändern, App neu starten.
19. Backup erstellen und in sauberem temporärem Datenordner wiederherstellen.
20. Hilfe öffnen und Tour starten/abbrechen.
21. App schließen und erneut starten: keine Daten verloren, keine Startfehler.

## Freigabekriterium

Release darf nur freigegeben werden, wenn alle Pflichtpunkte ohne Crash, unverständliche Fehlermeldung oder Datenverlust funktionieren.

GitHub-Releasepfad in v0.2.77: https://github.com/sloogy/FPM/releases. Der Updater nutzt latest.json über /releases/latest/download/latest.json.
