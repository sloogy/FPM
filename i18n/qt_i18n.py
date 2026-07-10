"""Qt runtime wiring for the app's JSON based i18n system.

Most visible UI text is now wired directly through explicit t("...") keys.
This module only provides conservative fallbacks for transient Qt convenience
dialogs/menus and legacy labels that may still be created dynamically.

Important performance rule: QWidget.show is never monkey-patched.  Large page
widgets are not recursively walked on every show(); translation is explicit at
construction time, with small fallback passes only for dialogs/menus.
"""
from __future__ import annotations

from functools import lru_cache
import re
from typing import Any, Iterable

from i18n.translator import Translator


_TAG_RE = re.compile(r"(<[^>]+>)")
_HOTKEY_RE = re.compile(r"(?<!&)&(?!&)")


def _flatten(node: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _flatten(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, str):
        yield prefix, node


@lru_cache(maxsize=8)
def _reverse_json_map(lang: str) -> dict[str, str]:
    tr = Translator.instance()
    # Load files through the already available fallback/current data.  For a
    # requested language that is not active yet, use a temporary Translator-like
    # file read via the public loader by switching and switching back.
    old_lang = tr.language
    try:
        tr.set_language("de")
        de_items = dict(_flatten(tr._data))  # noqa: SLF001 - internal bridge, same package intent
        tr.set_language(lang)
        target_items = dict(_flatten(tr._data))  # noqa: SLF001
    finally:
        tr.set_language(old_lang)

    result: dict[str, str] = {}
    for key, de_text in de_items.items():
        target = target_items.get(key)
        if isinstance(de_text, str) and isinstance(target, str) and de_text != target:
            result[de_text] = target
            # Common UI strings may include an icon prefix before the actual text.
            # Exact plain strings from JSON should still translate inside labels
            # such as "✒  Füller" through the phrase fallback below.
    return result

@lru_cache(maxsize=8)
def _any_json_map(lang: str) -> dict[str, str]:
    """Map any known localized JSON text back to the requested target language.

    This keeps live language switching working even when newer widgets already
    set text via t("key") instead of a German fallback literal.  Example:
    a widget built in English can still be switched to French because the
    English text resolves to the same JSON key first.
    """
    tr = Translator.instance()
    old_lang = tr.language
    try:
        all_items: dict[str, dict[str, str]] = {}
        for source_lang in ("de", "en", "fr"):
            tr.set_language(source_lang)
            all_items[source_lang] = dict(_flatten(tr._data))  # noqa: SLF001
        tr.set_language(lang)
        target_items = dict(_flatten(tr._data))  # noqa: SLF001
    finally:
        tr.set_language(old_lang)

    result: dict[str, str] = {}
    for items in all_items.values():
        for key, source_text in items.items():
            target = target_items.get(key)
            if isinstance(source_text, str) and isinstance(target, str) and source_text != target:
                result[source_text] = target
    return result


# Exact overrides for source strings that are visible but not part of the older
# JSON key set.  Keep these entries human-readable; they double as documentation
# of remaining legacy UI text.
_EXACT: dict[str, dict[str, str]] = {
    "en": {
        "Einfachmodus\nDetails rechts im Modul": "Simple mode\nDetails on the right in each module",
        "Sprache (nächster Start):": "Language (next start):",
        "Standard EDC-Plätze:": "Default EDC slots:",
        "Sidebar / Kategorien:": "Sidebar / categories:",
        "Optionen sind nach Bereichen getrennt. Links Bereich wählen, rechts ändern. Jede Seite besitzt bei Bedarf einen eigenen Scrollbalken.": "Options are grouped by area. Choose an area on the left and change settings on the right. Each page has its own scrollbar when needed.",
        "Grundlegende Programmeinstellungen. Regel-Details und Verbrauchslogik bleiben im eigenen Regel-Tab der App.": "Basic application settings. Rule details and consumption logic remain in the dedicated Rules tab.",
        "Easy/Expert Mode, Full Auto Mode, einzelne Regelgruppen und Verbrauchsautomatik werden im Modul „Regeln“ verwaltet. Dadurch bleiben die Einstellungen schlank.": "Easy/Expert Mode, Full Auto Mode, individual rule groups and consumption automation are managed in the Rules module. This keeps Settings lean.",
        "Schrift- und UI-Größe global anpassen. Wirkt sofort auf neue und bereits geöffnete Fenster.": "Adjust font and UI size globally. Applies immediately to new and already open windows.",
        "Auf Laptop/HiDPI meistens „Auto“ oder „Laptop groß“. Diese Einstellung verhindert abgeschnittene Texte in Dialogen.": "On laptop/HiDPI screens, “Auto” or “Large laptop” usually works best. This setting prevents clipped text in dialogs.",
        "Die Regeln-Seite hat zusätzlich eigene Tabellen-Dichte. Diese globale Einstellung gilt aber für Schrift, Eingabefelder, Tabs, Buttons und Dialoge in der gesamten App.": "The Rules page also has its own table density. This global setting applies to fonts, input fields, tabs, buttons and dialogs throughout the app.",
        "Zahlenformat, Standardwährung und Wechselkurse für Sammlungswert und Ausgaben.": "Number format, default currency and exchange rates for collection value and expenses.",
        "Datenbankpfad ändern": "Change database path",
        "Was möchtest du tun?": "What do you want to do?",
        "Neue leere Datenbank anlegen (frisch starten)": "Create a new empty database (fresh start)",
        "Vorhandene Datenbankdatei öffnen / wechseln": "Open / switch to an existing database file",
        "Pfad zur Datenbankdatei …": "Path to the database file …",
        "Datenmigration": "Data migration",
        "Aktuelle Daten in neue Datenbank kopieren": "Copy current data into the new database",
        "Neue Datenbank leer starten / nur Pfad wechseln": "Start with an empty database / only change path",
        "ℹ  Beim Öffnen einer vorhandenen DB wird nie kopiert – die Datei wird unverändert verwendet.": "ℹ  When opening an existing database, nothing is copied – the file is used unchanged.",
        "Neue Datenbankdatei anlegen": "Create new database file",
        "Vorhandene Datenbankdatei öffnen": "Open existing database file",
        "SQLite-Datenbank (*.db)": "SQLite database (*.db)",
        "SQLite-Datenbank (*.db);;Alle Dateien (*)": "SQLite database (*.db);;All files (*)",
        "Kein Pfad": "No path",
        "Bitte zuerst einen Pfad auswählen.": "Please select a path first.",
        "Gleicher Pfad": "Same path",
        "Das ist bereits der aktuelle Pfad.": "This is already the current path.",
        "Suchen im aktuellen Modul …": "Search in the current module …",
        "Füller hinzufügen": "Add pen",
        "Tinte hinzufügen": "Add ink",
        "Einfüllen": "Fill",
        "Gereinigt": "Cleaned",
        "Rotation vorschlagen": "Suggest rotation",
        "Navigation": "Navigation",
        "Die Navigation wurde im Calibre-Modus vereinfacht.\n\nDie Hauptmodule sind fest angeordnet, damit die Bedienung stabil und übersichtlich bleibt.\nKategorien, Tags und Filter werden künftig direkt in den Tabellen verwaltet.": "Navigation has been simplified in Calibre mode.\n\nThe main modules are fixed so the app stays stable and easy to use.\nCategories, tags and filters will be managed directly in the tables.",
        "Mit ✓ Übernehmen bestätigen, alternativ Doppelklick oder Rechtsklick.": "Confirm with ✓ Apply, or use double-click/right-click.",
        "Keine Regelverletzungen – Kombination empfohlen.": "No rule violations – combination recommended.",
        "Bitte Override-Grund eingeben:": "Please enter an override reason:",
        "Regelüberschreibung bestätigen": "Confirm rule override",
        "Als gekauft übernehmen …": "Convert as purchased …",
        "Status setzen": "Set status",
        "gekauft": "purchased",
        "reserviert": "reserved",
        "geplant": "planned",
        "offen": "open",
        "Keine Tinten vorhanden oder alle leer/archiviert.\nBitte zuerst in der Tintenverwaltung eine Tinte anlegen.": "No inks exist or all are empty/archived.\nPlease create an ink in Ink Management first.",
        "⚠  Keine Tinten vorhanden oder alle leer/archiviert.\nBitte zuerst in der Tintenverwaltung eine Tinte anlegen.": "⚠  No inks exist or all are empty/archived.\nPlease create an ink in Ink Management first.",
        "Noch keine Füller vorhanden. Klicke auf '+ Füller' um den ersten Füller anzulegen.": "No pens yet. Click '+ Pen' to add your first pen.",
        "Region / Voreinstellung:": "Region / preset:",
        "Region {} · Währung {} · Kurse gespeichert.\nAlle Anzeigen werden neu geladen.": "Region {} · currency {} · rates saved.\nAll views will be reloaded.",
        "Vergleicht gespeicherte Füllermaße. Nutzt Länge geschlossen/offen/gepostet, soweit vorhanden.": "Compares saved pen dimensions. Uses closed/open/posted length where available.",
        "Export abgeschlossen:\n{}": "Export completed:\n{}",
        "{} aktive InkLoad(s) geschlossen.": "{} active InkLoad(s) closed.",
        "Kein Limit": "No limit",
    },
    "fr": {
        "Einfachmodus\nDetails rechts im Modul": "Mode simple\nDétails à droite dans chaque module",
        "Sprache (nächster Start):": "Langue (prochain démarrage) :",
        "Standard EDC-Plätze:": "Emplacements EDC par défaut :",
        "Sidebar / Kategorien:": "Barre latérale / catégories :",
        "Optionen sind nach Bereichen getrennt. Links Bereich wählen, rechts ändern. Jede Seite besitzt bei Bedarf einen eigenen Scrollbalken.": "Les options sont regroupées par domaine. Choisissez un domaine à gauche et modifiez les réglages à droite. Chaque page dispose de sa propre barre de défilement si nécessaire.",
        "Grundlegende Programmeinstellungen. Regel-Details und Verbrauchslogik bleiben im eigenen Regel-Tab der App.": "Réglages de base de l'application. Les détails des règles et la logique de consommation restent dans l'onglet Règles dédié.",
        "Easy/Expert Mode, Full Auto Mode, einzelne Regelgruppen und Verbrauchsautomatik werden im Modul „Regeln“ verwaltet. Dadurch bleiben die Einstellungen schlank.": "Le mode Easy/Expert, le mode Full Auto, les groupes de règles et l'automatisation de la consommation sont gérés dans le module Règles. Les paramètres restent ainsi légers.",
        "Schrift- und UI-Größe global anpassen. Wirkt sofort auf neue und bereits geöffnete Fenster.": "Ajuste globalement la taille de police et de l'interface. S'applique immédiatement aux fenêtres nouvelles et déjà ouvertes.",
        "Auf Laptop/HiDPI meistens „Auto“ oder „Laptop groß“. Diese Einstellung verhindert abgeschnittene Texte in Dialogen.": "Sur un écran portable/HiDPI, « Auto » ou « Grand portable » convient généralement le mieux. Ce réglage évite les textes tronqués dans les dialogues.",
        "Die Regeln-Seite hat zusätzlich eigene Tabellen-Dichte. Diese globale Einstellung gilt aber für Schrift, Eingabefelder, Tabs, Buttons und Dialoge in der gesamten App.": "La page Règles possède aussi sa propre densité de tableau. Ce réglage global s'applique aux polices, champs de saisie, onglets, boutons et dialogues dans toute l'application.",
        "Zahlenformat, Standardwährung und Wechselkurse für Sammlungswert und Ausgaben.": "Format des nombres, devise par défaut et taux de change pour la valeur de collection et les dépenses.",
        "Datenbankpfad ändern": "Modifier le chemin de la base de données",
        "Was möchtest du tun?": "Que veux-tu faire ?",
        "Neue leere Datenbank anlegen (frisch starten)": "Créer une nouvelle base vide (nouveau départ)",
        "Vorhandene Datenbankdatei öffnen / wechseln": "Ouvrir / utiliser une base de données existante",
        "Pfad zur Datenbankdatei …": "Chemin vers le fichier de base de données …",
        "Datenmigration": "Migration des données",
        "Aktuelle Daten in neue Datenbank kopieren": "Copier les données actuelles dans la nouvelle base",
        "Neue Datenbank leer starten / nur Pfad wechseln": "Démarrer avec une base vide / changer seulement le chemin",
        "ℹ  Beim Öffnen einer vorhandenen DB wird nie kopiert – die Datei wird unverändert verwendet.": "ℹ  Lors de l'ouverture d'une base existante, rien n'est copié – le fichier est utilisé tel quel.",
        "Neue Datenbankdatei anlegen": "Créer un nouveau fichier de base de données",
        "Vorhandene Datenbankdatei öffnen": "Ouvrir un fichier de base de données existant",
        "SQLite-Datenbank (*.db)": "Base de données SQLite (*.db)",
        "SQLite-Datenbank (*.db);;Alle Dateien (*)": "Base de données SQLite (*.db);;Tous les fichiers (*)",
        "Kein Pfad": "Aucun chemin",
        "Bitte zuerst einen Pfad auswählen.": "Veuillez d'abord sélectionner un chemin.",
        "Gleicher Pfad": "Même chemin",
        "Das ist bereits der aktuelle Pfad.": "C'est déjà le chemin actuel.",
        "Suchen im aktuellen Modul …": "Rechercher dans le module actuel …",
        "Füller hinzufügen": "Ajouter un stylo",
        "Tinte hinzufügen": "Ajouter une encre",
        "Einfüllen": "Remplir",
        "Gereinigt": "Nettoyé",
        "Rotation vorschlagen": "Suggérer une rotation",
        "Navigation": "Navigation",
        "Die Navigation wurde im Calibre-Modus vereinfacht.\n\nDie Hauptmodule sind fest angeordnet, damit die Bedienung stabil und übersichtlich bleibt.\nKategorien, Tags und Filter werden künftig direkt in den Tabellen verwaltet.": "La navigation a été simplifiée en mode Calibre.\n\nLes modules principaux sont fixes afin que l'utilisation reste stable et claire.\nLes catégories, étiquettes et filtres seront gérés directement dans les tableaux.",
        "Mit ✓ Übernehmen bestätigen, alternativ Doppelklick oder Rechtsklick.": "Confirme avec ✓ Appliquer, ou utilise un double-clic / clic droit.",
        "Keine Regelverletzungen – Kombination empfohlen.": "Aucune violation de règle – combinaison recommandée.",
        "Bitte Override-Grund eingeben:": "Veuillez saisir la raison de l'exception :",
        "Regelüberschreibung bestätigen": "Confirmer l'exception à la règle",
        "Als gekauft übernehmen …": "Convertir comme acheté …",
        "Status setzen": "Définir le statut",
        "gekauft": "acheté",
        "reserviert": "réservé",
        "geplant": "prévu",
        "offen": "ouvert",
        "Keine Tinten vorhanden oder alle leer/archiviert.\nBitte zuerst in der Tintenverwaltung eine Tinte anlegen.": "Aucune encre n'existe ou toutes sont vides/archivées.\nCrée d'abord une encre dans la gestion des encres.",
        "⚠  Keine Tinten vorhanden oder alle leer/archiviert.\nBitte zuerst in der Tintenverwaltung eine Tinte anlegen.": "⚠  Aucune encre n'existe ou toutes sont vides/archivées.\nCrée d'abord une encre dans la gestion des encres.",
        "Noch keine Füller vorhanden. Klicke auf '+ Füller' um den ersten Füller anzulegen.": "Aucun stylo pour le moment. Clique sur '+ Stylo' pour ajouter ton premier stylo.",
        "Papier:": "Papier :",
        "— Kein Papier —": "— Aucun papier —",
        "Als Papier anlegen + Ausgabe": "Créer comme papier + dépense",
        "Region / Voreinstellung:": "Région / préréglage :",
        "Vergleicht gespeicherte Füllermaße. Nutzt Länge geschlossen/offen/gepostet, soweit vorhanden.": "Compare les dimensions enregistrées des stylos. Utilise la longueur fermé/ouvert/posté si disponible.",
        "Export abgeschlossen:\n{}": "Export terminé :\n{}",
        "{} aktive InkLoad(s) geschlossen.": "{} InkLoad(s) actif(s) clôturé(s).",
        "Kein Limit": "Aucune limite",
        "Alles kann als Wunsch erfasst werden: Füller, Tinte, Feder, Papier, Zubehör oder Service. Bilder/Rechnungen liegen in einer separaten Artikelkarte-Datei, nicht in SQLite.": "Tout peut être saisi comme souhait : stylo, encre, plume, papier, accessoires ou service. Les images/factures sont stockées dans un fichier de fiche article séparé, pas dans SQLite.",
        "Exportiert Füller, Tinten, Federn, Papier, InkLoads und Ausgaben in einzelne CSV-Dateien.": "Exporte les stylos, encres, plumes, papier, InkLoads et dépenses dans des fichiers CSV séparés.",
        "ACHTUNG: Diese Aktion löscht alle Füller, Tinten, Federn, Papier,\nInkLoads und Ausgaben unwiderruflich!\n\nSystemregeln und Einstellungen bleiben erhalten.\n\nBitte zuerst ein Backup erstellen. Wirklich fortfahren?": "ATTENTION : cette action supprime définitivement tous les stylos, encres, plumes, papiers,\nInkLoads et dépenses !\n\nLes règles système et les paramètres sont conservés.\n\nCrée d'abord une sauvegarde. Continuer vraiment ?",
    },
}


_PHRASES: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("FountainPen Manager", "FountainPen Manager"),
        ("Allgemeine Einstellungen", "General settings"),
        ("Programmeinstellungen", "Application settings"),
        ("Währung & Region", "Currency & Region"),
        ("Datenbank & Backup", "Database & Backup"),
        ("Import / Export", "Import / Export"),
        ("Reset / Gefahrenzone", "Reset / Danger Zone"),
        ("Darstellung speichern & sofort anwenden", "Save appearance & apply now"),
        ("Wechselkurse & Region speichern", "Save exchange rates & region"),
        ("ALLE DATEN LÖSCHEN", "DELETE ALL DATA"),
        ("Factory Reset", "Factory reset"),
        ("Füller-Status reset", "Reset pen status"),
        ("Tintenmengen reset", "Reset ink levels"),
        ("InkLoads schließen", "Close ink loads"),
        ("Datenbankpfad", "Database path"),
        ("Datenbank", "Database"),
        ("Wechselkurse", "Exchange rates"),
        ("Standardwährung", "Default currency"),
        ("Zahlenformat", "Number format"),
        ("Voreinstellung", "preset"),
        ("Dezimaltrennzeichen", "Decimal separator"),
        ("Tausendertrennzeichen", "Thousands separator"),
        ("Apostroph", "Apostrophe"),
        ("Komma", "Comma"),
        ("Punkt", "Dot"),
        ("Keines", "None"),
        ("Vorschau", "Preview"),
        ("Empfehlung", "Recommendation"),
        ("Durchsuchen", "Browse"),
        ("Ordner öffnen", "Open folder"),
        ("Pfad ändern", "Change path"),
        ("Optimieren", "Optimize"),
        ("CSV-Export starten", "Start CSV export"),
        ("Navigation anpassen", "Customize navigation"),
        ("Regeln & Reinigungszeiten", "Rules & cleaning times"),
        ("Hilfe & Regel-Erklärungen", "Help & rule explanations"),
        ("Ausgaben-Tracker", "Expense tracker"),
        ("Intelligente Rotation", "Smart rotation"),
        ("Vorschläge für leere Füller", "Suggestions for empty pens"),
        ("Freie Tinten", "Available inks"),
        ("Aktuelle Belegung", "Current loadout"),
        ("Letzte Einfüllungen", "Recent fills"),
        ("Ink Safety Timer", "Ink Safety Timer"),
        ("Service & Sperren", "Service & blocking"),
        ("Sperren/Service", "Block/Service"),
        ("Sperren", "Block"),
        ("Gesperrt", "Blocked"),
        ("Service", "Service"),
        ("Austrocknung", "Dry-out"),
        ("Reinigung fällig", "Cleaning due"),
        ("Überfällig", "Overdue"),
        ("Safety-Warnungen", "safety warnings"),
        ("Safety-Timer", "safety timers"),
        ("Regelverstöße", "rule violations"),
        ("Regelverletzungen", "rule violations"),
        ("Regelüberschreibung", "rule override"),
        ("harte Regel", "hard rule"),
        ("Warnungen", "Warnings"),
        ("Warnung", "Warning"),
        ("Fehler", "Errors"),
        ("Fehlern", "errors"),
        ("OK", "OK"),
        ("Einfüllen", "Fill"),
        ("Tinte einfüllen", "Fill ink"),
        ("Leeren und direkt neu befüllen", "Empty and refill directly"),
        ("Leer markieren", "Mark empty"),
        ("Gereinigt", "Cleaned"),
        ("Als gereinigt markieren", "Mark as cleaned"),
        ("Aktualisieren", "Refresh"),
        ("Vorschläge", "Suggestions"),
        ("Vorschlag", "Suggestion"),
        ("Übernehmen", "Apply"),
        ("Bearbeiten", "Edit"),
        ("Löschen", "Delete"),
        ("Speichern", "Save"),
        ("Hinzufügen", "Add"),
        ("hinzufügen", "add"),
        ("Erstellen", "Create"),
        ("erstellen", "create"),
        ("Kopieren", "Copy"),
        ("kopieren", "copy"),
        ("Refill", "Refill"),
        ("Importieren", "Import"),
        ("importieren", "import"),
        ("Exportieren", "Export"),
        ("exportieren", "export"),
        ("Archivieren", "Archive"),
        ("Archivierte", "Archived"),
        ("Archiviert", "Archived"),
        ("archiviert", "archived"),
        ("Wiederherstellen", "Restore"),
        ("Zurücksetzen", "Reset"),
        ("zurückgesetzt", "reset"),
        ("Schließen", "Close"),
        ("schließen", "close"),
        ("Abbrechen", "Cancel"),
        ("Fortfahren", "Continue"),
        ("Bestätigen", "Confirm"),
        ("Auswählen", "Select"),
        ("auswählen", "select"),
        ("Suchen", "Search"),
        ("Filter", "Filter"),
        ("Status setzen", "Set status"),
        ("Als gekauft übernehmen", "Convert as purchased"),
        ("gekauft", "purchased"),
        ("reserviert", "reserved"),
        ("geplant", "planned"),
        ("offen", "open"),
        ("Pflicht", "Required"),
        ("verheiratet", "paired"),
        ("feste Paarung", "fixed pairing"),
        ("Pflicht-Bonus", "required bonus"),
        ("Beliebtheit", "popularity"),
        ("Score", "Score"),
        ("Score-Legende", "Score legend"),
        ("Warum", "Why"),
        ("Grund", "Reason"),
        ("Notizen", "Notes"),
        ("Kommentar", "Comment"),
        ("Beschreibung", "Description"),
        ("Kategorie", "Category"),
        ("Kategorien", "Categories"),
        ("Tags", "Tags"),
        ("Tabelle", "Table"),
        ("Tabellen", "Tables"),
        ("Dichte", "density"),
        ("Füllerverwaltung", "Pen Management"),
        ("Füller", "Pens"),
        ("Tintenverwaltung", "Ink Management"),
        ("Tinten", "Inks"),
        ("Tinte", "Ink"),
        ("Federverwaltung", "Nib Management"),
        ("Federn", "Nibs"),
        ("Feder", "Nib"),
        ("Papierverwaltung", "Paper Management"),
        ("Papier", "Paper"),
        ("Ausgaben", "Expenses"),
        ("Ausgabe", "Expense"),
        ("Einstellungen", "Settings"),
        ("Regeln", "Rules"),
        ("Regel", "Rule"),
        ("Hilfe", "Help"),
        ("Dashboard", "Dashboard"),
        ("Rotation", "Rotation"),
        ("Wishlist", "Wishlist"),
        ("Allgemein", "General"),
        ("Darstellung", "Appearance"),
        ("Über", "About"),
        ("Marke", "Brand"),
        ("Modell", "Model"),
        ("Name", "Name"),
        ("Farbe", "Color"),
        ("Grundfarbe", "Base color"),
        ("Farbfamilie", "Color family"),
        ("Farbspektrum", "Color spectrum"),
        ("Füllsystem", "Filling system"),
        ("Kaufdatum", "Purchase date"),
        ("Kaufpreis", "Purchase price"),
        ("Marktwert", "Market value"),
        ("Versicherungswert", "Insurance value"),
        ("Länge", "Length"),
        ("Durchmesser", "Diameter"),
        ("Gewicht", "Weight"),
        ("Größe", "Size"),
        ("Größenvergleich", "Size comparison"),
        ("Griff", "Grip"),
        ("geschlossen", "closed"),
        ("offen", "open"),
        ("gepostet", "posted"),
        ("Schreibgefühl", "Writing feel"),
        ("Probleme", "Problems"),
        ("Problemfüller", "problem pen"),
        ("Reinigung", "Cleaning"),
        ("Aktuelle Tinte", "Current ink"),
        ("Leer", "Empty"),
        ("Tage eingefüllt", "Days inked"),
        ("Tage im Füller", "days in pen"),
        ("Tage", "days"),
        ("Tag", "day"),
        ("Eingefüllt seit", "Inked since"),
        ("Nässe", "Wetness"),
        ("Sheen", "Sheen"),
        ("Shimmer", "Shimmer"),
        ("Schimmer", "Shimmer"),
        ("Shading", "Shading"),
        ("Pigmenttinte", "Pigment ink"),
        ("Wasserfest", "Waterproof"),
        ("Feathering", "Feathering"),
        ("Sättigung", "Saturation"),
        ("Fluss", "Flow"),
        ("Reinigung", "Cleaning"),
        ("Menge", "Amount"),
        ("Füllstand", "Fill level"),
        ("Flasche", "Bottle"),
        ("leer", "empty"),
        ("verfügbar", "available"),
        ("nicht leer", "not empty"),
        ("aktuell eingefüllt", "currently inked"),
        ("Händler", "Vendor"),
        ("Bestellung", "Order"),
        ("Versand", "Shipping"),
        ("Zoll", "Customs"),
        ("Zubehör", "Accessories"),
        ("Betrag", "Amount"),
        ("Preis", "Price"),
        ("Währung", "Currency"),
        ("Region", "Region"),
        ("Sprache", "Language"),
        ("nächster Start", "next start"),
        ("Standard", "Default"),
        ("Plätze", "slots"),
        ("Seiten gesamt", "pages total"),
        ("Seiten verbraucht", "pages used"),
        ("Seiten", "pages"),
        ("grammatur", "gsm"),
        ("Glätte", "smoothness"),
        ("Saugfähigkeit", "absorbency"),
        ("Geeignet", "Suitable"),
        ("Vorlage", "Template"),
        ("Keine", "No"),
        ("keine", "no"),
        ("Kein", "No"),
        ("kein", "no"),
        ("Alle", "All"),
        ("alle", "all"),
        ("Aktuell", "Current"),
        ("aktuell", "current"),
        ("Vorhandene", "Existing"),
        ("vorhandene", "existing"),
        ("Neue", "New"),
        ("neue", "new"),
        ("neu", "new"),
        ("ändern", "change"),
        ("ändern", "change"),
        ("öffnen", "open"),
        ("gespeichert", "saved"),
        ("Kurse gespeichert", "rates saved"),
        ("Alle Anzeigen werden neu geladen", "All views will be reloaded"),
        ("Anzeigen", "views"),
        ("Kurse", "rates"),
        ("geladen", "loaded"),
        ("Daten", "data"),
        ("Datei", "file"),
        ("Dateien", "files"),
        ("Pfad", "path"),
        ("Ordner", "folder"),
        ("Zeile", "row"),
        ("Zeilen", "rows"),
        ("übersprungen", "skipped"),
        ("kopiert", "copied"),
        ("unbekannt", "unknown"),
        ("wirklich", "really"),
        ("löschen", "delete"),
        ("wurde", "was"),
        ("wird", "will be"),
        ("Soll", "Should"),
        ("Bitte", "Please"),
        ("Hinweis", "Note"),
        ("Achtung", "Attention"),
        ("Letzte", "Last"),
        ("letzte", "last"),
        ("geschlossen", "closed"),
        ("Rechtsklick", "right-click"),
        ("Doppelklick", "double-click"),
        ("links", "left"),
        ("rechts", "right"),
        ("Modul", "module"),
        ("Bereich", "area"),
        ("Bereiche", "areas"),
        ("Fenster", "windows"),
        ("Dialog", "dialog"),
        ("Dialoge", "dialogs"),
        ("Texte", "texts"),
        ("Text", "text"),
        ("Schrift", "font"),
        ("Eingabefelder", "input fields"),
        ("Buttons", "buttons"),
        ("gesamten App", "entire app"),
    ],
    "fr": [
        ("FountainPen Manager", "FountainPen Manager"),
        ("Allgemeine Einstellungen", "Paramètres généraux"),
        ("Programmeinstellungen", "Paramètres de l'application"),
        ("Währung & Region", "Devise & région"),
        ("Datenbank & Backup", "Base de données & sauvegarde"),
        ("Import / Export", "Import / Export"),
        ("Reset / Gefahrenzone", "Réinitialisation / zone dangereuse"),
        ("Darstellung speichern & sofort anwenden", "Enregistrer l'apparence et appliquer maintenant"),
        ("Wechselkurse & Region speichern", "Enregistrer les taux de change et la région"),
        ("ALLE DATEN LÖSCHEN", "SUPPRIMER TOUTES LES DONNÉES"),
        ("Factory Reset", "Réinitialisation d'usine"),
        ("Füller-Status reset", "Réinitialiser le statut des stylos"),
        ("Tintenmengen reset", "Réinitialiser les niveaux d'encre"),
        ("InkLoads schließen", "Clôturer les remplissages"),
        ("Datenbankpfad", "Chemin de la base de données"),
        ("Datenbank", "Base de données"),
        ("Wechselkurse", "Taux de change"),
        ("Standardwährung", "Devise par défaut"),
        ("Zahlenformat", "Format des nombres"),
        ("Voreinstellung", "préréglage"),
        ("Dezimaltrennzeichen", "Séparateur décimal"),
        ("Tausendertrennzeichen", "Séparateur de milliers"),
        ("Apostroph", "Apostrophe"),
        ("Komma", "Virgule"),
        ("Punkt", "Point"),
        ("Keines", "Aucun"),
        ("Vorschau", "Aperçu"),
        ("Empfehlung", "Recommandation"),
        ("Durchsuchen", "Parcourir"),
        ("Ordner öffnen", "Ouvrir le dossier"),
        ("Pfad ändern", "Modifier le chemin"),
        ("Optimieren", "Optimiser"),
        ("CSV-Export starten", "Lancer l'export CSV"),
        ("Navigation anpassen", "Personnaliser la navigation"),
        ("Regeln & Reinigungszeiten", "Règles & délais de nettoyage"),
        ("Hilfe & Regel-Erklärungen", "Aide & explications des règles"),
        ("Ausgaben-Tracker", "Suivi des dépenses"),
        ("Intelligente Rotation", "Rotation intelligente"),
        ("Vorschläge für leere Füller", "Suggestions pour stylos vides"),
        ("Freie Tinten", "Encres disponibles"),
        ("Aktuelle Belegung", "Remplissages actuels"),
        ("Letzte Einfüllungen", "Derniers remplissages"),
        ("Ink Safety Timer", "Minuteur de sécurité d'encre"),
        ("Service & Sperren", "Service & blocage"),
        ("Sperren/Service", "Blocage/Service"),
        ("Sperren", "Bloquer"),
        ("Gesperrt", "Bloqué"),
        ("Service", "Service"),
        ("Austrocknung", "Dessèchement"),
        ("Reinigung fällig", "Nettoyage dû"),
        ("Überfällig", "En retard"),
        ("Safety-Warnungen", "alertes de sécurité"),
        ("Safety-Timer", "minuteurs de sécurité"),
        ("Regelverstöße", "violations de règles"),
        ("Regelverletzungen", "violations de règles"),
        ("Regelüberschreibung", "exception à la règle"),
        ("harte Regel", "règle stricte"),
        ("Warnungen", "Avertissements"),
        ("Warnung", "Avertissement"),
        ("Fehler", "Erreurs"),
        ("Fehlern", "erreurs"),
        ("OK", "OK"),
        ("Einfüllen", "Remplir"),
        ("Tinte einfüllen", "Remplir avec une encre"),
        ("Leeren und direkt neu befüllen", "Vider et remplir directement"),
        ("Leer markieren", "Marquer vide"),
        ("Gereinigt", "Nettoyé"),
        ("Als gereinigt markieren", "Marquer comme nettoyé"),
        ("Aktualisieren", "Actualiser"),
        ("Vorschläge", "Suggestions"),
        ("Vorschlag", "Suggestion"),
        ("Übernehmen", "Appliquer"),
        ("Bearbeiten", "Modifier"),
        ("Löschen", "Supprimer"),
        ("Speichern", "Enregistrer"),
        ("Hinzufügen", "Ajouter"),
        ("hinzufügen", "ajouter"),
        ("Erstellen", "Créer"),
        ("erstellen", "créer"),
        ("Kopieren", "Copier"),
        ("kopieren", "copier"),
        ("Refill", "Recharge"),
        ("Importieren", "Importer"),
        ("importieren", "importer"),
        ("Exportieren", "Exporter"),
        ("exportieren", "exporter"),
        ("Archivieren", "Archiver"),
        ("Archivierte", "Archivés"),
        ("Archiviert", "Archivé"),
        ("archiviert", "archivé"),
        ("Wiederherstellen", "Restaurer"),
        ("Zurücksetzen", "Réinitialiser"),
        ("zurückgesetzt", "réinitialisé"),
        ("Schließen", "Fermer"),
        ("schließen", "fermer"),
        ("Abbrechen", "Annuler"),
        ("Fortfahren", "Continuer"),
        ("Bestätigen", "Confirmer"),
        ("Auswählen", "Sélectionner"),
        ("auswählen", "sélectionner"),
        ("Suchen", "Rechercher"),
        ("Filter", "Filtre"),
        ("Status setzen", "Définir le statut"),
        ("Als gekauft übernehmen", "Convertir comme acheté"),
        ("gekauft", "acheté"),
        ("reserviert", "réservé"),
        ("geplant", "prévu"),
        ("offen", "ouvert"),
        ("Pflicht", "Obligatoire"),
        ("verheiratet", "associé"),
        ("feste Paarung", "association fixe"),
        ("Pflicht-Bonus", "bonus obligatoire"),
        ("Beliebtheit", "popularité"),
        ("Score", "Score"),
        ("Score-Legende", "Légende du score"),
        ("Warum", "Pourquoi"),
        ("Grund", "Raison"),
        ("Notizen", "Notes"),
        ("Kommentar", "Commentaire"),
        ("Beschreibung", "Description"),
        ("Kategorie", "Catégorie"),
        ("Kategorien", "Catégories"),
        ("Tags", "Étiquettes"),
        ("Tabelle", "Tableau"),
        ("Tabellen", "Tableaux"),
        ("Dichte", "densité"),
        ("Füllerverwaltung", "Gestion des stylos"),
        ("Füller", "Stylos"),
        ("Tintenverwaltung", "Gestion des encres"),
        ("Tinten", "Encres"),
        ("Tinte", "Encre"),
        ("Federverwaltung", "Gestion des plumes"),
        ("Federn", "Plumes"),
        ("Feder", "Plume"),
        ("Papierverwaltung", "Gestion du papier"),
        ("Papier", "Papier"),
        ("Ausgaben", "Dépenses"),
        ("Ausgabe", "Dépense"),
        ("Einstellungen", "Paramètres"),
        ("Regeln", "Règles"),
        ("Regel", "Règle"),
        ("Hilfe", "Aide"),
        ("Dashboard", "Tableau de bord"),
        ("Rotation", "Rotation"),
        ("Wishlist", "Liste d'envies"),
        ("Allgemein", "Général"),
        ("Darstellung", "Apparence"),
        ("Über", "À propos"),
        ("Marke", "Marque"),
        ("Modell", "Modèle"),
        ("Name", "Nom"),
        ("Farbe", "Couleur"),
        ("Grundfarbe", "Couleur de base"),
        ("Farbfamilie", "Famille de couleur"),
        ("Farbspektrum", "Spectre de couleurs"),
        ("Füllsystem", "Système de remplissage"),
        ("Kaufdatum", "Date d'achat"),
        ("Kaufpreis", "Prix d'achat"),
        ("Marktwert", "Valeur de marché"),
        ("Versicherungswert", "Valeur d'assurance"),
        ("Länge", "Longueur"),
        ("Durchmesser", "Diamètre"),
        ("Gewicht", "Poids"),
        ("Größe", "Taille"),
        ("Größenvergleich", "Comparaison de tailles"),
        ("Griff", "Grip"),
        ("geschlossen", "fermé"),
        ("offen", "ouvert"),
        ("gepostet", "posté"),
        ("Schreibgefühl", "Sensation d'écriture"),
        ("Probleme", "Problèmes"),
        ("Problemfüller", "stylo problématique"),
        ("Reinigung", "Nettoyage"),
        ("Aktuelle Tinte", "Encre actuelle"),
        ("Leer", "Vide"),
        ("Tage eingefüllt", "Jours encrés"),
        ("Tage im Füller", "jours dans le stylo"),
        ("Tage", "jours"),
        ("Tag", "jour"),
        ("Eingefüllt seit", "Rempli depuis"),
        ("Nässe", "Humidité"),
        ("Sheen", "Sheen"),
        ("Shimmer", "Paillettes"),
        ("Schimmer", "Paillettes"),
        ("Shading", "Ombrage"),
        ("Pigmenttinte", "Encre pigmentaire"),
        ("Wasserfest", "Résistant à l'eau"),
        ("Feathering", "Feathering"),
        ("Sättigung", "Saturation"),
        ("Fluss", "Débit"),
        ("Menge", "Quantité"),
        ("Füllstand", "Niveau"),
        ("Flasche", "Flacon"),
        ("leer", "vide"),
        ("verfügbar", "disponible"),
        ("nicht leer", "non vide"),
        ("aktuell eingefüllt", "actuellement rempli"),
        ("Händler", "Vendeur"),
        ("Bestellung", "Commande"),
        ("Versand", "Expédition"),
        ("Zoll", "Douane"),
        ("Zubehör", "Accessoires"),
        ("Betrag", "Montant"),
        ("Preis", "Prix"),
        ("Währung", "Devise"),
        ("Region", "Région"),
        ("Sprache", "Langue"),
        ("nächster Start", "prochain démarrage"),
        ("Standard", "Défaut"),
        ("Plätze", "emplacements"),
        ("Seiten gesamt", "pages au total"),
        ("Seiten verbraucht", "pages utilisées"),
        ("Seiten", "pages"),
        ("grammatur", "grammage"),
        ("Glätte", "lissage"),
        ("Saugfähigkeit", "absorption"),
        ("Geeignet", "Adapté"),
        ("Vorlage", "Modèle"),
        ("Keine", "Aucun"),
        ("keine", "aucun"),
        ("Kein", "Aucun"),
        ("kein", "aucun"),
        ("Alle", "Tous"),
        ("alle", "tous"),
        ("Aktuell", "Actuel"),
        ("aktuell", "actuel"),
        ("Vorhandene", "Existant"),
        ("vorhandene", "existant"),
        ("Neue", "Nouveau"),
        ("neue", "nouveau"),
        ("neu", "nouveau"),
        ("ändern", "modifier"),
        ("öffnen", "ouvrir"),
        ("gespeichert", "enregistré"),
        ("Kurse gespeichert", "taux enregistrés"),
        ("Alle Anzeigen werden neu geladen", "Toutes les vues seront rechargées"),
        ("Anzeigen", "vues"),
        ("Kurse", "taux"),
        ("geladen", "chargé"),
        ("Daten", "données"),
        ("Datei", "fichier"),
        ("Dateien", "fichiers"),
        ("Pfad", "chemin"),
        ("Ordner", "dossier"),
        ("Zeile", "ligne"),
        ("Zeilen", "lignes"),
        ("übersprungen", "ignoré"),
        ("kopiert", "copié"),
        ("unbekannt", "inconnu"),
        ("wirklich", "vraiment"),
        ("löschen", "supprimer"),
        ("wurde", "a été"),
        ("wird", "sera"),
        ("Soll", "Faut-il"),
        ("Bitte", "Veuillez"),
        ("Hinweis", "Remarque"),
        ("Achtung", "Attention"),
        ("Letzte", "Dernier"),
        ("letzte", "dernier"),
        ("geschlossen", "fermé"),
        ("Rechtsklick", "clic droit"),
        ("Doppelklick", "double-clic"),
        ("links", "gauche"),
        ("rechts", "droite"),
        ("Modul", "module"),
        ("Bereich", "domaine"),
        ("Bereiche", "domaines"),
        ("Fenster", "fenêtres"),
        ("Dialog", "dialogue"),
        ("Dialoge", "dialogues"),
        ("Texte", "textes"),
        ("Text", "texte"),
        ("Schrift", "police"),
        ("Eingabefelder", "champs de saisie"),
        ("Buttons", "boutons"),
        ("gesamten App", "toute l'application"),
    ],
}

