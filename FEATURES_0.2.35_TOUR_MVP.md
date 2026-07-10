# v0.2.35 – Tour-MVP (Akt 1 + Akt 2)

Basis: v0.2.34-nib-format-split

Auslöser: das bestehende Onboarding (4-Schritt-Wizard: Willkommen → Tinte → Füller
→ Einfüllen) deckt weder einen UI-Rundgang noch den Kauf-Workflow ab. Neue
Anforderung: erst Übersicht aller Reiter (inkl. Einstellungen), dann geführter
Erstkauf (Wunsch → bestellt → gekauft → Tinte → Vorschlag).

## Neue Komponenten

### `ui/tour_overlay.py`
- **`SpotlightOverlay`**: vollflächiges Widget über dem Hauptfenster.
  Dimmt den Hintergrund über vier Rechtecke um das Target ab (kein
  `CompositionMode_Clear` – läuft so plattform-stabil), zeichnet einen
  blauen Rahmen um das Spotlight-Rechteck, positioniert die Bubble unter,
  über oder neben dem Target je nach Platz.
- **`TourBubble`**: Erklär-Karte mit Titel, Body (RichText), Nav-Buttons
  („Zurück", „Weiter / Fertig", „Überspringen / Tour beenden").
- Bei `pass_through=True` werden Maus-Events durch das Overlay an die
  echte UI durchgereicht (für interaktive Walkthrough-Schritte), die
  Bubble selbst bleibt klickbar.

### `ui/tour_controller.py`
- **`TourStep`** (Datenklasse): `title`, `body`, `page_index`,
  `target_resolver`, `on_next`, `next_label`, `pass_through`, `on_enter`.
- **`TourController`**: orchestriert die Schritt-Liste, navigiert die
  Sidebar, wartet kurz aufs Layout (QTimer 120 ms) bevor das Spotlight
  platziert wird, versteckt das Overlay bei `on_next` damit Dialoge
  sichtbar bleiben.
- **`build_steps()`**: 18 Schritte – 1 Willkommen, 11 Reiter-Stops
  (Dashboard … Einstellungen), 1 Übergang, 4 Walkthrough-Schritte,
  1 Abschluss.
- **`should_show_tour()` / `mark_tour_done()` / `reset_tour()`**:
  Steuerung über `AppSettings("onboarding_completed")`.

## Walkthrough-Schritte (Akt 2)

1. **Wunsch anlegen** – Wishlist-Reiter, Klick auf „Dialog öffnen" startet
   `_open_wishlist_add_dialog` → `WishlistWidget._add()`.
2. **Status: bestellt → gekauft** – `pass_through=True`, der User bedient
   die echte UI; beim Statuswechsel auf „gekauft" legt das bestehende
   Wishlist-Modul automatisch einen Füller-Eintrag an.
3. **Erste Tinte** – Klick auf „Dialog öffnen" startet
   `_open_ink_add_dialog` → `InkWidget._add()`.
4. **Vorschlag generieren** – navigiert zu Rotation, ruft `_generate`
   (Fallbacks: `_refresh_suggestions`, `_run`, `_load_suggestions`,
   `refresh`).

## Ablöse

- Alter `OnboardingWizard` wird nicht mehr aufgerufen
  (`main_window.show_onboarding_if_needed` ruft jetzt `start_tour`).
- Datei `ui/onboarding_wizard.py` bleibt im Tree, ist aber unreferenziert
  und kann später entfernt werden.

## Trigger-Punkte

- **Erster Start mit leerer DB**: `should_show_tour()` → `start_tour()`
  via `QTimer.singleShot(250, …)` damit das Fenster sichtbar ist.
- **Hilfe-Reiter**: prominente Karte oben mit „Tour starten"-Button
  (`tour_requested`-Signal, in `main_window._ensure_widget` automatisch
  mit `start_tour` verbunden).
- **Einstellungen → Daten zurücksetzen**: zusätzlicher Button „Tour jetzt
  starten" (gleicher Signalweg) neben dem bestehenden „Onboarding
  zurücksetzen" (das ist weiterhin der „bei nächstem Start"-Weg).

## Bewusst noch nicht in dieser Runde

- **Tiefe Button-Spotlights**: pro Reiter ein Stop, nicht mehrere. Die
  Erweiterung auf 2–4 Button-Stops pro Reiter (Add-Button, Filter, wichtige
  Spalten) folgt in 0.2.36, falls die Spotlight-Mechanik im echten Betrieb
  funktioniert. Vorher 30+ Stops zu schreiben wäre Verschwendung gewesen.
- **Einstellungen-Unterreiter** einzeln erklärt.
- **Re-Layout bei Fenster-Resize während laufender Tour**: das Spotlight
  rendert beim Navigieren neu (jeder Step-Wechsel), aber nicht bei
  reinem Resize zwischen Schritten. Praxisrelevant gering – wer das
  Fenster mitten in der Tour resized, klickt einmal Weiter/Zurück und
  alles passt wieder.

## Risiken

- **Lazy-Loading**: Page-Widgets werden erst beim ersten Navigieren
  erzeugt. Der Resolver `mw._ensure_widget(i)` erzwingt das Anlegen,
  damit das Spotlight ein Ziel hat. Verzögerung 120 ms reicht für die
  meisten Layouts; bei Riesentabellen evtl. nicht. Workaround: Step
  überspringen, App rendert während User liest.
- **Modale Dialoge** in `on_next` blockieren den Code-Fluss am Aufruf,
  was so gewollt ist (Overlay ist dann versteckt). Beim Schließen geht's
  zum nächsten Step.
- **GUI nicht testbar in dieser Build-Umgebung** (kein PySide6
  installierbar, kein Display) – getestet wurde nur Compile, Existenz
  der referenzierten Methoden in WishlistWidget/RotationWidget und
  Konsistenz der `page_index`-Werte (alle ∈ [0..10]).
