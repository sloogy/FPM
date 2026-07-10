# Version 0.2.84 – Visual Size Comparison & AI Search

## Fokus

Diese Version verbessert zwei Bedienpunkte aus dem Sammler-Alltag:

1. Der Größenvergleich nutzt keine abstrakten Balken mehr, sondern stilisierte Füller-Silhouetten, die anhand der gespeicherten Maße skaliert werden.
2. Die manuelle Recherche öffnet Google KI-/Websuchen ohne enge `site:`-Einschränkung. Die automatische Parser-Logik bleibt weiterhin vorsichtig und hersteller-zuerst.

## Änderungen

- Größenvergleich komplett neu gezeichnet:
  - Overlay-Modus: alle Füller starten links an derselben Kante und lassen sich visuell übereinander vergleichen.
  - Listenmodus: jeder Füller als eigene maßstäbliche Silhouette.
  - Maßauswahl: bestes verfügbares Maß, geschlossen, offen oder gepostet.
  - Gewicht und Maßtyp werden in der Liste lesbar angezeigt.
- Manuelle Dimensionssuche:
  - Erste Browser-URL ist eine Google-KI/Websuche mit natürlicher Frage nach Länge, Gewicht, Tintenkapazität und Füllsystem.
  - Keine `site:<domain>`-Einschränkung mehr im manuellen Browserpfad.
- Manuelle Bildsuche:
  - Öffnet Google KI/Web plus Google Images.
  - Keine harte Hersteller-`site:`-Einschränkung mehr.
- Automatischer Online-Lookup:
  - Bleibt unverändert konservativ: Herstellerdomains zuerst, `manufacturer:<domain>`-Quellen, Early-Stop ab Konfidenz ≥ 0.65.
- Texte und Handbuch für DE/EN/FR nachgeführt.

## Technische Dateien

- `ui/pen_widget.py`
- `logic/pen_dimensions_service.py`
- `i18n/de.json`
- `i18n/en.json`
- `i18n/fr.json`
- `docs/BENUTZERHANDBUCH_DE.md`
- `README.md`
- `tests/test_pen_dimensions_service.py`

## Validierung

```bash
python -m pytest -q -ra
python -m compileall -q .
python tools/sync_version.py --check
```
