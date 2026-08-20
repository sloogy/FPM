# FountainPen Manager v0.2.94 – Laptop-Dashboard-Fix

## Gemeldetes Problem
Im Fenstermodus auf einem Laptop war das Dashboard zu hoch und zu breit aufgebaut. Teile der Seite waren nicht erreichbar; KPI-Karten und Schnellaktionen blieben starr nebeneinander.

## Ursache
- Das Dashboard selbst war nicht in eine vollständige Scrollfläche eingebettet.
- Vier KPI-Karten und vier Schnellaktionen waren starr horizontal angeordnet.
- Tabellen und Abstände verbrauchten auf 1366×768 unverhältnismäßig viel Platz.

## Umsetzung
- Gesamtes Dashboard in eine vertikal scrollbarere `QScrollArea` verschoben.
- Responsiver Umbruch:
  - breite Fenster: 4 Spalten,
  - mittlere/Laptop-Fenster: 2 Spalten,
  - schmale Fenster: 1 Spalte.
- Schnellaktionen verwenden dieselbe responsive Logik.
- KPI-Karten kompakter gestaltet.
- Tabellen für kleine Fenster gehärtet.

## Prüfung
- 246 automatisierte Tests bestanden.
- Python-Syntaxprüfung des geänderten Dashboard-Moduls bestanden.
- Ein echter Qt-Offscreen-GUI-Test war in der Build-Umgebung nicht möglich, weil PySide6 dort nicht installiert ist.

## Manueller Testfokus
Fenstermodus bei 1366×768 sowie 100 %, 125 % und 150 % Betriebssystem-Skalierung prüfen. Alle Dashboard-Bereiche müssen durch vertikales Scrollen erreichbar sein; Karten und Schnellaktionen müssen auf zwei Spalten umbrechen.
