# Release- und Tiefenanalyse v0.2.88 – Locale & Currency Hardening

**Stand:** 10. Juli 2026  
**Ausgangsdatei:** vom Nutzer hochgeladene v0.2.87-Quell-ZIP  
**Bewertung:** Quellcode/RC **GO**; native Windows-/Linux-Pakete bleiben bis zum erfolgreichen CI-Build und Plattform-Smoke-Test ein **bedingtes GO**.

## 1. Gemeldetes Fehlerbild

Im Füller-Dialog wurde bei deutscher Betriebssystem-Locale beispielsweise `39,96 CHF` angezeigt, obwohl die FountainPen-Manager-Region auf Schweiz stand und damit `CHF 39.96` gelten sollte. Ursache war keine einzelne falsche Formatzeichenfolge, sondern eine verteilte Locale-Architektur:

- `QDoubleSpinBox` übernahm Komma/Punkt vom Betriebssystem;
- die App führte parallel eigene Regionseinstellungen;
- Währungscodes waren teils übersetzte Texte statt stabile ISO-Daten;
- einzelne Tabellen, Dialoge und CSV-Importer hatten eigene Format-/Parse-Logik.

Damit konnten Anzeige, Eingabe, Speicherung, Umrechnung und Export voneinander abweichen.

## 2. Gefundene und behobene Fehler

| Priorität | Fehler | Wirkung | Behebung |
|---|---|---|---|
| P0 | Betriebssystem-Locale statt App-Locale in Dezimalfeldern | `39,96`/`39.96` wechselte abhängig vom Host | zentrale `LocalizedDoubleSpinBox` für alle Dezimalfelder |
| P0 | Naiver Parser konnte `39,96` als `3996` behandeln | Faktor-100-Fehler bei Preisen | robuster Parser für Punkt, Komma und regionale Gruppierung |
| P0 | CHF-Übersetzung war in EN teilweise `USD`, in FR teilweise `EUR` | falsche Währung konnte gespeichert werden | ISO-Codes sind nicht mehr übersetzbar; Combo-Daten bleiben `CHF/EUR/USD/GBP` |
| P1 | Kauf-/Markt-/Versicherungswert nutzten starre oder falsche Suffixe | Anzeige passte nicht zur gewählten Währung/Region | dynamische Präfix-/Suffixbindung pro Währungsfeld |
| P1 | Wechsel der Währung aktualisierte das Betragsfeld nicht überall | sichtbarer Code und gespeicherter Code konnten auseinanderlaufen | zentrale Combo-Bindung mit sofortigem Refresh |
| P1 | Regionwechsel verschob offene Felder nicht live von Präfix zu Suffix | bis zum erneuten Öffnen blieb z. B. `CHF 39,96` stehen | Geldfelder merken ISO-Code und werden appweit live neu gezeichnet |
| P1 | Dezimal- und Tausender-Radiobuttons waren nicht als getrennte Gruppen definiert | Auswahl konnte die jeweils andere Gruppe abwählen | zwei explizite `QButtonGroup`-Instanzen |
| P1 | Frankreich-Preset verlangte Leerzeichen, UI bot es aber nicht an | FR wurde auf Apostroph verfälscht | Auswahl „Leerzeichen (1 234)“ ergänzt |
| P1 | „Kein Tausendertrennzeichen“ wurde beim Laden als fehlender Wert behandelt | Einstellung sprang nach Neustart auf Apostroph zurück | `None` und leerer String werden getrennt behandelt |
| P1 | Gleiches Dezimal- und Tausenderzeichen war speicherbar | mehrdeutige Werte wie `1,234,56` | Speichern wird blockiert; Altwerte werden fail-safe normalisiert |
| P1 | Wechselkursfelder nutzten unsicheres Komma→Punkt-Ersetzen | lokale Eingaben und ungültige Werte waren fehleranfällig | gemeinsamer Parser; nur positive, endliche Kurse zulässig |
| P1 | Fehlende Währung wurde bei Umrechnung implizit als CHF behandelt | falsche Beträge bei EUR/USD-Standardregion | fehlende Währung gilt als aktuelle Standardwährung |
| P2 | Wishlist, Ausgabenhistorie, Tintenwerte und Papier hatten eigene Formatierungen | optische Inkonsistenzen | einheitliches `format_money()` |
| P2 | CSV-Import verwendete einfache String-Ersetzungen | gruppierte Werte/Symbole konnten falsch gelesen werden | derselbe locale-sichere Parser wie in der GUI |
| P2 | Malformed Gruppierungen wie `12,34,56` wurden zu einer plausiblen Zahl umgedeutet | stiller Eingabefehler | fehlerhafte Gruppierung wird abgelehnt |

## 3. Festgelegtes Verhalten

| App-Region | Anzeige |
|---|---|
| Schweiz | `CHF 1'234.56` |
| Deutschland / Österreich | `1.234,56 EUR` |
| Frankreich | `1 234,56 EUR` |
| Grossbritannien | `GBP 1,234.56` |
| USA | `USD 1,234.56` |

