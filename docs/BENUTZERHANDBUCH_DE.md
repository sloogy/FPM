# FountainPen Manager – Benutzerhandbuch (Leitfaden)

**Stand: v0.2.88 · Sprache: Deutsch**

Dieses Handbuch ist der ausführliche Leitfaden zum FountainPen Manager. Es ergänzt die In-App-Hilfe (das „Wiki“ im Hilfe-Bereich): Das Wiki beantwortet Fragen kurz am Ort des Geschehens – dieses Handbuch erklärt die Funktionen **im Detail**, inklusive der konkreten Zahlen, Formeln und Dateien dahinter. Alle Zahlenangaben sind Werkseinstellungen des angegebenen Versionsstands; vieles davon ist in der App selbst einstellbar.

---

## Inhalt

1. [Grundphilosophie](#1-grundphilosophie)
2. [Start, Datenverzeichnis & portabler Betrieb](#2-start-datenverzeichnis--portabler-betrieb)
3. [Erste Schritte](#3-erste-schritte)
4. [Oberfläche: Modi, Module, Navigation](#4-oberfläche-modi-module-navigation)
5. [Dashboard im Detail](#5-dashboard-im-detail)
6. [Füllerverwaltung](#6-füllerverwaltung)
7. [Tintenverwaltung](#7-tintenverwaltung)
8. [Federn & Papier](#8-federn--papier)
9. [Rotation & Vorschläge im Detail](#9-rotation--vorschläge-im-detail)
10. [Die Regel-Engine](#10-die-regel-engine)
11. [Full-Auto-Modus (Expertensystem)](#11-full-auto-modus-expertensystem)
12. [Ink Safety Timer](#12-ink-safety-timer)
13. [Ausgaben & Sammlerwert](#13-ausgaben--sammlerwert)
14. [Wishlist](#14-wishlist)
15. [Statistiken & Schreibproben](#15-statistiken--schreibproben)
16. [Enthusiasten-Lab](#16-enthusiasten-lab)
17. [Recherche & Referenzdaten](#17-recherche--referenzdaten)
18. [Einstellungen – alle Seiten](#18-einstellungen--alle-seiten)
19. [Mehrsprachigkeit](#19-mehrsprachigkeit)
20. [Updates](#20-updates)
21. [Datensicherung & Umzug](#21-datensicherung--umzug)
22. [Fehlerbehebung & FAQ](#22-fehlerbehebung--faq)
23. [Referenz](#23-referenz)
24. [Glossar](#24-glossar)

---

## 1. Grundphilosophie

Der FountainPen Manager ist keine reine Sammlungsdatenbank, sondern eine Plattform für die **tägliche Nutzung, Pflege und Werterhaltung** von Füllfederhaltern. Drei Grundsätze ziehen sich durch alle Funktionen:

1. **Die Engine empfiehlt – du entscheidest.** Jede automatische Entscheidung ist übersteuerbar. Warnungen dürfen ignoriert werden, Doppelbelegungen sind erlaubbar, und ein Override-Log macht Übersteuerungen nachvollziehbar.
2. **Schutz vor Schaden ist die einzige harte Grenze.** Kombinationen, die einen Füller beschädigen könnten (z. B. Shimmer-Tinte im Vakuumfüller), werden blockiert markiert und im Zufallsmodus nie vorgeschlagen – es sei denn, du hast sie als feste Paarung bewusst gesetzt.
3. **Offline zuerst.** Die App funktioniert vollständig ohne Internet. Online geht sie nur auf ausdrücklichen Klick (Recherche, Updates) und niemals im Hintergrund.

---

## 2. Start, Datenverzeichnis & portabler Betrieb

### 2.1 Wo liegen meine Daten?

Beim Start bestimmt die App ihr **Datenverzeichnis** nach dieser Priorität:

1. **Umgebungsvariable `FPM_DATA_DIR`** – für portable Starter (z. B. USB-Stick): Setze die Variable auf einen Ordner deiner Wahl, und alles bleibt dort.
2. **`installation.json` neben der App** – bei Installer-Builds; die Datei verweist auf das gewählte Datenverzeichnis.
3. **`~/.fpm_data`** – der Standard für Quell-/Entwicklerinstallationen (im Benutzerordner).

### 2.2 Was liegt im Datenverzeichnis?

| Datei/Ordner | Zweck |
|---|---|
| `fpm.db` (SQLite) | Die komplette Datenbank: Füller, Tinten, Regeln, Einstellungen, Logs |
| `images/pens/` | Hochgeladene bzw. heruntergeladene Füllerbilder |
| `pen_dimensions_cache.json` | Bestätigte Maße/Referenzdaten aus der Online-Recherche |
| `manufacturer_domains.json` | *Optional, von dir anlegbar:* eigene Hersteller-Domains (siehe Kap. 17.4) |

Ein Backup des Datenverzeichnisses sichert **alles** (siehe Kap. 21).

### 2.3 Erststart

Beim ersten Start legt die App eine **leere Sammlung** mit Standard-Einstellungen und Standard-Regeln (Kap. 23.2) an. Es werden bewusst keine Beispiel-Tinten und keine Beispiel-Füller mehr eingespielt.

Die geführte Einrichtung beginnt mit einer vollständigen **Modulrunde**:

1. Dashboard, Füller, Tinten, Rotation, Hilfe und Einstellungen kennenlernen;
2. am Schluss der Runde vorübergehend die Expertenmodule öffnen: Federn, Papier, Schreibproben, Wishlist, Ausgaben, Statistik, Regeln und Enthusiasten-Labor;
3. anschließend gemeinsam die **erste Tinte** anlegen;
4. den **ersten Füller** und optional einen zweiten Füller anlegen;
5. einen echten Rotationsvorschlag erzeugen, dessen Score lesen und den Vorschlag bewusst als erste Befüllung übernehmen.

Der ursprüngliche Einfach-/Expertenmodus wird nach der Führung automatisch wiederhergestellt. Wird ein Erfassungsdialog abgebrochen, bleibt die Führung am aktuellen Schritt. Der optionale zweite Füller kann übersprungen werden. Die gesamte Führung lässt sich abbrechen und später über Hilfe oder Einstellungen erneut starten.

---

## 3. Erste Schritte

Die empfohlene Reihenfolge, damit alle Systeme sinnvoll arbeiten:

1. **Tinte anlegen**. Wichtig für gute Vorschläge: Farbfamilie, Shimmer/Pigment/Wasserfest-Flags und Reinigungsaufwand ehrlich pflegen.
2. **Federn** optional als eigene Objekte anlegen oder direkt am Füller hinterlegen.
3. **Füller anlegen**, Feder zuweisen, Füllsystem wählen, ggf. Tags (Grail, Vintage …) setzen.
4. **Einen Füller befüllen** – ab jetzt laufen Safety Timer und Regelprüfung.
5. **Rotationsseite öffnen → „💡 Vorschläge“ klicken** und per Klick auf eine Zeile befüllen. Ab hier arbeitet die App *für* dich.

Solange noch eine Tinte **oder** ein Füller fehlt, zeigt das Dashboard ein Onboarding-Panel mit passenden Schnellaktionen. Zusätzlich startet beim ersten Programmstart die geführte Einrichtung. Für den Expertenteil schaltet sie den Modus kontrolliert und nur vorübergehend um; danach wird der vorherige Modus wiederhergestellt.

Die Schnellaktion **„Rotation vorschlagen“** erzeugt direkt neue Vorschläge. Sie öffnet nicht mehr nur die Rotationsseite.

---

## 4. Oberfläche: Modi, Module, Navigation

### 4.1 Einfach- und Expertenmodus

Der **Einfachmodus** (Standard) zeigt die sechs Kernbereiche: Dashboard, Füller, Tinten, Rotation, Hilfe, Einstellungen. Der **Expertenmodus** schaltet alle 14 Module frei. Umschalten: Button in der Seitenleiste oder Einstellungen → Darstellung. Der Modus wird gespeichert.

### 4.2 Die 14 Module (Expertenmodus)

| # | Modul | Kurzbeschreibung |
|---|---|---|
| 1 | Dashboard | Alarmzentrale & Überblick (Kap. 5) |
| 2 | Füller | Sammlung, Sammlerdaten, Maße, Bilder (Kap. 6) |
| 3 | Tinten | Bestand, Eigenschaften, Restmengen (Kap. 7) |
| 4 | Federn | Eigenständige Feder-Objekte, Grinds, Historie (Kap. 8) |
| 5 | Papier | Notizbücher/Papiere mit Eignungsprofilen (Kap. 8) |
| 6 | Rotation | Aktuelle Belegung + Vorschlags-Engine (Kap. 9) |
| 7 | Ausgaben | Käufe, Versand/Zoll, Wertdaten (Kap. 13) |
| 8 | Wishlist | Wunschliste mit Kauf-Übernahme (Kap. 14) |
| 9 | Regeln | Regel-Engine, Zeiten, Gruppen, Auto-Mode (Kap. 10/11) |
| 10 | Hilfe | Das In-App-Wiki inkl. Tour |
| 11 | Einstellungen | Neun Einstellungsseiten (Kap. 18) |
| 12 | Statistik | Auswertungen über Sammlung & Nutzung (Kap. 15) |
| 13 | Schreibproben | Proben je Füller/Tinte/Papier dokumentieren (Kap. 15) |
| 14 | Enthusiasten-Lab | Bestands-, Lücken- und Pflege-Analysen (Kap. 16) |

### 4.3 Globale Suche & Bedienung

Die Werkzeugleiste enthält eine **globale Suche** über die Sammlung. Listen bieten durchgängig **Kontextmenüs** (Rechtsklick) für die häufigsten Aktionen; Dialoge sind auf schnelle Dateneingabe optimiert. Tabellen mit Score-Spalten zeigen per Klick auf den Score eine „Warum“-Erklärung (Kap. 9.4).

---

## 5. Dashboard im Detail

Das Dashboard ist bewusst eine **Alarmzentrale**, keine Inventarliste. Von oben nach unten:

**Onboarding-Panel** – nur sichtbar, solange weder Füller noch Tinten existieren.

**Schnellaktionen** – Füller eintragen, Tinte eintragen, Füller befüllen, Reinigung eintragen.

**Vier Karten:**
- **Aktive Füller**: Anzahl aktuell befüllter Füller. Tooltip zeigt Gesamt-/Archivbestand.
- **Tinten**: Anzahl aktiver (nicht archivierter, nicht leerer) Tinten.
- **Warnungen**: Summe aus überfälligen Safety-Timer-Ladungen und aktuellen Regelverstößen der Belegung.
- **Sammlungswert**: Gesamtwert nach hinterlegten Wertdaten (Kap. 13), in deiner Anzeigewährung.

**Bestandszeile** (grau, unter den Karten): „Bestand: X Füller (Y archiviert) · Z Tinten archiviert · N im Service/gesperrt“ – die Detailzahlen, ohne eigene Karten zu belegen.

**Budget-/Sparziele**: Kompakttabelle der BM-Ziele, falls gepflegt.

**⏱ Ink Safety Timer**: Zeigt **nur** überfällige und *bald fällige* Ladungen. „Bald fällig“ heißt: erreichte Tage ≥ **80 %** der Maximaltage dieser Ladung (Berechnung der Maximaltage: Kap. 12). Der Abschnittstitel nennt beide Zähler. Alles „Grüne“ steht vollständig auf der Rotationsseite unter „Aktuelle Belegung“ – es *fehlt* nicht, es ist nur kein Alarm.

**🔒 Service & Sperren**: Füller im Service, mit Problemstatus oder Rotationssperre; Titel mit Zähler.

**Sammlungs-Advisor**: Bis zu 6 Gesundheits-Hinweise zur Sammlung (z. B. lange ungenutzte Füller).

**Letzte Einfüllungen**: Die 8 jüngsten Befüllungen als Aktivitätsprotokoll.

Sind alle Alarmbereiche leer, erscheint stattdessen eine „Alles im grünen Bereich“-Meldung. Leere Abschnitte werden komplett ausgeblendet.

---

## 6. Füllerverwaltung

### 6.1 Stammdaten & Felder

Pro Füller: Marke, Modell, Farbe/Finish, Kaufdaten (Datum, Preis, Händler), **Füllsystem** (Kolben, Vakuum, Konverter, Patrone, Eyedropper), Feder (verknüpftes Feder-Objekt oder Direktangabe), Kommentarfelder für Schreibgefühl, Probleme und Reinigung.

### 6.2 Tags & Status

- **Tags**: frei kombinierbar, u. a. *Grail*, *Problemfüller*, *Sammlerstück*, *Vintage*. Tags wirken in Regeln (z. B. verkürzt „grail“ das Reinigungsintervall, Kap. 12) und in der Rollen-Erkennung (Kap. 9.2).
- **Verfügbarkeitsstatus**: *verfügbar*, *im Service*, *gesperrt* u. a. Füller im Service oder gesperrt erscheinen weiterhin unter „Aktuelle Belegung“, werden aber **nie** für neue Befüllungen vorgeschlagen.
- **Rotationssperre**: nimmt einen Füller gezielt aus den Vorschlägen, ohne Statuswechsel.
- **Archivieren** statt löschen: Der Füller verschwindet aus allen aktiven Listen, bleibt aber mit Historie erhalten.

### 6.3 💍 Feste Paarung & ⭐ Pflicht-Füller

- **Feste Paarung** („Verheiratung“): Dieser Füller bekommt in Vorschlägen immer genau diese Tinte. Sie ist von Reroll-Sperren und vom Zufallsmodus ausgenommen und – als bewusste Nutzerentscheidung – sogar von der Blockade-Abwertung (Override-Prinzip). Der Farbfamilien-Malus entfällt für feste Paarungen ebenfalls.
- **Pflicht-Füller** („muss in Rotation“): bekommt bei der Slot-Vergabe immer zuerst einen Platz (Kap. 9.3, Pass 1); die Tintenwahl bleibt frei.

### 6.4 Bilder

Bilder lassen sich per Dateiauswahl hinzufügen; die App legt sie unter `images/pens/` im Datenverzeichnis ab. Der Button **„Bilder suchen“** öffnet die dreistufige Bild-Kaskade im Browser: **zuerst die Hersteller-Domain**, dann die Google-KI-Suche, dann die offene Bildersuche (Details Kap. 17.3). Die Maße-Suche nutzt bewusst die umgekehrte Reihenfolge (KI zuerst). Ein gefundenes Bild kannst du per URL übernehmen; die App lädt es in ihr Bildverzeichnis herunter.

### 6.5 Abmessungen & Referenzdaten

Speicherbar: Länge (geschlossen/aufgesteckt), Durchmesser, Gewicht, Tintenkapazität. Der Button **„Maße suchen“** startet die dreistufige Recherche (lokaler Cache → Herstellerseite → offenes Netz, Kap. 17). Wichtig: Vorschläge werden **vor** der Übernahme angezeigt und füllen **nur leere Felder** – manuell eingetragene Werte werden nie überschrieben. Bestätigte Treffer landen im lokalen Cache und sind beim nächsten Füller desselben Modells sofort da.

### 6.6 Visueller Größenvergleich

Der Größenvergleich stellt mehrere Füller **maßstabsgetreu** gegenüber – nützlich vor einem Kauf oder zur Einordnung eines Neuzugangs.

- **Modus „Überlagert“**: Alle gewählten Füller liegen als stilisierte Silhouetten übereinander, gemeinsame Grundlinie und Lineal. Unterschiede in Länge und Durchmesser springen sofort ins Auge.
- **Modus „Zeilen“**: Jeder Füller in eigener Zeile, ebenfalls mit Lineal – die bessere Wahl bei vielen Füllern.
- **Metrik**: *Beste verfügbare*, *Geschlossen*, *Ohne Kappe* oder *Aufgesteckt*. „Beste verfügbare“ nimmt je Füller den vorhandenen Wert in dieser Reihenfolge und beschriftet, welcher verwendet wurde.

Voraussetzung sind gepflegte Maße (Kap. 6.5). Füller ohne passenden Messwert werden übersprungen statt geraten.

### 6.7 Verwaltete Medien

Bilder und Schreibproben liegen in einer strukturierten Ablage unterhalb von `media/` im Datenverzeichnis – pro Füller ein eigener, aus ID/Marke/Modell abgeleiteter Ordner. Übernommene Dateien und Downloads werden dorthin kopiert bzw. geladen (Obergrenze **15 MB** je Datei, Pfad-Ausbruch wird verhindert). Vorteil: Ein Backup des Datenverzeichnisses enthält alle Medien; Umbenennungen der Quelldateien brechen nichts.

---

## 7. Tintenverwaltung

### 7.1 Stammdaten

Marke, Name, Farbtyp (Freitext), **Farbfamilie** (normiert, z. B. blue/teal/green – Grundlage der Farbspektrum-Logik), Farbwert (Hex), Flaschengröße, Kaufpreis.

### 7.2 Eigenschaftsprofil

Jeweils als Stufen bzw. Flags: Nass-/Trockenverhalten (wetness), Fluss (flow), Sättigung, **Sheen** (mit Stufe und Sheen-Farbe), **Shimmer**, Shading, Feathering-Neigung, **Pigment**, **Wasserfest**, **Reinigungsaufwand** (1–5). Diese Werte speisen Regeln, Rollen-Matching und den Safety Timer – je ehrlicher gepflegt, desto besser die Vorschläge.

### 7.3 Individuelle Standzeit

`Max. Tage im Füller` überschreibt für diese Tinte **alle** Kategorie-Standardzeiten des Safety Timers (Kap. 12). Beispiel: Eine extrem sheen-lastige Tinte kann individuell auf 14 Tage gesetzt werden.

### 7.4 Restmenge & leere Flaschen

Beim Befüllen zieht die App das Befüllvolumen zentral von der Restmenge ab; negative Restmengen sind ausgeschlossen. Erreicht die Flasche 0, wird sie als **leer** markiert und aus allen Vorschlägen genommen. Leere und archivierte Tinten bleiben in der Historie sichtbar.

### 7.5 Doppelbelegung

Standardmäßig wird eine bereits **aktive** Tinte (steckt gerade in einem Füller) nicht erneut vorgeschlagen – dieselbe Flasche in zwei Füllern ist ein Verbrauchs-/Sammlerrisiko. Über Einstellungen → Rotation & Vorschläge → „Gleiche Tinte in mehreren Füllern erlauben“ lässt sich das bewusst freischalten; feste Paarungen dürfen es immer.

---

## 8. Federn & Papier

### 8.1 Federn

Federn sind optional eigenständige Objekte: Hersteller (Bock, Jowo, Schmidt, Pilot …), Größe, Schliff, **Custom Grinds** mit Nibmeister-Angabe, Feedback-/Kratz-Notizen. Eine Feder kann Füllern zugewiesen werden; das Enthusiasten-Lab führt eine Feder-Historie (Kap. 16). Die Federgröße fließt in Rollen-/Themen-Matching ein (z. B. bevorzugt eine EF-Rolle fließende Tinten).

### 8.2 Papier

Notizbücher/Papiere mit Gewicht, Oberfläche, Sheen-/Shading-Eignung, Feathering-/Bleedthrough-Bewertung und EDC-Kennzeichnung. Auf der Rotationsseite kannst du ein Papier als **Kontext** wählen: Der Papier-Score-Anteil bewertet dann, wie gut Tinte und Papier zusammenpassen (z. B. Sheen-Tinte auf sheen-tauglichem Papier).

---

## 9. Rotation & Vorschläge im Detail

Das Herzstück. Die Seite hat zwei Bereiche: **Aktuelle Belegung** (alle befüllten Füller mit Tagen/Max/Score/Hinweisen) und **Vorschläge**.

### 9.1 Ablauf

1. Slots wählen (1–30), optional **Papier** und **Thema** als Kontext.
2. **„💡 Vorschläge“** klicken → die Engine bewertet jede Kombination aus *leerem, verfügbarem* Füller × *aktiver* Tinte.
3. Klick auf eine Zeile → Befüll-Dialog (Volumen, Bestätigung, Regel-Übersteuerung falls nötig).
4. Für bereits befüllte Füller gibt es **„Leeren + Befüllen“**: Die Empfehlungsliste für den Nachfüll-Dialog nutzt dieselbe Engine (gleiche Sortierlogik, aktuelle Tinte ausgeschlossen).

Automatisch **ausgelassen** werden: Füller mit Rotationssperre oder blockierendem Status (Service etc.), bereits befüllte Füller, leere/archivierte Tinten sowie – standardmäßig – bereits aktive Tinten (Kap. 7.5).

### 9.2 Der Score: alle Faktoren (Werkseinstellung)

Der Score startet bei der Regel-Basis und summiert Kontextfaktoren:

| Faktor | Wert | Erläuterung |
|---|---|---|
| Regel-Basis | 100 ± Regelwirkung | `RuleEngine.score`: weiche Regeln geben Boni/Mali auf die Basis 100; der Why-Dialog zeigt die Abweichung als „Regel-Delta“ |
| Leerer Füller | **+120** | Leere Füller sollen zuerst versorgt werden |
| Füller-Standzeit | **+0…+80** | Tage seit letzter Nutzung ÷ 2, gedeckelt bei 80 („nie benutzt“ = 80) |
| Tinten-Standzeit | **0/10/25/50/75/90** | Staffel: <14 T = 0 · ≥14 T = 10 · ≥30 T = 25 · ≥90 T = 50 · ≥180 T = 75 · nie = 90 |
| Farbfamilie | **+14 / −18** | Neue Familie im aktiven Spektrum +14; bereits aktive Familie −18; bei fester Paarung 0 |
| Reinigung/Sicherheit | variabel | Zuschläge/Abzüge aus Reinigungsaufwand vs. Füllsystem |
| Papier-Kontext | variabel | Nur wenn ein Papier gewählt ist |
| Rolle | variabel | Passung der Tinte zur erkannten Füller-Rolle (Kap. 9.2.1) |
| Thema | variabel | Passung zum gewählten Thema (z. B. `sheen_showcase`) |
| Aktive Doppel-Tinte | **−22** | Nur relevant, wenn Doppelbelegung erlaubt ist |
| Blockierende harte Regel | **→ max. −50** | Score wird auf höchstens −50 gedeckelt (außer feste Paarung) |
| Full-Auto-Reject | **→ max. −999** | Praktisch aus dem Rennen |

**9.2.1 Rollen:** Jeder Füller bekommt eine Rolle – explizit gesetzt oder aus Tags/Feder abgeleitet. Verfügbare Rollen (anpassbar unter Rotation → Rollen-Editor): `writer, edc, agenda, journal, work, creative, letter, collector, vintage, problem, fine, broad, must`. Jede Rolle definiert Zielkorridore (z. B. Nässe, Reinigungsaufwand) und Ziel-Tags; die Tintenpassung ergibt das Rollen-Delta. Hinweis: Eine explizit gesetzte Rolle „writer“ gilt als *nicht autoritativ* – Tags oder die Feder können sie präzisieren.

**9.2.2 Score-Ampel in der Tabelle:** grün ≥ 100 (sehr passend), orange < 0 (eher ungünstig), **rot** = blockierende Schutzregel liegt an.

### 9.3 Auswahlverfahren (aus Kandidaten werden Slots)

Nicht einfach „Top N nach Score“, sondern ein zweistufiges Verfahren mit Farbdiversität:

- **Pass 1 – Pflicht & Verheiratung:** Füller mit ⭐ oder 💍 werden zuerst bedient. Bei fester Paarung wird **immer die feste Tinte** gewählt, selbst wenn eine andere knapp höher läge.
- **Pass 2 – Rest nach effektivem Score:** Pro Füller gewinnt die Tinte mit dem besten *effektiven* Score. Effektiv = Roh-Score **+ Diversitätsbonus 0–30** (je größer der Farbabstand zu bereits gewählten Tinten) **− 30 In-Batch-Familien-Malus** (Familie schon im aktuellen Vorschlagssatz).
- Jeder Füller max. 1×, jede Tinte max. 1× pro Vorschlagssatz.

### 9.4 Der „Warum“-Dialog

Klick auf einen Score öffnet die vollständige Aufschlüsselung: alle Deltas aus 9.2, Diversitätsbonus/Familien-Malus, Zufalls-Delta (falls aktiv) und die ausgelösten Regeln. So bleibt jede Empfehlung nachvollziehbar.

### 9.5 Reroll: „Nochmal klicken = andere Vorschläge“

Jeder weitere Klick auf „💡 Vorschläge“ **meidet hart** alle bereits gezeigten (Füller, Tinte)-**Paare** – kumulativ über die Sitzung. Dadurch rotierst du systematisch durch die Sammlung:

- **Paar- statt Tintensperre:** Eine gezeigte Tinte bleibt für *andere* Füller wählbar.
- **Pro-Füller-Neustart:** Hat ein Füller alle seine Kandidaten gesehen, beginnt *nur für ihn* automatisch eine neue Runde – erkennbar am 🔁-Hinweis. Kein Füller geht leer aus, nur weil die Historie voll ist.
- **Feste Paarungen** sind von der Sperre ausgenommen (💍 gewinnt immer).
- Der Button-Tooltip erinnert an dieses Verhalten.

### 9.6 🎲 Zufälligkeit dosieren

Einstellungen → Rotation & Vorschläge → **Zufälligkeit (0–100 %)**:

- Formel pro Kandidat: `Score_neu = Score · (100−p)/100 + Jitter · p/100` mit Jitter aus **±140** (kryptografischer Zufall). Bei 100 % besteht der Score praktisch nur noch aus dem Jitter → echte Zufallsauswahl.
- **Sicherheitsfilter in jedem Zufallsgrad:** Kombinationen mit blockierender harter Regel **oder** Full-Auto-Reject werden vor dem Würfeln aussortiert – ausgenommen feste Paarungen (Override-Prinzip).
- 💍/⭐ bleiben strukturell garantiert, weil Pass 1 des Auswahlverfahrens (9.3) unabhängig vom gejitterten Score zuerst greift.
- Aktiver Zufall ist sichtbar: Hinweis „🎲 Zufall p %“ an jedem Vorschlag, Prozentangabe in der Zusammenfassungszeile, Zufalls-Delta im Warum-Dialog.

---

## 10. Die Regel-Engine

### 10.1 Regeltypen & Warnstufen

- **Harte Regeln** schützen den Füller. Auf Stufe *Blockiert* deckeln sie den Score (→ −50) und sind im Zufallsmodus tabu; übersteuern bleibt im Befüll-Dialog möglich (mit Log).
- **Weiche Regeln** sind Empfehlungen: Sie verschieben nur den Score und erzeugen Hinweise.
- **Warnstufen:** 🔵 Info · 🟠 Warnung · 🔴 Kritisch · ⛔ Blockiert.

### 10.2 Die Regelseite (4 Tabs)

Oben auf der Seite fasst ein Kurzlogik-Panel das System zusammen. Die Tabs:

1. **Zeiten** – die vier Standard-Reinigungsintervalle (Kap. 12).
2. **Auto-Mode** – das Expertensystem (Kap. 11).
3. **Regelgruppen** – ganze Gruppen (Safety, Wartung, Rotation, Füller, Tinte, Befüllung, Verbrauch, Feder, Papier …) per Schalter aktiv/inaktiv; die Verbrauchsgruppe ist ab Werk aus.
4. **Regelliste** – alle Regeln mit Suche, **Gruppen- und Warnstufen-Filter**. Spalten: Aktiv (✓, Doppelklick schaltet), *Wirksam* (berücksichtigt auch den Gruppenschalter: „Nein (Gruppe aus)“), Name, Gruppe, Typ, Stufe, Bedingung. Eigene Regeln lassen sich anlegen und bearbeiten (Bedingungstyp, Zielwerte, Stufe, Typ).

### 10.3 Override & Log

Jede Warnung – auch ⛔ – kann beim Befüllen bewusst übersteuert werden. Übersteuerungen werden im **Override-Log** festgehalten (wer/was/wann/welche Regel), damit Entscheidungen nachvollziehbar bleiben.

---

## 11. Full-Auto-Modus (Expertensystem)

Für Nutzer, die der Engine mehr Autonomie geben wollen (Regeln-Tab „Auto-Mode“). Vier Einstellungen (Werkszustand in Klammern):

- `full_auto_mode` (aus): Aktiviert die automatische Entscheidung.
- `full_auto_can_reject` (**an**): Bei blockierenden Verstößen darf die Engine eine Kombination komplett **ablehnen** („reject“) – sie fällt aus Vorschlägen praktisch heraus (Score → −999) und ist im Zufallsmodus gefiltert.
- `full_auto_can_override` (aus): Alternativ darf die Engine statt Ablehnung eine **Pflicht-Übersteuerung** anfordern („require_override“) – du musst aktiv bestätigen.
- `full_auto_logging` (an): Auto-Entscheidungen werden protokolliert.

Entscheidungslogik je Kombination: *allow* (nichts anliegend) · *warn* (weiche Verstöße) · *reject* bzw. *require_override* (blockierende Verstöße, je nach Rechten). Wichtig: Auch der Full-Auto-Reject respektiert feste Paarungen nicht als Verbot deiner Entscheidung – 💍 bleibt deine Hoheit.

---

## 12. Ink Safety Timer

Überwacht die Standzeit jeder Befüllung und mahnt Reinigung an, bevor Tinte im Füller eintrocknet oder Pigmente verkleben.

**Berechnung der Maximaltage einer Ladung:**

1. Hat die **Tinte** einen individuellen Wert `Max. Tage im Füller`? → dieser gilt, Punkt.
2. Sonst Start bei `cleaning_days_normal` (**28**) und dann das **Minimum** aller zutreffenden Kategorien:
   - Tinte hat **Shimmer** → min mit `cleaning_days_shimmer` (**14**)
   - Tinte ist **Pigment** *oder* **wasserfest** → min mit `cleaning_days_pigment` (**10**)
   - Füller trägt Tag **„grail“** → min mit `cleaning_days_grail` (**21**)

Beispiel: Wasserfeste Shimmer-Tinte im Grail-Füller → min(28, 14, 10, 21) = **10 Tage**.

Alle vier Werte sind unter Regeln → Zeiten einstellbar. **Anzeige:** „Aktuelle Belegung“ zeigt Tage/Max je Ladung; das Dashboard alarmiert ab **80 %** („bald fällig“) bzw. bei Überschreitung („überfällig“); überfällige Ladungen zählen in die Warnungen-Karte.

---

## 13. Ausgaben & Sammlerwert

Pro Objekt erfassbar: Kaufpreis, **Versand**, **Zoll**, Zahlungsart, Händler, Datum – getrennt nach Positionstypen (Füller, Tinte, Feder, Papier, Zubehör). Zusätzlich je Füller: **aktueller Marktwert** und **Versicherungswert**; daraus entstehen Wertentwicklung und der **Gesamtwert der Sammlung** (Dashboard-Karte). Die Ausgabenseite zeigt Summenkarten und Listen mit Filtern; Ausgaben synchronisieren die Wertfelder des Füllers. Anzeigewährung und Formatierung folgen Kap. 18 (Standard: CHF, Schweizer Format mit Apostroph-Tausendertrennung).

---

## 14. Wishlist

Wunschliste mit Typ (Füller/Tinte/…), Status (z. B. beobachtet, geplant, gekauft), Zielpreis und Notizen. Der **Kauf-Flow** übernimmt einen Wishlist-Eintrag direkt in die Sammlung samt Ausgabenerfassung – Status wandert auf „gekauft“, nichts wird doppelt getippt.

---

## 15. Statistiken & Schreibproben

**Statistik:** Auswertungen über Sammlung und Nutzung – Verteilungen (Marken, Farbfamilien, Füllsysteme), Nutzungshäufigkeit, Ausgabenverlauf, Wertentwicklung.

**Schreibproben:** Dokumentiere Proben als Kombination Füller × Tinte × Papier mit Notizen – die Erinnerungsstütze, *warum* eine Kombination gut oder schlecht war.

---

## 16. Enthusiasten-Lab

Vier Analyse-Tabs für den Sammlerblick:

1. **Tintenbestand** – Restmengen-Übersicht, Verbrauchssicht, leere Flaschen.
2. **Farb-Lücken** – welche Farbfamilien im Bestand unter- oder überrepräsentiert sind: die Einkaufsliste für das Spektrum.
3. **Feder-Historie** – welche Feder wann in welchem Füller steckte, inkl. Grind-Daten.
4. **Reinigung** – Pflegeübersicht: was wann zuletzt gereinigt wurde, was ansteht.

---

## 17. Recherche & Referenzdaten

### 17.1 Grundprinzip

Die Suchreihenfolge ist absichtlich je nach Aufgabe unterschiedlich: Die sichtbare **Maße-Suche startet mit der KI-Suche**, während die sichtbare **Bildersuche beim Hersteller beginnt**. Der automatische Parser für technische Referenzdaten arbeitet weiterhin hersteller-zuerst. Die App kennt dafür ~46 Marken mit ihren offiziellen Domains – teils mehrere pro Marke (z. B. Pilot EU **und** US). Das Marken-Matching ist token-basiert mit Längster-Treffer-Logik („Graf von Faber-Castell“ trifft nie den bloßen „Faber-Castell“-Eintrag; „Crossfield“ trifft nicht „Cross“).

### 17.2 Ablauf der Maße-Suche (Button „Maße suchen“)

1. **Lokaler Cache** (`pen_dimensions_cache.json`): Modell schon bestätigt? → sofortiges Ergebnis, offline.
2. **Herstellerphase(n)**: gezielte `site:`-Suche je bekannter Domain – bewusst **nur mit dem Modellnamen** (z. B. `site:faber-castell.com Essetio`): Jedes zusätzliche Pflichtwort würde echte Produktseiten aussieben, weil Suchmaschinen alle Begriffe gleichzeitig verlangen; die Voll-Suchphrase bleibt der offenen Netzphase vorbehalten; **nur Links dieser Domain** (inkl. Subdomains wie `shop.pelikan.com`) werden geladen und konservativ ausgewertet. Treffer heißen `manufacturer:<domain>`. Ein Herstellertreffer mit Konfidenz ≥ 0.65 beendet die Suche vor Shop-/Forenrauschen.
3. **Offenes Netz** nur bei leerer Herstellerphase; Treffer heißen `online:<domain>`.

Vorschläge werden angezeigt, nie automatisch übernommen; Übernahme füllt nur leere Felder; Bestätigtes wandert in den Cache. Ohne Internet liefert die Suche schlicht keine Online-Treffer – die App bricht nicht.

### 17.3 Bildersuche

Beide Recherche-Buttons öffnen eine **dreistufige Kaskade** – die Reihenfolge ist bewusst **unterschiedlich**, weil sich die Ziele unterscheiden:

**Maße suchen (KI zuerst):**

1. **KI-Stufe** – Google-Suche im KI-Modus (`udm=50`) mit natürlichsprachigem Prompt. Die KI-Übersicht trägt technische Daten aus mehreren Quellen zusammen und nennt sie – für Zahlen der schnellste Weg.
2. **Hersteller-Stufe** – `site:<hersteller-domain> <Modell>`, je bekannter Domain eine Suche. Bleibt als belastbare Primärquelle erhalten, falls die KI ungenau ist oder Quellen fehlen.
3. **Web-Stufe** – klassische Google-/DuckDuckGo-Suche als Rückfallebene.

**Bilder suchen (Hersteller zuerst):**

1. **Hersteller-Stufe** – Bildersuche auf der/den Hersteller-Domain(s). Bei Produktfotos ist die offizielle Quelle das Ziel: korrekte Farbe, Finish und aktuelle Ausführung, nicht eine Zusammenfassung.
2. **KI-Stufe** – findet offizielle Fotos und nennt die Quellen.
3. **Offene Bildersuche** – Google Images, DuckDuckGo.

Die `site:`-Stufen tragen bewusst **nur den Modellnamen** (z. B. `site:faber-castell.com Essetio`): Jedes zusätzliche Pflichtwort und erst recht ein Exact-Phrase-Quoting würde echte Produktseiten aussieben, weil Suchmaschinen alle Begriffe gleichzeitig verlangen. Die Voll-Phrase bleibt den offenen Stufen vorbehalten.

Ist der KI-Modus für dein Konto/deine Region nicht verfügbar, öffnet Google eine normale Suche mit demselben Prompt – die Stufe bleibt also immer nützlich. Bei unbekannten Marken entfällt die Hersteller-Stufe ersatzlos.

**Der automatische Lookup** (Kap. 17.2) bleibt davon unberührt hersteller-zuerst: Er liest Seiten mit dem eigenen Parser, dort gibt es keine KI-Übersicht.

### 17.4 Eigene Marken: `manufacturer_domains.json`

Fehlt eine Marke oder stimmt eine Domain nicht, lege im **Datenverzeichnis** diese Datei an – kein Update nötig:

```json
{
  "Meine Marke": "meinemarke.example",
  "Pilot": ["pilotpen.eu", "pilotpen.com"]
}
```

- Wert = **ein** Domain-String **oder** eine **Liste** (Reihenfolge = Suchreihenfolge).
- Einträge hier **überschreiben** die eingebaute Liste (der Pilot-Eintrag oben ersetzt den mitgelieferten).
- Falsche Einträge sind unkritisch: die offene Websuche bleibt immer die letzte Stufe.

### 17.5 Grenzen (bewusst)

Die Recherche ist **kein Scraper**: Sie liest Textangaben konservativ und verweigert lieber, als zu raten. Händler-/Wiki-Seiten sind zu instabil für harte Automatik – deshalb Hersteller zuerst, Browser für den Rest, Cache für Bestätigtes.

---

## 18. Einstellungen – alle Seiten

| Seite | Inhalt |
|---|---|
| **⚙ Allgemein** | Sprache (DE/EN/FR), Grundverhalten, Modus-Startwahl |
| **🎲 Rotation & Vorschläge** | Zufälligkeit 0–100 % (Kap. 9.6), „Gleiche Tinte in mehreren Füllern erlauben“ (Kap. 7.5); Erklärnoten zu Sicherheit und Reroll; Änderungen wirken sofort |
| **🔎 Darstellung** | UI-Skalierung (auto/manuell), Einfach-/Expertenmodus, Darstellungsoptionen |
| **🌍 Währung & Region** | Anzeigewährung (Standard CHF), Zahlen-/Datumsformat (Standard Schweiz, Apostroph-Tausender), Wechselkurse für Fremdwährungskäufe |
| **💾 Datenbank & Backup** | Datenpfad, vollständiges `.fpmbackup` erstellen, validiertes Backup wiederherstellen, Datenordner öffnen und Datenbank optimieren |
| **📤 Import / Export** | Datenübernahme; CSV-/PDF-Export ist als Ausbau vorgesehen |
| **⚠ Reset / Gefahrenzone** | Zurücksetzen einzelner Bereiche oder der ganzen Datenbank – mit Sicherheitsabfragen |
| **⬆ Updates** | Update-Prüfung gegen GitHub Releases (Kap. 20) |
| **ℹ Über** | Version, Build, Lizenz-/Projektinfos |

### 18.1 Dezimalzeichen und Währungen

Die App verwendet **nicht ungeprüft die Sprache oder das Betriebssystem**, sondern die unter **Währung & Region** gewählte Region:

| Region | Beispiel |
|---|---|
| Schweiz | `CHF 1'234.56` |
| Deutschland / Österreich | `1.234,56 EUR` |
| Frankreich | `1 234,56 EUR` |
| Grossbritannien / USA | `GBP 1,234.56` / `USD 1,234.56` |

In editierbaren Zahlenfeldern werden aus Gründen der sicheren Eingabe keine Tausenderzeichen eingefügt. **Komma und Punkt werden beide akzeptiert.** Dadurch bleibt `39,96` ebenso wie `39.96` der Wert 39,96 und kann nicht versehentlich zu `3996` werden. Nach dem Verlassen des Feldes erscheint der Wert im gewählten Regionalformat.

Sprache und Region sind getrennt: Eine deutsche Oberfläche kann weiterhin die Region Schweiz verwenden und zeigt dann `CHF 39.96`. Dezimal- und Tausendertrennzeichen dürfen nicht identisch sein. Als Tausenderzeichen stehen Apostroph, Punkt, Komma, Leerzeichen oder „keines“ zur Verfügung; „keines“ und das französische Leerzeichen bleiben auch nach einem Neustart erhalten.

Die Währungsauswahl bleibt in jeder Sprache identisch: `CHF`, `EUR`, `USD`, `GBP`. Wechselst du die Währung neben einem Betrag, aktualisiert sich der Währungscode im Betragsfeld sofort. Datenbank und CSV-Export speichern Zahlen technisch mit Dezimalpunkt; das ist absichtlich unabhängig von der Darstellung. Beim CSV-Import versteht die App beide Dezimalzeichen sowie gängige Währungssymbole.

**Hinweis zu älteren Daten:** Frühere englische/französische Builds konnten in einzelnen Auswahlfeldern `CHF` falsch als `USD` bzw. `EUR` anzeigen. Neue und erneut gespeicherte Einträge sind behoben. Bereits historisch falsch gespeicherte Währungen können nicht sicher automatisch erraten werden und sollten bei betroffenen Einträgen einmal kontrolliert werden.

---

## 19. Mehrsprachigkeit

Alle sichtbaren Texte kommen aus externen Sprachdateien (DE/EN/FR, je ~2000 Schlüssel, automatisch auf Parität geprüft). Sprachwechsel unter Einstellungen → Allgemein; die Oberfläche übersetzt live, auch dynamisch erzeugte Dialoge. Fachbegriffe wie *Sheen*, *Shimmer*, *Reroll* bleiben bewusst sprachinvariant.

---

## 20. Updates

Die App prüft **nur auf Klick** (Einstellungen → Updates) gegen die offiziellen GitHub-Releases (`https://github.com/sloogy/FPM/releases`) anhand eines Manifests (`latest.json`). Es gibt keine stille Hintergrundverbindung. Portable Nutzer ersetzen einfach den Programmordner; das Datenverzeichnis bleibt unberührt.

---

## 21. Datensicherung & Umzug

### 21.1 Vollbackup in der App

Unter **Einstellungen → Datenbank & Backup → Vollbackup erstellen** erzeugt die App eine Datei mit der Endung `.fpmbackup`. Sie enthält:

- einen konsistenten SQLite-Snapshot der Datenbank;
- Füllerbilder, Schreibproben und weitere Medien;
- Cache- und Referenzdateien;
- Konfiguration und Hersteller-Overlay;
- ein Manifest mit Dateigrößen und SHA-256-Prüfsummen.

Vor Abschluss prüft die App das Archiv und die SQLite-Integrität. Vor einer Wiederherstellung wird automatisch ein zusätzliches Rückfall-Backup des aktuellen Zustands erstellt. Danach wird das ausgewählte Archiv nochmals validiert und erst dann eingespielt. Der lokale Datenbankpfad des Zielrechners bleibt erhalten.

### 21.2 Manuelle Sicherung und Umzug

Eine Kopie des gesamten Datenverzeichnisses bleibt eine vollständige manuelle Sicherung. Beende die App vorher, damit die SQLite-Datei nicht während des Kopierens verändert wird.

Für einen Umzug kopierst du entweder das Datenverzeichnis oder stellst ein `.fpmbackup` auf dem neuen Rechner wieder her. Bei portablem Betrieb zeigt `FPM_DATA_DIR` auf den gewünschten Ordner.

---

## 22. Fehlerbehebung & FAQ

**„Meine Befüllungen fehlen auf dem Dashboard.“** Sie fehlen nicht – der Safety Timer zeigt bewusst nur Fälliges/bald Fälliges (≥ 80 %). Vollständige Liste: Rotation → Aktuelle Belegung.

**„Die Vorschläge zeigen immer dieselbe Tinte.“** Prüfe, ob eine 💍 feste Paarung gesetzt ist (die gewinnt immer). Sonst: einfach erneut klicken – Reroll meidet gezeigte Paare.

**„Ein Füller taucht nie in Vorschlägen auf.“** Ist er befüllt, im Service, gesperrt oder rotationsgesperrt? Nur leere, verfügbare Füller werden vorgeschlagen.

**„Die Maße-Suche findet nichts.“** Ohne Internet keine Online-Treffer (gewollt). Sonst: Marke unbekannt? → Overlay anlegen (Kap. 17.4). Herstellerseite ohne Datenblatt? → die offene Netzphase läuft automatisch als Stufe 3.

**„Eine Warnung nervt.“** Regelseite: Regel per Doppelklick deaktivieren, Gruppe abschalten oder die Stufe der eigenen Regel senken. Einzelfall: im Befüll-Dialog übersteuern (wird geloggt).

**„100 % Zufall schlägt ‚verbotene‘ Kombis vor?“** Nein – blockierende Regeln und Auto-Rejects sind in jedem Zufallsgrad ausgefiltert. Ausnahme ist allein deine eigene feste Paarung.

**„Wo ändere ich die Reinigungsintervalle?“** Regeln → Zeiten (vier Werte, Kap. 12). Pro Tinte: Feld „Max. Tage im Füller“.

---

## 23. Referenz

### 23.1 Wichtige Einstellungs-Schlüssel (AppSettings)

| Schlüssel | Werk | Bedeutung |
|---|---|---|
| `rotation_randomness_percent` | 0 | Zufallsanteil der Vorschläge (0–100) |
| `rotation_allow_active_ink_duplicates` | 0 | Gleiche Tinte in mehreren Füllern |
| `cleaning_days_normal` | 28 | Standard-Standzeit |
| `cleaning_days_shimmer` | 14 | Standzeit Shimmer |
| `cleaning_days_pigment` | 10 | Standzeit Pigment/wasserfest |
| `cleaning_days_grail` | 21 | Standzeit Grail-Füller |
| `rules_enabled` | 1 | Regel-Engine global |
| `full_auto_mode` | 0 | Expertensystem an/aus |
| `full_auto_can_reject` | 1 | Auto darf ablehnen |
| `full_auto_can_override` | 0 | Auto darf Pflicht-Override anfordern |
| `full_auto_logging` | 1 | Auto-Entscheidungen loggen |
| `rule_group_consumption_enabled` | 0 | Verbrauchsregeln (ab Werk aus) |
| `ui_mode` | easy | Einfach-/Expertenmodus |
| `language` | de | Sprache |
| `locale_region` | CH | Zahlen-/Datumsformat |

### 23.2 Mitgelieferte Standard-Regeln

| Regel | Typ | Stufe |
|---|---|---|
| Shimmer-Tinte in Vac-Füller vermeiden | hart | ⛔ Blockiert |
| Pigmenttinte in Vac-Füller vermeiden | hart | ⛔ Blockiert |
| Shimmer-Tinte in Eyedropper | weich | 🟠 Warnung |
| EF-Feder: nasse Tinte bevorzugen | weich | 🔵 Info |
| Wasserfeste Tinte: Reinigungshinweis | weich | 🔵 Info |
| Grail-Füller: keine Shimmer-Tinte | weich | 🔴 Kritisch |
| Grail-Füller: keine schwer reinigbare Sheen-Tinte | weich | 🟠 Warnung |
| Stub/Flex: Sheen bevorzugen | Präferenz | 🔵 Info |

### 23.3 Dateien im Datenverzeichnis

Siehe Kap. 21. Merksatz: **Das `.fpmbackup` ist die geprüfte Standardsicherung; eine Kopie des geschlossenen Datenordners bleibt die manuelle Alternative.**

### 23.4 Score-Kurzreferenz

Siehe Tabelle in Kap. 9.2; Auswahl-Layer (+0–30 Diversität, −30 Batch-Familie) in Kap. 9.3; Zufallsformel in Kap. 9.6.

---

## 24. Glossar

**Blockiert (⛔)** – höchste Warnstufe harter Regeln; deckelt den Score und ist im Zufall tabu (außer 💍).
**EDC** – „Every Day Carry“; die täglich mitgeführten Füller. Als Rolle und Papier-Kennzeichen vorhanden.
**Effektiver Score** – Roh-Score plus Diversitätsbonus minus Batch-Familien-Malus (nur bei der Slot-Auswahl).
**Eyedropper** – Füllsystem, bei dem der Schaft direkt Tinte hält; empfindlich gegenüber Shimmer (weiche Warnregel).
**Feste Paarung (💍)** – verheiratete Füller-Tinte-Kombination; gewinnt gegen Reroll, Zufall und Blockade-Abwertung.
**Full-Auto** – Expertensystem, das Kombinationen automatisch erlauben/warnen/ablehnen darf (Kap. 11).
**Grail** – Tag für den „heiligen Gral“ der Sammlung; verkürzt u. a. die Standzeit (21 T) und triggert Schutzregeln.
**Jitter** – Zufallsanteil ±140, der bei aktivem Zufallsregler in den Score gemischt wird.
**Konfidenz** – Vertrauensmaß (0–1) eines Online-Recherche-Treffers; ≥ 0.65 vom Hersteller beendet die Suche.
**Override** – bewusstes Übersteuern einer Warnung; wird protokolliert.
**Pflicht-Füller (⭐)** – „muss in Rotation“; bekommt Slots immer zuerst.
**Pigmenttinte** – partikelbasierte Tinte; kurze Standzeit (10 T), hart geblockt im Vac.
**Reroll** – erneutes Klicken auf „💡 Vorschläge“; zeigt garantiert andere Paare (Kap. 9.5).
**Rolle** – Einsatzprofil eines Füllers (writer, edc, journal …); steuert die Tintenpassung.
**Sheen** – Glanz-Überfarbe satter Tinten auf geeignetem Papier.
**Shimmer** – Glitzerpartikel in Tinte; verkürzt Standzeit (14 T), hart geblockt im Vac.
**Standzeit** – Tage einer Tintenladung im Füller; Grundlage des Safety Timers.
**Vac / Vacuum** – Vakuumfüllsystem; groß im Volumen, aufwendig in der Reinigung.
**Warum-Dialog** – Klick auf einen Score; zeigt alle Score-Bestandteile.

---

*Ende des Handbuchs. Fragen, die hier fehlen? Die In-App-Hilfe (Wiki) deckt die Kurzform ab – und Lücken in diesem Leitfaden sind Bugs: bitte melden.*
