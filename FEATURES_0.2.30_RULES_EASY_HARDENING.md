# v0.2.30 Rules Easy Hardening

Fixes gegenüber v0.2.28:

- Systemregeln bleiben individuell ausschaltbar: `_insert_default_rules()` aktiviert bestehende Systemregeln nicht mehr ungefragt erneut.
- Neuer `ui_mode`: `easy` / `expert`.
- Default ist `easy`.
- Im Easy Mode ist automatische Verbrauchs-/Restmengenbuchung immer aus.
- Die Regelgruppe `consumption` hat Default `0`.
- Im Rules-UI ist die Verbrauchsgruppe im Easy Mode deaktiviert und nicht editierbar.
- Im Expert Mode kann Verbrauch/Restmenge wieder bewusst eingeschaltet werden.
- Full Auto und Rotation nutzen weiterhin `AutoModeService.consumption_tracking_enabled()` und respektieren damit den Easy/Expert-Modus.

Akzeptanzkriterium:
- Einzelne Regel deaktivieren → App neu starten → Regel bleibt deaktiviert.
- Easy Mode → Befüllen reduziert `Ink.remaining_ml` nicht automatisch.
- Expert Mode + Verbrauchsgruppe aktiv → Befüllen reduziert `Ink.remaining_ml` wie bisher.
