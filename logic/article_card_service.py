"""Artikelkarten-Dateien für Wishlist/Medien.

Bilder, Screenshots und Rechnungen bleiben außerhalb der SQLite-DB. Die DB speichert
nur den Pfad zur JSON-Artikelkarte. Dadurch bleibt die Datenbank klein und portabel.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from database.db import get_db_path


def media_root() -> Path:
    root = get_db_path().parent / "media" / "wishlist"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_article_card(item) -> str:
    folder = media_root() / str(item.id)
    (folder / "images").mkdir(parents=True, exist_ok=True)
    (folder / "invoices").mkdir(parents=True, exist_ok=True)
    (folder / "screenshots").mkdir(parents=True, exist_ok=True)
    card = folder / "article_card.json"
    payload = {
        "id": item.id,
        "type": item.item_type,
        "title": item.title,
        "brand": item.brand,
        "model": item.model,
        "variant": item.variant,
        "status": item.status,
        "shop": item.shop,
        "url": item.url,
        "price": {
            "desired": item.desired_price,
            "expected": item.expected_price,
            "actual": item.actual_price,
            "currency": item.currency,
            "shipping": item.shipping,
            "customs": item.customs,
        },
        "media_dirs": {
            "images": "images/",
            "invoices": "invoices/",
            "screenshots": "screenshots/",
        },
        "created_object": {
            "type": getattr(item, "created_object_type", None),
            "id": getattr(item, "created_object_id", None),
        },
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "notes": item.notes,
        "reason": item.reason,
    }
    card.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(card)