# Make phrase replacement deterministic: longer phrases first.
for _lang, _items in _PHRASES.items():
    _PHRASES[_lang] = sorted(_items, key=lambda pair: len(pair[0]), reverse=True)


def _strip_hotkeys(text: str) -> str:
    # Qt uses & for keyboard mnemonics.  Translate the visible text but preserve
    # escaped && by leaving the string otherwise intact.
    return _HOTKEY_RE.sub("", text)


def _translate_plain(text: str, lang: str) -> str:
    if not text or lang == "de":
        return text

    exact = _any_json_map(lang).get(text)
    if exact is not None:
        return exact
    exact = _reverse_json_map(lang).get(text)
    if exact is not None:
        return exact
    exact = _EXACT.get(lang, {}).get(text)
    if exact is not None:
        return exact

    original = text
    translated = text
    for source, target in _PHRASES.get(lang, []):
        if not source:
            continue
        if source in translated:
            # Single-word phrase fallbacks must not replace inside longer words.
            # Example: "geschlossen" must not turn "abgeschlossen" into
            # "abclosed".  Multi-word phrases intentionally remain phrase-based.
            if re.fullmatch(r"[\wÀ-ÖØ-öø-ÿ]+", source, flags=re.UNICODE):
                pattern = rf"(?<![\wÀ-ÖØ-öø-ÿ]){re.escape(source)}(?![\wÀ-ÖØ-öø-ÿ])"
                translated = re.sub(pattern, target, translated)
            else:
                translated = translated.replace(source, target)

    # Avoid returning half-translated Qt mnemonics only.
    return translated if translated != original else original


