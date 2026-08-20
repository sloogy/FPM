# UI-/Logik-Audit: Usability & Design – FountainPen Manager v0.2.74

**Basis:** v0.2.73 · **Build:** ui-design-usability-audit · **Datum:** 6. Juli 2026

## Kurzurteil

**Der Stand ist in Usability und Design deutlich reifer als der Versionsstempel
vermuten lässt.** Die großen UX-Empfehlungen früherer Audits sind inzwischen
umgesetzt; die Analyse fand genau **einen dringenden Fehler** (i18n-Verdrahtung
in der Rotation) – behoben. Sonst waren keine dringenden Änderungen nötig, und
ich habe bewusst keine erfunden.

---

## 1. Logik-Usability (Briefing-Kernanforderungen)

**Warnstufen** ✅ Zentral in der Engine definiert (`LEVEL_COLORS`, `LEVEL_ICONS`,
`PENALTY` für info/warning/critical/blocked) – exakt die vier Briefing-Stufen,
farblich sinnvoll abgestuft (blau → gelb-orange → orange → rot). Das UI
importiert die Icons aus der Engine statt sie zu duplizieren → kein Drift.
Die zwei „Orangetöne" aus dem Farb-Scan sind also **bewusste Abstufung**
(warning vs. critical), kein Widerspruch.

**Override-System** ✅ „Die Engine empfiehlt – der Nutzer entscheidet" ist real:
Bei aktiven Regel-Verstößen fragt ein `OverrideReasonDialog` den Grund ab und
schreibt ins `OverrideLog`; harte Regeln blockieren nur den Auto-Weg, nicht den
manuellen. Zusätzlich existiert ein `WhyScoreDialog` („Warum dieser
Vorschlag?") – Scoring-Transparenz, wie sie sich ein Enthusiast wünscht.

**Dringender Fund (behoben):** In den Vorschlagsdetails wurde der Zusatz
`" (harte Regel)"` als **deutsches Literal** angehängt, obwohl der Key
`rotation.warning_hard_rule_suffix` in DE/EN/FR **bereits existierte** – ein
reiner Verdrahtungsfehler (EN/FR sahen deutschen Text). Jetzt über `t()`
verdrahtet; Guard-Test verhindert Rückfall.

## 2. UI-Design & Konsistenz

**Dialog-Struktur** ✅ Der früher kritisierte, überfüllte Füller-Dialog ist
inzwischen in **vier Tabs** gegliedert (✒ Grunddaten / 🔧 Feder / 📐 Details &
Wert / 📝 Notizen) mit ScrollAreas – genau das empfohlene Basis/Erweitert-
Prinzip. Für Einsteiger ist der Pflichtteil klein; Sammlertiefe bleibt erreichbar.

**Farb-Semantik** ✅ Dominante, konsistente Töne je Bedeutung (Grün `#27ae60`
= ok/gefüllt, Violett `#8e44ad` = gesperrt, Rot `#e74c3c` = kritisch; Zweittöne
sind Abstufungen bzw. Hover). Es gibt eine zentrale `styles.py`; daneben
existieren ~200 verstreute Hex-Werte in Widgets. Das ist **gewachsen, aber
nicht widersprüchlich** – eine Token-Konsolidierung wäre Design-Refactoring,
kein Fehler, und ohne GUI-Test riskant → bewusst nicht angefasst.

**Bereits verifiziert aus früheren Runden (unverändert intakt):** einheitliche
Empty-States in allen sechs Listen, konsistente „+ X hinzufügen"-Buttons,
Kontextmenüs überall, Dashboard blendet leere Abschnitte aus, gruppierte
Seitenleiste (`GROUPED_ORDER`), Modul-Shortcuts mit Tooltip-Hinweis.

## 3. Systematischer Neu-Check: „Key existiert, aber unverdrahtet"

Der Rotation-Fund legte die Frage nahe, ob weitere deutsche Literale exakt
einem vorhandenen i18n-Wert entsprechen. Projektweiter AST-Scan: 130 Roh-
Treffer, nach Kontext-Klassifikation:

| Kontext | Anzahl | Bewertung |
|---|---:|---|
| CSV-Import/Export-Spaltennamen (`row.get("Marke")` …) | Großteil | **Korrekt so** – Datenformat-Vertrag; Übersetzen würde alte CSVs brechen |
| Glossar-Fachtermini (Sheen, Shimmer, Grail …) | 4 | **Bewusst international** – Beschreibungen sind übersetzt |
| Echte UI-Anzeige-Positionen (setText, Items, Tooltips, Titel …) | **0** | Nach dem Rotation-Fix keine offenen Fälle |

## 4. Ehrlichkeit über die Checker selbst

Zwei erste, naive Prüfläufe erzeugten Falsch-Positive (Format-Specs `{value:g}`,
verschachtelte kwargs, geerbte Qt-Slots). Alle wurden **verifiziert und
widerlegt** statt „gefixt". Die Anzeige-Positions-Heuristik erkennt zudem keine
Literale, die erst einer Variablen zugewiesen und später angezeigt werden –
genau diese Klasse wurde in den letzten zwei Runden separat abgedeckt
(Emoji-/Konnektor-Muster, `pen_widget`-Fixes).

## 5. Validierung

```text
python -m compileall -q .            → OK
Testsuite (headless)                 → 125 passed (+1 Guard: hard-rule-Suffix)
tools/sync_version.py --check        → 0.2.74 synchron
alle fünf i18n-Audits                → OK (1955 Keys × 3)
Key-Parität                          → de=en=fr=1955, 0 Waisen
Unverdrahtete Anzeige-Literale       → 0
```

## 6. Offen (unverändert, kein Blocker)

- Manueller **GUI-Smoke-Test** auf PySide6/Windows (Checklisten in
  `docs/GUI_SMOKE_TEST_*.md`) – jetzt zusätzlich: Rotationsvorschlag mit
  harter Regel auf EN/FR ansehen (Suffix „(hard rule)"/„(règle stricte)").
- Optionales Design-Refactoring: Streufarben in `styles.py`-Tokens
  konsolidieren (Nice-to-have, nicht dringend).

**Freigabe: v0.2.74 als Source/Portable-RC empfohlen.**
