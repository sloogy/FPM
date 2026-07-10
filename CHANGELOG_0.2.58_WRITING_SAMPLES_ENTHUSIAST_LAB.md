# CHANGELOG v0.2.58 – Schreibproben & Enthusiasten-Labor

## Ziel

v0.2.58 baut FPM von einer reinen Inventar-/Rotationsverwaltung stärker zu einem echten Sammler- und Erfahrungsarchiv aus. Enthusiasten wollen nicht nur wissen, was sie besitzen, sondern welche Kombination aus Füller, Feder, Tinte und Papier wirklich funktioniert.

## Neu

- Neues Modul **Schreibproben** in der Seitenleiste.
- Scrivener-artiger Binder mit Gruppen:
  - Nach Füller
  - Nach Tinte
  - Nach Papier
  - Highlights
  - Prüfen
- Schreibproben können verknüpft werden mit:
  - Füller
  - Tinte
  - Papier
  - Feder
- Erfassbare Erfahrungswerte:
  - Textprobe
  - Foto/Scan-Pfad
  - Linienbreite
  - Trockenzeit
  - Feathering
  - Durchschlag
  - Shading
  - Sheen
  - Fluss
  - Feedback
  - Gesamtbewertung
  - Tags und Notizen
- Automatischer Titel aus der Kombination, damit neue Nutzer nicht an Pflichtdenken scheitern.
- Reine Logik in `logic/writing_sample_service.py` mit Regressionstests.
- Neue Tabelle `writing_samples`, bestehende Datenbanken werden nicht gelöscht.

## DAU-Freundlichkeit

- Leere Ansicht mit direktem Button.
- Suche über Titel, Füller, Tinte, Papier und Status.
- Problemstatus wird aus Messwerten abgeleitet.
- Fehlende Verknüpfungen sind erlaubt, aber im Binder unter „Prüfen“ sichtbar.

## Enthusiasten-Nutzen

- Lieblingskombinationen werden durch hohe Bewertung als Highlights sichtbar.
- Problemkombinationen werden erkennbar, ohne dass man alte Notizen suchen muss.
- Papier- und Tintenverhalten kann über echte Proben verglichen werden.
- Grundlage für spätere Features wie Galerie, Vergleichsansicht, Export-Karten oder Druckbogen.