def translate_source_text(text: str | None, lang: str | None = None) -> str:
    """Translate a German source/fallback UI string to the active language."""
    if text is None:
        return ""
    if not isinstance(text, str):
        return text
    lang = lang or Translator.instance().language
    if lang == "de" or not text.strip():
        return text

    # Never translate pure numbers, unit-only fragments or stylesheet snippets.
    stripped = text.strip()
    if not stripped:
        return text
    if stripped.startswith(("QWidget", "QFrame", "QMainWindow", "#")):
        return text
    if re.fullmatch(r"[\d\s.,'/:+\-–—|()%#×✓✕✅❌⚠ℹ⭐💍]+", stripped):
        return text

    # Translate HTML text segment-by-segment, preserving tags/attributes.
    if "<" in text and ">" in text:
        parts = _TAG_RE.split(text)
        return "".join(part if _TAG_RE.fullmatch(part) else _translate_plain(part, lang) for part in parts)

    return _translate_plain(text, lang)


# ── Qt object traversal ──────────────────────────────────────────────────────

def _source_property(obj, prop_name: str, current: str) -> str:
    try:
        stored = obj.property(prop_name)
        if isinstance(stored, str):
            return stored
        obj.setProperty(prop_name, current)
    except Exception:
        pass
    return current


def _set_translated(obj, prop_name: str, getter, setter):
    try:
        current = getter()
        source = _source_property(obj, prop_name, current)
        new_value = translate_source_text(source)
        if isinstance(new_value, str) and new_value != current:
            setter(new_value)
    except Exception:
        pass


