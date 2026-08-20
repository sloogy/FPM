# v0.2.27 Expert Auto + Wishlist

Umgesetzt:
- Regelsystem global ein-/ausschaltbar.
- Full Auto Mode ein-/ausschaltbar.
- Full Auto darf Entscheidungen erklären, ablehnen und loggen.
- Regelgruppen-Grundlage: safety, maintenance, rotation, pen, ink, nib, paper, collector.
- RuleViolation enthält Gruppe, Auto-Aktion und Score-Delta.
- Rotation zeigt Auto-Entscheidung/Erklärung in Hinweisen.
- Harte Regeln werden ohne Override nicht still übernommen.
- Wishlist als generisches Modul für Füller, Tinte, Feder, Papier, Zubehör und Service.
- Wishlist-Kauf kann in Sammlung + Ausgabe übernommen werden.
- Artikelkarte wird als JSON-Datei unter media/wishlist/<id>/article_card.json gespeichert; Bilder/Rechnungen liegen außerhalb der SQLite-DB.

Bewusst noch ausbaubar:
- Regelgruppen-UI pro Gruppe detailliert schalten.
- Media-Import per Drag & Drop in Artikelkartenordner.
- Vollständige Undo/EventLog-Architektur.
