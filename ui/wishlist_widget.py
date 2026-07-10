"""Wishlist-Modul mit generischer Artikelkarte und Übernahme in Sammlung/Ausgaben."""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QComboBox, QSpinBox, QMessageBox,
    QDialogButtonBox, QMenu, QStackedWidget
)

from ui.locale_widgets import (
    LocalizedDoubleSpinBox as QDoubleSpinBox,
    bind_currency_combo,
    current_currency,
    populate_currency_combo,
    set_combo_currency,
)
from ui.ui_scale import scale_px
from ui.common import EmptyStateWidget
from database.db import get_session
from database.models import WishlistItem, Expense, Pen, Ink, Nib, NibFormat, Paper
from i18n.translator import LocaleService, format_money, t
from logic.article_card_service import ensure_article_card
from logic.event_bus import AppEventBus
from logic.budget_export_service import sync_default_outbox_from_session
from ui.theme import BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS, BTN_DANGER

TYPE_KEYS = ["pen", "ink", "nib", "paper", "accessory", "service"]
STATUS_KEYS = ["wish", "watching", "ordered", "bought", "rejected"]

def _wishlist_types():
    return {key: t(f"wishlist.types.{key}") for key in TYPE_KEYS}

def _wishlist_statuses():
    return {key: t(f"wishlist.statuses.{key}") for key in STATUS_KEYS}


class WishlistWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        hdr = QHBoxLayout()
        title = QLabel(t('ui.wishlist_widget.wishlist_034c68ba'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()
        add = QPushButton(t('ui.wishlist_widget.wunsch_bd625c0d'))
        add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        hdr.addWidget(add)
        root.addLayout(hdr)

        info = QLabel(t('ui.wishlist_widget.alles_kann_als_wunsch_erfasst_werden_fuller_tint_d1d13013'))
        info.setWordWrap(True)
        root.addWidget(info)

        # Filterzeile: Suche + Statusfilter (Default: aktive Wünsche)
        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("common.search"))
        self.search_edit.textChanged.connect(lambda *_: self.refresh())
        filter_row.addWidget(self.search_edit, 1)
        self.status_filter = QComboBox()
        self.status_filter.addItem(t("wishlist.filter_active"), "active")
        self.status_filter.addItem(t("wishlist.filter_all"), "all")
        for key, label in _wishlist_statuses().items():
            self.status_filter.addItem(label, key)
        self.status_filter.currentIndexChanged.connect(lambda *_: self.refresh())
        filter_row.addWidget(self.status_filter)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([t('ui.wishlist_widget.typ_38dd3364'), t('ui.wishlist_widget.titel_d4de8f9c'), t('ui.wishlist_widget.status_f6e0e9f5'), t('ui.wishlist_widget.prio_18f630f7'), t('ui.wishlist_widget.preis_0aa12925'), t('ui.wishlist_widget.shop_0d430712'), t('ui.wishlist_widget.artikelkarte_ce5fc39d'), t('ui.wishlist_widget.ubernommen_57c1fbb7'), t('ui.wishlist_widget.notiz_3bb78998')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)

        # Einheitlicher Leerzustand (wie Tinten/Federn/Papier) statt blanker Tabelle.
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)                    # index 0
        self._empty_state = EmptyStateWidget(
            icon="🧾",
            title=t("ui.wishlist_widget.empty_title"),
            subtitle=t("ui.wishlist_widget.empty_subtitle"),
            action_label=t("ui.wishlist_widget.empty_action"),
            action_slot=self._add,
        )
        self.stack.addWidget(self._empty_state)             # index 1
        root.addWidget(self.stack, 1)

        # Buttonleiste: Kernaktionen sichtbar machen statt nur im Kontextmenü.
        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("\u270f  " + t("common.edit"))
        self.edit_btn.setStyleSheet(BTN_SECONDARY)
        self.edit_btn.clicked.connect(self._edit)
        self.transfer_btn = QPushButton("\U0001f6d2  " + t('ui.wishlist_widget.als_gekauft_ubernehmen_4d301ce7'))
        self.transfer_btn.setStyleSheet(BTN_SUCCESS)
        self.transfer_btn.setToolTip(t("wishlist.use_transfer_body"))
        self.transfer_btn.clicked.connect(self._mark_bought)
        self.delete_btn = QPushButton("\U0001f5d1  " + t("common.delete"))
        self.delete_btn.setStyleSheet(BTN_DANGER)
        self.delete_btn.clicked.connect(self._delete)
        for b in (self.edit_btn, self.transfer_btn, self.delete_btn):
            b.setEnabled(False)
            btn_row.addWidget(b)
        btn_row.addStretch()
        root.addLayout(btn_row)
        self.table.itemSelectionChanged.connect(self._update_buttons)


    def _update_buttons(self):
        has_sel = self._selected_id() is not None
        for b in (self.edit_btn, self.transfer_btn, self.delete_btn):
            b.setEnabled(has_sel)

    def refresh(self):
        s = get_session()
        try:
            rows = s.query(WishlistItem).order_by(WishlistItem.status, WishlistItem.priority.desc(), WishlistItem.created_at.desc()).all()
            _has_any_wishes = bool(rows)  # Leerzustand nur bei wirklich leerer Sammlung, nicht bei leerem Filter.
            # Statusfilter: "active" = wish/watching/ordered, "all" = alles, sonst exakter Status.
            mode = self.status_filter.currentData() if hasattr(self, "status_filter") else "all"
            if mode == "active":
                rows = [i for i in rows if (i.status or "wish") in ("wish", "watching", "ordered")]
            elif mode not in (None, "all"):
                rows = [i for i in rows if (i.status or "wish") == mode]
            # Suchfilter über Titel, Marke, Modell, Shop und Notizen.
            needle = (self.search_edit.text() if hasattr(self, "search_edit") else "").strip().lower()
            if needle:
                def _hit(i):
                    hay = " ".join(filter(None, [i.title, i.brand, i.model, i.variant, i.shop, i.notes, i.reason])).lower()
                    return needle in hay
                rows = [i for i in rows if _hit(i)]
            self.stack.setCurrentIndex(1 if not _has_any_wishes else 0)
            self.table.setRowCount(len(rows))
            for r, item in enumerate(rows):
                first = QTableWidgetItem(_wishlist_types().get(item.item_type, item.item_type))
                first.setData(Qt.ItemDataRole.UserRole, item.id)
                self.table.setItem(r, 0, first)
                self.table.setItem(r, 1, QTableWidgetItem(item.title or ""))
                self.table.setItem(r, 2, QTableWidgetItem(_wishlist_statuses().get(item.status, item.status)))
                self.table.setItem(r, 3, QTableWidgetItem(str(item.priority or 3)))
                price = item.actual_price or item.expected_price or item.desired_price
                cur = item.currency or LocaleService.instance().currency
                self.table.setItem(r, 4, QTableWidgetItem(format_money(price, cur) if price is not None else "—"))
                self.table.setItem(r, 5, QTableWidgetItem(item.shop or ""))
                self.table.setItem(r, 6, QTableWidgetItem(item.article_card_path or "—"))
                übernommen = f"{item.created_object_type} #{item.created_object_id}" if item.created_object_id else "—"
                self.table.setItem(r, 7, QTableWidgetItem(übernommen))
                self.table.setItem(r, 8, QTableWidgetItem((item.notes or item.reason or "")[:120]))
        finally:
            s.close()

    def _selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
        menu = QMenu(self)
        add = menu.addAction(t('ui.wishlist_widget.wunsch_bd625c0d'))
        edit = menu.addAction(t('ui.wishlist_widget.bearbeiten_12de14ad'))
        status_menu = menu.addMenu(t("wishlist.status_menu"))
        status_actions = {}
        for key, label in _wishlist_statuses().items():
            # "Gekauft" führt über _set_status zur nachvollziehbaren Übernahme.
            status_actions[status_menu.addAction(label)] = key
        bought = menu.addAction(t('ui.wishlist_widget.als_gekauft_ubernehmen_4d301ce7'))
        card = menu.addAction(t('ui.wishlist_widget.artikelkarte_aktualisieren_cccfc2c6'))
        delete = menu.addAction(t('ui.wishlist_widget.loschen_5a2946a1'))
        has = self._selected_id() is not None
        for a in (edit, bought, card, delete):
            a.setEnabled(has)
        status_menu.setEnabled(has)
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == add:
            self._add()
        elif act == edit:
            self._edit()
        elif act in status_actions:
            self._set_status(status_actions[act])
        elif act == bought:
            self._mark_bought()
        elif act == card:
            self._update_card()
        elif act == delete:
            self._delete()

    def _add(self):
        dlg = WishlistDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_id = None
            wants_bought = False
            s = get_session()
            try:
                data = dlg.data()
                wants_bought = data.get("status") == "bought"
                if wants_bought:
                    # Nie still auf gekauft: erst als Wunsch speichern,
                    # danach die nachvollziehbare Übernahme starten.
                    data["status"] = "wish"
                item = WishlistItem(**data)
                s.add(item)
                s.commit()
                item.article_card_path = ensure_article_card(item)
                s.commit()
                new_id = item.id
                self.refresh()
            finally:
                s.close()
            if wants_bought and new_id:
                self._transfer_item(new_id)

    def _edit(self):
        wid = self._selected_id()
        if not wid:
            return
        s = get_session()
        try:
            item = s.get(WishlistItem, wid)
            if not item:
                return
            dlg = WishlistDialog(self, item)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.data()
                old_status = item.status or "wish"
                requested_bought = data.get("status") == "bought" and not self._is_purchase_transferred(item)

                # "Gekauft" darf nicht nur ein Statuswechsel sein: sonst landet ein
                # Wunschfüller zwar als "bought" in der Wishlist, aber nicht sauber in
                # Sammlung + Ausgaben. Deshalb werden erst die Stammdaten gespeichert und
                # dann derselbe nachvollziehbare Übernahme-Workflow genutzt wie im Kontextmenü.
                if requested_bought:
                    data["status"] = old_status

                for k, v in data.items():
                    setattr(item, k, v)
                item.updated_at = datetime.now()

                if requested_bought:
                    transfer = WishlistTransferDialog(self, item)
                    if transfer.exec() == QDialog.DialogCode.Accepted:
                        target = transfer.target_type()
                        self._apply_purchase_transfer(s, item, target)
                        s.commit()
                        self._sync_budget_bridge_after_purchase(s)
                        item.article_card_path = ensure_article_card(item)
                        s.commit()
                        self._emit_transfer_events(target)
                        self._show_transfer_result(item, target)
                    else:
                        s.commit()
                        item.article_card_path = ensure_article_card(item)
                        s.commit()
                        QMessageBox.information(self, t("wishlist.use_transfer_title"), t("wishlist.use_transfer_body"))
                else:
                    s.commit()
                    item.article_card_path = ensure_article_card(item)
                    s.commit()

                self.refresh()
        finally:
            s.close()

    def _update_card(self):
        wid = self._selected_id()
        if not wid:
            return
        s = get_session()
        try:
            item = s.get(WishlistItem, wid)
            item.article_card_path = ensure_article_card(item)
            s.commit()
            QMessageBox.information(self, t('ui.wishlist_widget.artikelkarte_ce5fc39d'), t("ui.wishlist_widget.article_card_updated", path=item.article_card_path))
            self.refresh()
        finally:
            s.close()

    def _delete(self):
        wid = self._selected_id()
        if not wid:
            return
        s = get_session()
        try:
            item = s.get(WishlistItem, wid)
            if item and QMessageBox.question(self, t('ui.wishlist_widget.loschen_15ec14b7'), t('ui.wishlist_widget.confirm_delete_item', title=item.title)) == QMessageBox.StandardButton.Yes:
                s.delete(item)
                s.commit()
                self.refresh()
        finally:
            s.close()

    def _set_status(self, status: str):
        """Status ändern, aber "gekauft" nie still in Sammlung/Ausgaben umgehen."""
        wid = self._selected_id()
        if not wid:
            return
        if status == "bought":
            self._transfer_item(wid)
            return
        s = get_session()
        try:
            item = s.get(WishlistItem, wid)
            if not item:
                return
            item.status = status
            item.updated_at = datetime.now()
            item.article_card_path = ensure_article_card(item)
            s.commit()
            QMessageBox.information(
                self,
                t("wishlist.status_changed_title"),
                t("wishlist.status_changed_body", status=_wishlist_statuses().get(status, status)),
            )
            self.refresh()
        finally:
            s.close()

    @staticmethod
    def _is_purchase_transferred(item) -> bool:
        """True, wenn ein Wishlist-Kauf bereits nachvollziehbar übernommen wurde.

        ``created_object_id`` deckt echte Sammlungsobjekte ab. Für reine Ausgaben
        (accessory/service/other) gibt es kein Objekt, deshalb zählt dort
        ``created_object_type`` als Abschlussmarker. Alte Datensätze mit
        status="bought" aber ohne Marker können weiterhin repariert/übernommen werden.
        """
        if not item:
            return False
        if getattr(item, "created_object_id", None):
            return True
        marker = getattr(item, "created_object_type", None)
        return bool(getattr(item, "status", None) == "bought" and marker in {"none", "other", "accessory", "service"})

    def _sync_budget_bridge_after_purchase(self, session) -> None:
        """Aktualisiert die FPM→BudgetManager-Outbox nach Wishlist-Käufen best-effort.

        Wichtig: Ein Wishlist-Kauf erzeugt eine normale FPM-Ausgabe. Ohne diesen
        Sync sieht der BudgetManager keine neue Füller-Ausgabe zum Importieren.
        Fehler in der Bridge dürfen die eigentliche Wishlist-Übernahme aber nie
        rückgängig machen.
        """
        try:
            sync_default_outbox_from_session(session)
        except Exception:
            pass

    def _emit_transfer_events(self, target: str) -> None:
        """Alle betroffenen Widgets nach einer Wishlist-Übernahme aktualisieren."""
        bus = AppEventBus.instance()
        bus.expenses_changed.emit()
        if target == "pen":
            bus.pens_changed.emit()
        elif target == "ink":
            bus.inks_changed.emit()
        elif target == "nib":
            bus.nibs_changed.emit()
        elif target == "paper":
            bus.papers_changed.emit()
        bus.all_changed.emit()

    def _create_collection_object(self, session, item, target: str, price: float, cur: str):
        """Erzeugt das passende Sammlungsobjekt für einen Wishlist-Kauf."""
        purchase_price = price if price > 0 else None
        if target == "pen":
            # Explizite Defaults sind hier Absicht: alte DBs/SQLAlchemy-Defaults dürfen
            # nicht dazu führen, dass ein übernommener Wunschfüller in der aktiven
            # Füllerliste durch is_active/availability NULL unsichtbar bleibt.
            return Pen(
                brand=item.brand or "",
                model=item.model or item.title,
                color=item.variant,
                fill_system="converter",
                purchase_date=item.bought_date,
                purchase_price=purchase_price,
                purchase_currency=cur,
                is_active=True,
                availability_status="available",
                rotation_blocked=False,
                popularity_rating=3,
                must_include_in_rotation=False,
                rotation_role="writer",
            )
        if target == "ink":
            return Ink(
                brand=item.brand or "",
                name=item.model or item.title,
                purchase_date=item.bought_date,
                purchase_price=purchase_price,
                purchase_currency=cur,
                is_empty=False,
                is_archived=False,
            )
        if target == "nib":
            fmt = None
            if item.brand:
                fmt = session.query(NibFormat).filter_by(manufacturer=item.brand, physical_size=item.model).first()
                if fmt is None:
                    fmt = NibFormat(manufacturer=item.brand, physical_size=item.model or None)
                    session.add(fmt)
                    session.flush()
            return Nib(
                format_id=fmt.id if fmt else None,
                manufacturer=item.brand,
                physical_size=item.model,
                size=item.variant or None,
                label=item.title,
                notes=item.notes,
            )
        if target == "paper":
            return Paper(
                brand=item.brand or "",
                name=item.model or item.title,
                paper_type="notebook",
                purchase_date=item.bought_date,
                purchase_price=purchase_price,
                purchase_currency=cur,
            )
        return None

    def _apply_purchase_transfer(self, session, item, target: str):
        """Wishlist-Kauf atomar in Status, Sammlung und Ausgaben übernehmen."""
        item.status = "bought"
        item.bought_date = datetime.now()
        item.updated_at = datetime.now()
        price = item.actual_price or item.expected_price or item.desired_price or 0.0
        cur = item.currency or LocaleService.instance().currency

        created = self._create_collection_object(session, item, target, price, cur)
        if created is not None:
            session.add(created)
            session.flush()
            item.created_object_type = target
            item.created_object_id = created.id
        elif target in {"none", "other", "accessory", "service"}:
            item.created_object_type = target
            item.created_object_id = None

        if target != "none":
            exp = Expense(
                item_type=target if target in ("pen", "ink", "nib", "paper") else item.item_type,
                amount=price,
                shipping=item.shipping or 0.0,
                customs=item.customs or 0.0,
                currency=cur,
                purchase_date=item.bought_date,
                description=t("wishlist.purchase_description", title=item.title),
                vendor=item.shop,
                notes=f"WISHLIST:{item.id}\n{item.url or ''}".strip(),
            )
            if target == "pen" and created is not None:
                exp.pen_id = created.id
            elif target == "ink" and created is not None:
                exp.ink_id = created.id
            elif target == "nib" and created is not None:
                exp.nib_id = created.id
            elif target == "paper" and created is not None:
                exp.paper_id = created.id
            session.add(exp)
        return created

    def _mark_bought(self):
        wid = self._selected_id()
        if not wid:
            return
        self._transfer_item(wid)

    def _transfer_item(self, wid: int):
        """Nachvollziehbare Übernahme: Wunsch → Sammlung + Ausgabe + Status gekauft."""
        s = get_session()
        try:
            item = s.get(WishlistItem, wid)
            if not item:
                return
            if self._is_purchase_transferred(item):
                QMessageBox.information(
                    self,
                    t("wishlist.already_transferred_title"),
                    t("wishlist.already_transferred_body", type=item.created_object_type or "?", id=item.created_object_id or "—"),
                )
                return
            dlg = WishlistTransferDialog(self, item)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            target = dlg.target_type()
            self._apply_purchase_transfer(s, item, target)
            s.commit()
            self._sync_budget_bridge_after_purchase(s)
            item.article_card_path = ensure_article_card(item)
            s.commit()
            self._emit_transfer_events(target)
            self.refresh()
            self._show_transfer_result(item, target)
        finally:
            s.close()

    def _show_transfer_result(self, item, target: str):
        """Klare Rückmeldung, was die Übernahme angelegt hat (Usability)."""
        if getattr(item, "created_object_id", None):
            QMessageBox.information(
                self,
                t("wishlist.transfer_done_title"),
                t("wishlist.transfer_done_body", type=_wishlist_types().get(target, target), id=item.created_object_id),
            )
        elif target == "none":
            QMessageBox.information(self, t("wishlist.transfer_done_title"), t("wishlist.transfer_none_body"))
        else:
            QMessageBox.information(self, t("wishlist.transfer_done_title"), t("wishlist.transfer_expense_body"))


class WishlistDialog(QDialog):
    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(t("wishlist.edit_title") if item else t("wishlist.add_title"))
        self.resize(scale_px(680), scale_px(620))
        self._setup()
        if item:
            self._load(item)

    def _setup(self):
        root = QVBoxLayout(self)
        fl = QFormLayout()
        self.type = QComboBox(); [self.type.addItem(v, k) for k, v in _wishlist_types().items()]
        self.title = QLineEdit()
        self.brand = QLineEdit(); self.model = QLineEdit(); self.variant = QLineEdit()
        self.status = QComboBox(); [self.status.addItem(v, k) for k, v in _wishlist_statuses().items()]
        self.priority = QSpinBox(); self.priority.setRange(1, 5); self.priority.setValue(3)
        self.desired = QDoubleSpinBox(); self.desired.setRange(0, 1_000_000); self.desired.setDecimals(2)
        self.expected = QDoubleSpinBox(); self.expected.setRange(0, 1_000_000); self.expected.setDecimals(2)
        self.actual = QDoubleSpinBox(); self.actual.setRange(0, 1_000_000); self.actual.setDecimals(2)
        self.currency = QComboBox(); populate_currency_combo(self.currency)
        self.shipping = QDoubleSpinBox(); self.shipping.setRange(0, 100_000); self.shipping.setDecimals(2)
        self.customs = QDoubleSpinBox(); self.customs.setRange(0, 100_000); self.customs.setDecimals(2)
        bind_currency_combo(self.currency, self.desired, self.expected, self.actual, self.shipping, self.customs)
        self.shop = QLineEdit(); self.url = QLineEdit()
        self.reason = QTextEdit(); self.reason.setMaximumHeight(80)
        self.notes = QTextEdit(); self.notes.setMaximumHeight(100)
        for lab, w in [
            (t("ui.wishlist_widget.typ_38dd3364"), self.type), (t("ui.wishlist_widget.titel_d4de8f9c"), self.title), (t("ui.wishlist_widget.brand_label"), self.brand), (t("ui.wishlist_widget.model_label"), self.model),
            (t("ui.wishlist_widget.variante_farbe_feder"), self.variant), (t("ui.wishlist_widget.status_f6e0e9f5"), self.status), (t("ui.wishlist_widget.prio_18f630f7"), self.priority),
            (t("ui.wishlist_widget.wunschpreis"), self.desired), (t("ui.wishlist_widget.expected_price"), self.expected), (t("ui.wishlist_widget.actual_price"), self.actual),
            (t("ui.wishlist_widget.currency_label"), self.currency), (t("ui.wishlist_widget.shipping_label"), self.shipping), (t("ui.wishlist_widget.customs_label"), self.customs),
            (t("ui.wishlist_widget.shop_0d430712"), self.shop), (t("ui.wishlist_widget.url_label"), self.url), (t("ui.wishlist_widget.reason_label"), self.reason), (t("ui.wishlist_widget.notes_label"), self.notes)
        ]:
            fl.addRow(lab + ":", w)
        root.addLayout(fl)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self, i):
        self.type.setCurrentIndex(max(0, self.type.findData(i.item_type)))
        self.title.setText(i.title or ""); self.brand.setText(i.brand or ""); self.model.setText(i.model or ""); self.variant.setText(i.variant or "")
        self.status.setCurrentIndex(max(0, self.status.findData(i.status)))
        self.priority.setValue(i.priority or 3)
        for widget, value in [(self.desired, i.desired_price), (self.expected, i.expected_price), (self.actual, i.actual_price), (self.shipping, i.shipping), (self.customs, i.customs)]:
            widget.setValue(float(value or 0))
        set_combo_currency(self.currency, i.currency)
        self.shop.setText(i.shop or ""); self.url.setText(i.url or "")
        self.reason.setPlainText(i.reason or ""); self.notes.setPlainText(i.notes or "")

    def _save(self):
        if not self.title.text().strip():
            QMessageBox.warning(self, t('ui.wishlist_widget.pflichtfeld_06ee348c'), t('ui.wishlist_widget.titel_fehlt_8e23cee4'))
            return
        self.accept()

    def _val(self, w):
        return float(w.value()) if w.value() > 0 else None

    def data(self):
        return {
            "item_type": self.type.currentData(), "title": self.title.text().strip(),
            "brand": self.brand.text().strip() or None, "model": self.model.text().strip() or None,
            "variant": self.variant.text().strip() or None, "status": self.status.currentData(),
            "priority": self.priority.value(), "desired_price": self._val(self.desired),
            "expected_price": self._val(self.expected), "actual_price": self._val(self.actual),
            "currency": current_currency(self.currency), "shipping": self._val(self.shipping),
            "customs": self._val(self.customs), "shop": self.shop.text().strip() or None,
            "url": self.url.text().strip() or None, "reason": self.reason.toPlainText().strip() or None,
            "notes": self.notes.toPlainText().strip() or None,
        }