def _translate_action(action) -> None:
    _set_translated(action, "_fpm_i18n_action_text", action.text, action.setText)
    try:
        tip = action.toolTip()
        if tip:
            source = _source_property(action, "_fpm_i18n_action_tooltip", tip)
            action.setToolTip(translate_source_text(source))
    except Exception:
        pass
    try:
        stat = action.statusTip()
        if stat:
            source = _source_property(action, "_fpm_i18n_action_status", stat)
            action.setStatusTip(translate_source_text(source))
    except Exception:
        pass


def _translate_combo(combo) -> None:
    """Translate static combo labels without reusing stale item text caches.

    Earlier runtime wiring stored the complete item-text list on first pass.
    That breaks when a combo is repopulated with the same item count but new
    content.  Store the per-item source text in Qt.UserRole+n instead, and
    invalidate it whenever the visible text no longer matches either the
    source or its current translation.  User data in Qt.UserRole remains
    untouched.
    """
    try:
        from PySide6.QtCore import Qt
        role = int(Qt.ItemDataRole.UserRole) + 996
        for i in range(combo.count()):
            current = combo.itemText(i)
            source = combo.itemData(i, role)
            if isinstance(source, str):
                translated = translate_source_text(source)
                if current not in (source, translated):
                    # Item was repopulated/changed after the last translation.
                    source = current
                    combo.setItemData(i, source, role)
            else:
                source = current
                combo.setItemData(i, source, role)
            new_value = translate_source_text(source)
            if new_value != current:
                combo.setItemText(i, new_value)
    except Exception:
        pass


