# Changelog v0.2.82 – BENUTZERHANDBUCH (Leitfaden)

## Neu: `docs/BENUTZERHANDBUCH_DE.md`
Ausführlicher Leitfaden zusätzlich zum In-App-Wiki – 24 Kapitel, detailliert statt oberflächlich:

- **Grundlagen:** Philosophie (Engine empfiehlt – Nutzer entscheidet), Datenverzeichnis-Priorität (`FPM_DATA_DIR` → `installation.json` → `~/.fpm_data`), Dateiinventar (fpm.db, images/, pen_dimensions_cache.json, manufacturer_domains.json), Erststart-Seeding.
- **Module:** alle 14 Expertenmodule mit Zweck; Einfach-/Expertenmodus; globale Suche.
- **Dashboard:** Semantik jeder Zone inkl. 80-%-Schwelle des Safety-Timers und Warnungen-Definition.
- **Rotation im Detail:** vollständige Score-Tabelle mit Werkswerten (Regel-Basis 100, Leer-Bonus +120, Füller-Standzeit Tage÷2 bis +80, Tinten-Staffel 0/10/25/50/75/90, Farbfamilie +14/−18, Duplikat −22, Blockade-Deckel −50, Auto-Reject −999); Rollenliste (13); zweistufiges Auswahlverfahren mit Diversitätsbonus 0–30 und Batch-Familien-Malus −30; Warum-Dialog; Reroll-Mechanik (Paar-Sperre, 🔁-Neustart); Zufallsformel `Score·(100−p)/100 + Jitter·p/100`, Jitter ±140, Sicherheitsfilter.
- **Regeln & Auto:** Typen/Stufen, 4 Tabs, Override-Log; Full-Auto-Entscheidungslogik (allow/warn/reject/require_override) mit Werkszustand der 4 Schalter.
- **Safety Timer:** exakte Berechnung – Tinten-Individualwert hat Vorrang, sonst Minimum aus normal 28 / shimmer 14 / pigment-oder-wasserfest 10 / grail 21; Rechenbeispiel.
- **Weitere Kapitel:** Füller/Tinten/Federn/Papier-Felder inkl. 💍/⭐-Semantik, Ausgaben & Sammlerwert, Wishlist-Kaufflow, Statistiken/Schreibproben, Enthusiasten-Lab (4 Tabs), Recherche mit Konfidenz-Early-Stop 0.65 und Overlay-Spezifikation (String/Liste), alle 9 Einstellungsseiten, Mehrsprachigkeit, Updates, Backup/Umzug, FAQ (8 Einträge), Referenztabellen (15 Settings-Schlüssel, 8 Standardregeln, Score-Kurzreferenz), Glossar (20 Begriffe).

## Verankerung
- README verlinkt das Handbuch direkt unter dem Release-Fokus.
- Hilfe → Schnellstart: neue Karte „📖 Ausführliches Handbuch" mit Fundort (DE/EN/FR, 2 neue i18n-Keys × 3).

## Absicherung: Doku-Drift wird Testfehler
Neuer Guard `tests/test_user_manual_0282_static.py` (10 Tests) prüft das Handbuch **gegen den Code**:
- Standzeit-Defaults 28/14/10/21 gegen das DB-Seeding,
- Score-Gewichte (+120, ÷2/80-Deckel, Staffel, +14/−18, −22, −50, −999, ±140, Mischformel) gegen die Engine,
- Auswahl-Layer (0–30 / −30), 80-%-Schwelle, Konfidenz 0.65,
- alle 8 Standardregel-Namen wörtlich, 13 Rollen, Dateinamen, `FPM_DATA_DIR`,
- Settings-Referenz (8 Schlüssel mit Werkswert),
- Existenz/Umfang (> 20 000 Zeichen) und Verlinkung in README + Hilfe.

Beim ersten Lauf fing der Guard prompt einen eigenen Filterfehler (case-sensitives „Tinte" übersah „Pigmenttinte") – behoben durch kontextgenaues Matching auf `Rule(`-Blöcke.

## Technik
- KILLCRITIC-Audit +3 Invarianten (Handbuch existiert, README-Link, Hilfe-Link): 57 × 20 = 1140 Checks, 0 Findings.
- i18n: 2031 Keys × 3 (Parität grün). Keine Logikänderungen – reine Doku-, Verankerungs- und Guard-Runde.