class WishlistTransferDialog(QDialog):
    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.wishlist_widget.wishlist_kauf_ubernehmen_1267d6d5'))
        self.resize(scale_px(460), scale_px(220))
        root = QVBoxLayout(self)
        text = QLabel(t('ui.wishlist_widget.transfer_intro', title=item.title))
        text.setWordWrap(True)
        root.addWidget(text)
        self.target = QComboBox()
        self.target.addItem(t('ui.wishlist_widget.als_fuller_anlegen_ausgabe_d11feaac'), "pen")
        self.target.addItem(t('ui.wishlist_widget.als_tinte_anlegen_ausgabe_f509507f'), "ink")
        self.target.addItem(t('ui.wishlist_widget.als_feder_anlegen_ausgabe_06313c1e'), "nib")
        self.target.addItem(t('ui.wishlist_widget.als_papier_anlegen_ausgabe_827bb0cb'), "paper")
        self.target.addItem(t('ui.wishlist_widget.nur_ausgabe_erfassen_4a62097b'), item.item_type if item.item_type in ("accessory", "service") else "other")
        self.target.addItem(t('ui.wishlist_widget.nur_status_auf_gekauft_setzen_900b1159'), "none")
        ix = self.target.findData(item.item_type)
        if ix >= 0:
            self.target.setCurrentIndex(ix)
        root.addWidget(self.target)
        info = QLabel(t('ui.wishlist_widget.ein_wishlist_kauf_wird_nie_still_ubernommen_obje_7e755a65'))
        info.setWordWrap(True)
        root.addWidget(info)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def target_type(self):
        return self.target.currentData()