def _translate_list_widget(list_widget) -> None:
    try:
        from PySide6.QtCore import Qt
        role = int(Qt.ItemDataRole.UserRole) + 997
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is None:
                continue
            source = item.data(role)
            if not isinstance(source, str):
                source = item.text()
                item.setData(role, source)
            new_value = translate_source_text(source)
            if new_value != item.text():
                item.setText(new_value)
    except Exception:
        pass


def _translate_table_headers(table) -> None:
    try:
        from PySide6.QtCore import Qt
        role = int(Qt.ItemDataRole.UserRole) + 998
        for col in range(table.columnCount()):
            item = table.horizontalHeaderItem(col)
            if item is not None:
                source = item.data(role)
                if not isinstance(source, str):
                    source = item.text()
                    item.setData(role, source)
                new_value = translate_source_text(source)
                if new_value != item.text():
                    item.setText(new_value)
        for row in range(table.rowCount()):
            item = table.verticalHeaderItem(row)
            if item is not None:
                source = item.data(role)
                if not isinstance(source, str):
                    source = item.text()
                    item.setData(role, source)
                new_value = translate_source_text(source)
                if new_value != item.text():
                    item.setText(new_value)
    except Exception:
        pass


def apply_widget_tree(root) -> None:
    """Translate visible static text inside a QWidget/QDialog subtree."""
    if root is None:
        return
    try:
        from PySide6.QtWidgets import (
            QWidget, QLabel, QAbstractButton, QGroupBox, QLineEdit, QComboBox,
            QTabWidget, QListWidget, QTableWidget, QMenu, QToolBar,
        )
    except Exception:
        return

    widgets = []
    try:
        if isinstance(root, QWidget):
            widgets.append(root)
            widgets.extend(root.findChildren(QWidget))
    except Exception:
        return

    for widget in widgets:
        # Window titles for dialogs/pages.
        try:
            title = widget.windowTitle()
            if title:
                source = _source_property(widget, "_fpm_i18n_window_title", title)
                widget.setWindowTitle(translate_source_text(source))
        except Exception:
            pass

        if isinstance(widget, QLabel):
            _set_translated(widget, "_fpm_i18n_text", widget.text, widget.setText)
        elif isinstance(widget, QAbstractButton):
            _set_translated(widget, "_fpm_i18n_text", widget.text, widget.setText)
        elif isinstance(widget, QGroupBox):
            _set_translated(widget, "_fpm_i18n_title", widget.title, widget.setTitle)
        elif isinstance(widget, QLineEdit):
            try:
                ph = widget.placeholderText()
                if ph:
                    source = _source_property(widget, "_fpm_i18n_placeholder", ph)
                    widget.setPlaceholderText(translate_source_text(source))
            except Exception:
                pass
        elif isinstance(widget, QComboBox):
            _translate_combo(widget)
        elif isinstance(widget, QTabWidget):
            try:
                for i in range(widget.count()):
                    txt = widget.tabText(i)
                    sources = widget.property("_fpm_i18n_tab_texts")
                    if not isinstance(sources, list) or len(sources) != widget.count():
                        sources = [widget.tabText(j) for j in range(widget.count())]
                        widget.setProperty("_fpm_i18n_tab_texts", sources)
                    new_txt = translate_source_text(sources[i])
                    if new_txt != txt:
                        widget.setTabText(i, new_txt)
            except Exception:
                pass
        elif isinstance(widget, QListWidget):
            _translate_list_widget(widget)
        elif isinstance(widget, QTableWidget):
            _translate_table_headers(widget)
        elif isinstance(widget, QMenu):
            try:
                source = _source_property(widget, "_fpm_i18n_menu_title", widget.title())
                widget.setTitle(translate_source_text(source))
            except Exception:
                pass

        # Actions live on toolbars, menus and some widgets.
        try:
            for action in widget.actions():
                _translate_action(action)
        except Exception:
            pass

        if isinstance(widget, QToolBar):
            _set_translated(widget, "_fpm_i18n_toolbar_title", widget.windowTitle, widget.setWindowTitle)


