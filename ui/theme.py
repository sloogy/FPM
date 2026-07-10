"""Zentrale UI-Stilkonstanten (Usability-Befund 3.9, v0.2.53-Analyse).

Erster Konsolidierungsschritt: Die am häufigsten duplizierten Inline-Button-
Styles werden hier als benannte Konstanten geführt. Die CSS-Strings sind
BEWUSST identisch mit den bisherigen Inline-Werten — diese Migration ändert
keine Optik, nur die Quelle. Spätere Theme-Anpassungen (z.B. Dark Mode)
brauchen dann nur noch diese Datei.
"""
from __future__ import annotations

BTN_PRIMARY = "background:#3498db;color:white;border:none;padding:7px 16px;border-radius:5px;font-weight:bold;"
BTN_SUCCESS = "background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:5px;font-weight:bold;"
BTN_DANGER = "background:#e74c3c;color:white;border:none;padding:7px 16px;border-radius:5px;font-weight:bold;"
BTN_SECONDARY = "background:#34495e;color:white;border:none;padding:7px 14px;border-radius:5px;font-weight:bold;"
BTN_MUTED = "background:#7f8c8d;color:white;border:none;padding:7px 16px;border-radius:5px;"
BTN_ACCENT = "background:#16a085;color:white;border:none;padding:7px 14px;border-radius:5px;font-weight:bold;"