In editierbaren Feldern werden keine Tausenderzeichen erzwungen. Sowohl `39,96` als auch `39.96` werden als **39.96** gespeichert. Die Datenbank speichert numerische Werte sprachneutral; die Region wirkt nur auf Ein-/Ausgabe.

## 4. Betroffene Bereiche

Die zentrale Logik ist eingebunden in:

- Füller: Kaufpreis, Marktwert, Versicherungswert, Servicekosten;
- Tinten: Kaufpreis, Kosten/ml, Kosten/Füllung und Restwert;
- Papier und Notizbücher;
- Ausgaben inklusive Versand und Zoll;
- Wishlist inklusive Ziel-, Erwartungs-, Istpreis, Versand und Zoll;
- Monats-/Jahresbudgets und Wechselkurse;
- Statistiken, Dashboard und Detailansichten;
- alle weiteren Dezimalfelder wie ml, mm, g und Minuten;
- CSV-Importe für Füller und Tinten.

## 5. Zusätzlich erhaltene Release-Härtungen

Die hochgeladene v0.2.87 enthielt gegenüber dem zuvor gehärteten Stand Regressionen. v0.2.88 bewahrt bzw. vereint deshalb weiterhin:

- Modulrunde, Expertenfunktionen am Schluss, danach Tinte, ein bis zwei Füller und Rotation;
- echte Rotationsvorschläge über die Schnellaktion;
- keine automatisch erzeugten Beispiel-Tinten;
- vollständiges Backup/Restore mit Manifest, Prüfsummen und Rückfall-Wiederherstellung;
- Foreign Keys, fail-fast Migrationen und Vor-Migrationsbackup;
- gehärtete ZIP-/Updater-Prüfung;
- Linux-/Windows-GUI-Smoke-Tests in CI;
- nicht-fatale Bildimporte, sodass ein Bildfehler keinen Datensatz verwirft;
- zwei tatsächlich geöffnete Recherche-Stufen.

## 6. Validierung

| Prüfung | Ergebnis |
|---|---:|
| Pytest | **235 bestanden** |
| Neue Locale-/Währungstests | **16 bestanden** |
| Python `compileall` | bestanden |
| Versionssynchronität | **0.2.88**, bestanden |
| Ruff `F,B,PLW` | **0 Befunde** |
| i18n-Parität | **2.102 Schlüssel × 3 Sprachen** |
| i18n Qualitätsaudit | bestanden |
| i18n Key-Wiring | bestanden |
| i18n Runtime-Audit | bestanden |
| Sichtbare-Texte-Audit | bestanden |
| KILLCRITIC | **2.000 Checks, 0 Findings** |
| Qt GUI Smoke | bestanden |
| Pen-Dialog CH/DE Integration | bestanden |
| Settings-Preset Frankreich | `1 234,56 EUR`, bestanden |

Die Tests prüfen unter anderem alle sieben Regionen, Eingabe mit Punkt und Komma, dynamischen Währungswechsel, Live-Regionwechsel, stabile ISO-Codes, ungültige Gruppierungen und die Verwendung der zentralen Qt-Komponente in allen UI-Modulen.

## 7. Historische Daten

Frühere englische bzw. französische Builds konnten wegen der falschen Übersetzungswerte einen als CHF gedachten Datensatz als USD oder EUR gespeichert haben. Das lässt sich nicht sicher automatisch korrigieren, weil echte USD-/EUR-Käufe nicht von fehlerhaften Einträgen unterscheidbar sind. Betroffene ältere Datensätze sollten einmal in Füller-, Tinten-, Papier-, Wishlist- und Ausgabenansicht kontrolliert werden. Neue und erneut gespeicherte Einträge verwenden stabile ISO-Codes.

## 8. Packaging und Releaseentscheidung

Ein echter Qt-Start aus dem Quellbaum ist erfolgreich. Der lokale PyInstaller-Linux-Build überschritt in dieser begrenzten Umgebung zweimal das verfügbare Zeitfenster während der PySide-Hook-Analyse; es wurde kein Quellcodefehler ausgegeben, aber auch kein fertiges natives Bundle erzeugt.

- **Source / interner RC:** GO.
- **Öffentlicher Stable-Release:** bedingtes GO nach erfolgreichem GitHub-Actions-Build und je einem kurzen Starttest unter Windows und Linux.

Minimaler Plattform-Smoke-Test:

1. Region Schweiz: Kaufpreis zeigt `CHF 39.96`.
2. Region Deutschland: Kaufpreis zeigt `39,96 EUR`.
3. Eingabe `39,96` und `39.96` ergibt jeweils denselben gespeicherten Wert.
4. Währungswechsel CHF→EUR ändert den sichtbaren Code sofort.
5. App-Neustart behält Leerzeichen bzw. „kein Tausendertrennzeichen“.
6. Rotation erzeugt und übernimmt einen echten Vorschlag.
7. Vollbackup lässt sich erstellen und prüfen.