def install_qt_i18n_hooks() -> None:
    """Install narrow Qt i18n helpers for transient dialogs only.

    This deliberately does *not* patch QWidget.show.  Static page text is wired
    through explicit t("...") keys, so repeatedly walking large widget trees on
    every show() would be unnecessary and costly.  The remaining hooks only
    cover tiny transient objects created by Qt convenience APIs.
    """
    try:
        from PySide6.QtWidgets import QDialog, QMenu, QMessageBox, QFileDialog, QInputDialog
    except Exception:
        return

    if getattr(QMessageBox, "_fpm_i18n_dialog_hooks_installed", False):
        return
    QMessageBox._fpm_i18n_dialog_hooks_installed = True

    _orig_dialog_exec = QDialog.exec

    def _dialog_exec(self, *args, **kwargs):
        # Dialog subtrees are small and created on demand.  This keeps legacy
        # transient dialogs safe without a global QWidget.show hook.
        apply_widget_tree(self)
        return _orig_dialog_exec(self, *args, **kwargs)

    QDialog.exec = _dialog_exec

    _orig_menu_exec = QMenu.exec

    def _menu_exec(self, *args, **kwargs):
        # Menus are tiny; translate immediately before opening.
        apply_widget_tree(self)
        return _orig_menu_exec(self, *args, **kwargs)

    QMenu.exec = _menu_exec
    if hasattr(QMenu, "popup"):
        _orig_popup = QMenu.popup

        def _popup(self, *args, **kwargs):
            apply_widget_tree(self)
            return _orig_popup(self, *args, **kwargs)

        QMenu.popup = _popup

    def _wrap_msgbox(fn_name: str):
        original = getattr(QMessageBox, fn_name)

        def _wrapped(*args, **kwargs):
            args = list(args)
            if len(args) >= 2 and isinstance(args[1], str):
                args[1] = translate_source_text(args[1])
            if len(args) >= 3 and isinstance(args[2], str):
                args[2] = translate_source_text(args[2])
            if "title" in kwargs:
                kwargs["title"] = translate_source_text(kwargs["title"])
            if "text" in kwargs:
                kwargs["text"] = translate_source_text(kwargs["text"])
            return original(*args, **kwargs)

        setattr(QMessageBox, fn_name, staticmethod(_wrapped))

    for name in ("information", "warning", "critical", "question"):
        try:
            _wrap_msgbox(name)
        except Exception:
            pass

    def _wrap_file_dialog(fn_name: str):
        original = getattr(QFileDialog, fn_name)

        def _wrapped(*args, **kwargs):
            args = list(args)
            if len(args) >= 2 and isinstance(args[1], str):
                args[1] = translate_source_text(args[1])
            if len(args) >= 4 and isinstance(args[3], str):
                args[3] = translate_source_text(args[3])
            return original(*args, **kwargs)

        setattr(QFileDialog, fn_name, staticmethod(_wrapped))

    for name in ("getOpenFileName", "getSaveFileName", "getExistingDirectory"):
        try:
            _wrap_file_dialog(name)
        except Exception:
            pass

    def _wrap_input_dialog(fn_name: str):
        original = getattr(QInputDialog, fn_name)

        def _wrapped(*args, **kwargs):
            args = list(args)
            if len(args) >= 2 and isinstance(args[1], str):
                args[1] = translate_source_text(args[1])
            if len(args) >= 3 and isinstance(args[2], str):
                args[2] = translate_source_text(args[2])
            return original(*args, **kwargs)

        setattr(QInputDialog, fn_name, staticmethod(_wrapped))

    for name in ("getText", "getItem", "getInt", "getDouble"):
        try:
            _wrap_input_dialog(name)
        except Exception:
            pass
