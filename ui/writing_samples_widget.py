"""Schreibproben-Verwaltung – Scrivener-artiger Binder für Füller/Tinte/Papier."""
from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTreeWidget,
    QTreeWidgetItem, QDialog, QFormLayout, QComboBox, QDateEdit,
    QTextEdit, QSpinBox, QFileDialog, QMessageBox,
    QStackedWidget, QGroupBox, QMenu,
)

from database.db import get_session, _data_dir
from database.models import WritingSample, Pen, Ink, Paper, Nib
from i18n.translator import t, format_date
from logic.event_bus import AppEventBus
from logic.media_storage_service import import_writing_sample_image
from logic.writing_sample_service import (
    build_binder_tree,
    evaluate_sample,
    suggested_sample_title,
    compare_samples,
    BinderNode,
)
from ui.common import EmptyStateWidget
from ui.theme import BTN_PRIMARY
from ui.locale_widgets import LocalizedDoubleSpinBox as QDoubleSpinBox
from ui.ui_scale import scale_px

SAMPLE_TYPES = ["regular", "ink_test", "paper_test", "nib_tuning", "quote", "longform"]


def _type_label(key: str | None) -> str:
    return t(f"writing_samples.types.{key or 'regular'}")


def _pen_label(pen: Pen | None) -> str:
    return f"{pen.brand} {pen.model}".strip() if pen else "—"


def _ink_label(ink: Ink | None) -> str:
    return f"{ink.brand} {ink.name}".strip() if ink else "—"


def _paper_label(paper: Paper | None) -> str:
    return f"{paper.brand} {paper.name}".strip() if paper else "—"


def _nib_label(nib: Nib | None) -> str:
    if not nib:
        return "—"
    parts = [getattr(nib, "manufacturer", None), getattr(nib, "physical_size", None), getattr(nib, "size", None), getattr(nib, "grind", None)]
    return " ".join(str(p).strip() for p in parts if p).strip() or f"#{nib.id}"


class WritingSamplesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._visible_ids: set[int] | None = None
        self._setup_ui()
        bus = AppEventBus.instance()
        bus.samples_changed.connect(self.refresh)
        bus.pens_changed.connect(self.refresh)
        bus.inks_changed.connect(self.refresh)
        bus.papers_changed.connect(self.refresh)
        bus.nibs_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(t("writing_samples.title"))
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("writing_samples.search_placeholder"))
        self.search_edit.setMinimumWidth(scale_px(260))
        self.search_edit.textChanged.connect(self._filter)
        header.addWidget(self.search_edit)

        add_btn = QPushButton(t("writing_samples.add"))
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._add)
        header.addWidget(add_btn)
        root.addLayout(header)

        hint = QLabel(t("writing_samples.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7f8c8d; border:none; padding:2px;")
        root.addWidget(hint)

        self.stack = QStackedWidget()
        content = QSplitter(Qt.Orientation.Horizontal)

        self.binder = QTreeWidget()
        self.binder.setHeaderLabel(t("writing_samples.binder"))
        self.binder.setMinimumWidth(scale_px(260))
        self.binder.itemClicked.connect(self._binder_clicked)
        content.addWidget(self.binder)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            t("writing_samples.headers.title"),
            t("writing_samples.headers.pen"),
            t("writing_samples.headers.ink"),
            t("writing_samples.headers.paper"),
            t("writing_samples.headers.type"),
            t("writing_samples.headers.date"),
            t("writing_samples.headers.rating"),
            t("writing_samples.headers.flow"),
            t("writing_samples.headers.feathering"),
            t("writing_samples.headers.bleedthrough"),
            t("writing_samples.headers.status"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.clicked.connect(self._on_select)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        right_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.compare_btn = QPushButton("▦  " + t("writing_samples.compare"))
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self._compare_selected)
        self.edit_btn = QPushButton("✏  " + t("common.edit"))
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit)
        self.del_btn = QPushButton("🗑  " + t("common.delete"))
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.compare_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        content.addWidget(right)
        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)
        self.stack.addWidget(content)
        self._empty_state = EmptyStateWidget(
            icon="📝",
            title=t("writing_samples.empty_title"),
            subtitle=t("writing_samples.empty_subtitle"),
            action_label=t("writing_samples.add"),
            action_slot=self._add,
        )
        self.stack.addWidget(self._empty_state)
        root.addWidget(self.stack)

    def refresh(self) -> None:
        session = get_session()
        try:
            samples = session.query(WritingSample).order_by(WritingSample.written_at.desc()).all()
            if not samples:
                self.stack.setCurrentIndex(1)
                return
            self.stack.setCurrentIndex(0)
            pens = {p.id: p for p in session.query(Pen).all()}
            inks = {i.id: i for i in session.query(Ink).all()}
            papers = {p.id: p for p in session.query(Paper).all()}
            binder_root = build_binder_tree(samples, pens, inks, papers)
            self._populate_binder(binder_root)
            self._populate_table(samples)
            self._filter(self.search_edit.text())
        finally:
            session.close()

    def _populate_binder(self, root_node: BinderNode) -> None:
        self.binder.clear()
        root_item = QTreeWidgetItem([t("writing_samples.binder_all")])
        root_item.setData(0, Qt.ItemDataRole.UserRole, None)
        self.binder.addTopLevelItem(root_item)
        for child in root_node.children:
            root_item.addChild(self._tree_item(child))
        root_item.setExpanded(True)
        self.binder.setCurrentItem(root_item)
        self._visible_ids = None

    def _tree_item(self, node: BinderNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem([node.title])
        item.setData(0, Qt.ItemDataRole.UserRole, node.sample_id if node.node_type == "sample" else None)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node)
        for child in node.children:
            item.addChild(self._tree_item(child))
        if node.children:
            item.setExpanded(False)
        return item

    def _ids_from_item(self, item: QTreeWidgetItem) -> set[int]:
        sid = item.data(0, Qt.ItemDataRole.UserRole)
        ids: set[int] = set()
        if sid is not None:
            ids.add(int(sid))
        for idx in range(item.childCount()):
            ids.update(self._ids_from_item(item.child(idx)))
        return ids

    def _binder_clicked(self, item: QTreeWidgetItem) -> None:
        ids = self._ids_from_item(item)
        self._visible_ids = ids or None
        self._filter(self.search_edit.text())
        if len(ids) == 1:
            sid = next(iter(ids))
            self._select_row_by_id(sid)

    def _populate_table(self, samples: list[WritingSample]) -> None:
        self.table.setRowCount(len(samples))
        for row, s in enumerate(samples):
            status = self._status_text(s)
            values = [
                s.title,
                _pen_label(s.pen),
                _ink_label(s.ink),
                _paper_label(s.paper),
                _type_label(s.sample_type),
                format_date(s.written_at),
                f"{s.overall_rating}/5",
                f"{s.flow_level}/5",
                f"{s.feathering_level}/5",
                f"{s.bleedthrough_level}/5",
                status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "—")
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, s.id)
                if col == 10 and status != t("writing_samples.status.ok"):
                    item.setToolTip("; ".join(issue.code for issue in evaluate_sample(s)))
                self.table.setItem(row, col, item)

    def _status_text(self, sample: WritingSample) -> str:
        issues = evaluate_sample(sample)
        if not issues:
            return t("writing_samples.status.ok")
        if any(i.severity == "critical" for i in issues):
            return t("writing_samples.status.problem")
        return t("writing_samples.status.check")

    def _filter(self, text: str) -> None:
        text = (text or "").lower().strip()
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            sid = id_item.data(Qt.ItemDataRole.UserRole) if id_item else None
            by_binder = self._visible_ids is None or (sid in self._visible_ids)
            by_text = not text or any(
                self.table.item(row, c) and text in self.table.item(row, c).text().lower()
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not (by_binder and by_text))

    def _selected_id(self) -> int | None:
        ids = self._selected_ids()
        return ids[0] if ids else None

    def _selected_ids(self) -> list[int]:
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}) if self.table.selectionModel() else []
        ids: list[int] = []
        for row in rows:
            item = self.table.item(row, 0)
            if item is not None:
                ids.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return ids

    def _select_row_by_id(self, sample_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == sample_id:
                self.table.selectRow(row)
                self._on_select()
                break

    def _on_select(self) -> None:
        ids = self._selected_ids()
        has = bool(ids)
        self.compare_btn.setEnabled(len(ids) >= 2)
        self.edit_btn.setEnabled(len(ids) == 1)
        self.del_btn.setEnabled(has)

    def _compare_selected(self) -> None:
        ids = self._selected_ids()
        if len(ids) < 2:
            QMessageBox.information(self, t("common.info"), t("writing_samples.compare_select_hint"))
            return
        if len(ids) > 4:
            ids = ids[:4]
        session = get_session()
        try:
            samples = session.query(WritingSample).filter(WritingSample.id.in_(ids)).all()
            # Preserve visual selection order.
            by_id = {s.id: s for s in samples}
            samples = [by_id[i] for i in ids if i in by_id]
            pens = {p.id: p for p in session.query(Pen).all()}
            inks = {i.id: i for i in session.query(Ink).all()}
            papers = {p.id: p for p in session.query(Paper).all()}
            comparison = compare_samples(samples, pens, inks, papers)
            dlg = WritingSampleComparisonDialog(self, comparison=comparison)
            dlg.exec()
        finally:
            session.close()

    def _context_menu(self, pos) -> None:
        """Rechtsklick auf die Probenliste – nutzt die bestehenden Aktionen."""
        has_sel = self._selected_id() is not None
        multi = len(self._selected_ids()) >= 2
        menu = QMenu(self)
        act_add = menu.addAction("＋  " + t("writing_samples.add"))
        act_edit = menu.addAction("✏  " + t("common.edit"))
        act_edit.setEnabled(has_sel)
        act_compare = menu.addAction("▦  " + t("writing_samples.compare"))
        act_compare.setEnabled(multi)
        menu.addSeparator()
        act_delete = menu.addAction("🗑  " + t("common.delete"))
        act_delete.setEnabled(has_sel)

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is act_add:
            self._add()
        elif chosen is act_edit:
            self._edit()
        elif chosen is act_compare:
            self._compare_selected()
        elif chosen is act_delete:
            self._delete()

    def _store_sample_image_if_needed(self, sample: WritingSample) -> None:
        self._last_media_warning = None
        raw = getattr(sample, "image_path", None)
        if not raw:
            return
        pen = self.session.get(Pen, sample.pen_id) if hasattr(self, "session") else None
        # Widget-Methoden arbeiten mit lokalen Sessions; deshalb robust über
        # object_session umgehen, wenn keine Dialog-Session existiert.
        if pen is None and sample.pen_id:
            try:
                from sqlalchemy.orm import object_session

                sess = object_session(sample)
                pen = sess.get(Pen, sample.pen_id) if sess else None
            except Exception:
                pen = None
        try:
            imported = import_writing_sample_image(
                _data_dir(),
                raw,
                pen_id=sample.pen_id,
                brand=getattr(pen, "brand", None),
                model=getattr(pen, "model", None),
                title=sample.title,
            )
        except Exception as exc:  # media is optional; the sample itself must survive
            self._last_media_warning = str(exc)
            return
        if imported:
            sample.image_path = imported

    def _warn_media_import_failed(self) -> None:
        message = getattr(self, "_last_media_warning", None)
        if not message:
            return
        self._last_media_warning = None
        QMessageBox.warning(
            self,
            t("media.import_failed_title"),
            t("media.import_failed_body", error=message),
        )

    def _add(self) -> None:
        session = get_session()
        try:
            dlg = WritingSampleDialog(self, session=session)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                sample = WritingSample(**dlg.get_data())
                session.add(sample)
                session.flush()
                self._store_sample_image_if_needed(sample)
                session.commit()
                AppEventBus.instance().emit_samples()
                self.refresh()
                self._warn_media_import_failed()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, t("common.error"), str(exc))
        finally:
            session.close()

    def _edit(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        session = get_session()
        try:
            sample = session.get(WritingSample, sid)
            if sample is None:
                return
            dlg = WritingSampleDialog(self, session=session, sample=sample)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for key, value in dlg.get_data().items():
                    setattr(sample, key, value)
                sample.updated_at = datetime.now()
                session.flush()
                self._store_sample_image_if_needed(sample)
                session.commit()
                AppEventBus.instance().emit_samples()
                self.refresh()
                self._warn_media_import_failed()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, t("common.error"), str(exc))
        finally:
            session.close()

    def _delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        session = get_session()
        try:
            sample = session.get(WritingSample, sid)
            if sample is None:
                return
            if QMessageBox.question(
                self,
                t("writing_samples.delete_title"),
                t("writing_samples.delete_confirm", title=sample.title),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                session.delete(sample)
                session.commit()
                AppEventBus.instance().emit_samples()
                self.refresh()
                self._warn_media_import_failed()
        finally:
            session.close()


class WritingSampleDialog(QDialog):
    def __init__(self, parent=None, *, session, sample: Optional[WritingSample] = None, defaults: dict | None = None):
        super().__init__(parent)
        self.session = session
        self.sample = sample
        self.defaults = defaults or {}
        self.setWindowTitle(t("writing_samples.edit_title") if sample else t("writing_samples.add_title"))
        self.setMinimumWidth(scale_px(680))
        self._setup_ui()
        self._load_choices()
        if sample:
            self._load_sample(sample)
        else:
            self._apply_defaults()
            self._auto_title()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        base = QGroupBox(t("writing_samples.groups.base"))
        form = QFormLayout(base)
        self.title_edit = QLineEdit()
        self.type_combo = QComboBox()
        for key in SAMPLE_TYPES:
            self.type_combo.addItem(_type_label(key), key)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.pen_combo = QComboBox()
        self.ink_combo = QComboBox()
        self.paper_combo = QComboBox()
        self.nib_combo = QComboBox()
        for combo in (self.pen_combo, self.ink_combo, self.paper_combo, self.nib_combo):
            combo.currentIndexChanged.connect(self._auto_title_if_empty)
        form.addRow(t("writing_samples.fields.title"), self.title_edit)
        form.addRow(t("writing_samples.fields.type"), self.type_combo)
        form.addRow(t("writing_samples.fields.date"), self.date_edit)
        form.addRow(t("writing_samples.fields.pen"), self.pen_combo)
        form.addRow(t("writing_samples.fields.ink"), self.ink_combo)
        form.addRow(t("writing_samples.fields.paper"), self.paper_combo)
        form.addRow(t("writing_samples.fields.nib"), self.nib_combo)
        root.addWidget(base)

        text_group = QGroupBox(t("writing_samples.groups.evidence"))
        text_form = QFormLayout(text_group)
        self.sample_text = QTextEdit()
        self.sample_text.setPlaceholderText(t("writing_samples.sample_text_placeholder"))
        self.sample_text.setMinimumHeight(scale_px(100))
        img_row = QHBoxLayout()
        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText(t("writing_samples.image_placeholder"))
        browse_btn = QPushButton(t("writing_samples.browse"))
        browse_btn.clicked.connect(self._browse_image)
        img_row.addWidget(self.image_edit, 1)
        img_row.addWidget(browse_btn)
        text_form.addRow(t("writing_samples.fields.text"), self.sample_text)
        text_form.addRow(t("writing_samples.fields.image"), img_row)
        root.addWidget(text_group)

        metrics = QGroupBox(t("writing_samples.groups.metrics"))
        mf = QFormLayout(metrics)
        self.line_width = QDoubleSpinBox(); self.line_width.setRange(0, 5); self.line_width.setDecimals(2); self.line_width.setSuffix(" mm")
        self.dry_time = QDoubleSpinBox(); self.dry_time.setRange(0, 600); self.dry_time.setDecimals(0); self.dry_time.setSuffix(" s")
        self.feathering = self._spin5(default=1)
        self.bleedthrough = self._spin5(default=1)
        self.shading = self._spin5(default=3)
        self.sheen = self._spin5(default=0, minimum=0)
        self.flow = self._spin5(default=3)
        self.feedback = self._spin5(default=3)
        self.rating = self._spin5(default=3)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText(t("writing_samples.tags_placeholder"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(scale_px(70))
        mf.addRow(t("writing_samples.fields.line_width"), self.line_width)
        mf.addRow(t("writing_samples.fields.dry_time"), self.dry_time)
        mf.addRow(t("writing_samples.fields.feathering"), self.feathering)
        mf.addRow(t("writing_samples.fields.bleedthrough"), self.bleedthrough)
        mf.addRow(t("writing_samples.fields.shading"), self.shading)
        mf.addRow(t("writing_samples.fields.sheen"), self.sheen)
        mf.addRow(t("writing_samples.fields.flow"), self.flow)
        mf.addRow(t("writing_samples.fields.feedback"), self.feedback)
        mf.addRow(t("writing_samples.fields.rating"), self.rating)
        mf.addRow(t("writing_samples.fields.tags"), self.tags_edit)
        mf.addRow(t("writing_samples.fields.notes"), self.notes_edit)
        root.addWidget(metrics)

        buttons = QHBoxLayout()
        auto_btn = QPushButton(t("writing_samples.auto_title"))
        auto_btn.clicked.connect(self._auto_title)
        buttons.addWidget(auto_btn)
        buttons.addStretch()
        save = QPushButton(t("common.save"))
        cancel = QPushButton(t("common.cancel"))
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _spin5(self, *, default: int, minimum: int = 1) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, 5)
        spin.setValue(default)
        spin.setSuffix(t("writing_samples.scale_suffix"))
        return spin

    def _load_choices(self) -> None:
        self._fill_combo(self.pen_combo, t("writing_samples.none_pen"), [(p.id, _pen_label(p)) for p in self.session.query(Pen).order_by(Pen.brand, Pen.model).all()])
        self._fill_combo(self.ink_combo, t("writing_samples.none_ink"), [(i.id, _ink_label(i)) for i in self.session.query(Ink).order_by(Ink.brand, Ink.name).all()])
        self._fill_combo(self.paper_combo, t("writing_samples.none_paper"), [(p.id, _paper_label(p)) for p in self.session.query(Paper).order_by(Paper.brand, Paper.name).all()])
        self._fill_combo(self.nib_combo, t("writing_samples.none_nib"), [(n.id, _nib_label(n)) for n in self.session.query(Nib).order_by(Nib.manufacturer, Nib.size).all()])

    def _fill_combo(self, combo: QComboBox, empty_label: str, rows: list[tuple[int, str]]) -> None:
        combo.clear()
        combo.addItem(empty_label, None)
        for rid, label in rows:
            combo.addItem(label, rid)

    def _select_combo(self, combo: QComboBox, value: int | None) -> None:
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                return

    def _apply_defaults(self) -> None:
        """Vorauswahl für kontextnahe Aktionen, z.B. aus dem Füller-Detail."""
        defaults = self.defaults or {}
        mapping = (
            (self.type_combo, defaults.get("sample_type") or "regular"),
            (self.pen_combo, defaults.get("pen_id")),
            (self.ink_combo, defaults.get("ink_id")),
            (self.paper_combo, defaults.get("paper_id")),
            (self.nib_combo, defaults.get("nib_id")),
        )
        for combo, value in mapping:
            if value is not None:
                self._select_combo(combo, value)
        if defaults.get("sample_text"):
            self.sample_text.setPlainText(str(defaults.get("sample_text") or ""))
        if defaults.get("notes"):
            self.notes_edit.setPlainText(str(defaults.get("notes") or ""))

    def _load_sample(self, sample: WritingSample) -> None:
        self.title_edit.setText(sample.title or "")
        self._select_combo(self.type_combo, sample.sample_type or "regular")
        self._select_combo(self.pen_combo, sample.pen_id)
        self._select_combo(self.ink_combo, sample.ink_id)
        self._select_combo(self.paper_combo, sample.paper_id)
        self._select_combo(self.nib_combo, sample.nib_id)
        if sample.written_at:
            self.date_edit.setDate(QDate(sample.written_at.year, sample.written_at.month, sample.written_at.day))
        self.sample_text.setPlainText(sample.sample_text or "")
        self.image_edit.setText(sample.image_path or "")
        self.line_width.setValue(float(sample.line_width_mm or 0))
        self.dry_time.setValue(float(sample.dry_time_seconds or 0))
        self.feathering.setValue(int(sample.feathering_level or 1))
        self.bleedthrough.setValue(int(sample.bleedthrough_level or 1))
        self.shading.setValue(int(sample.shading_level or 3))
        self.sheen.setValue(int(sample.sheen_level or 0))
        self.flow.setValue(int(sample.flow_level or 3))
        self.feedback.setValue(int(sample.feedback_level or 3))
        self.rating.setValue(int(sample.overall_rating or 3))
        self.tags_edit.setText(sample.tags or "")
        self.notes_edit.setPlainText(sample.notes or "")

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("writing_samples.choose_image"),
            "",
            t("writing_samples.image_filter"),
        )
        if path:
            self.image_edit.setText(path)

    def _combo_obj(self, combo: QComboBox, cls):
        obj_id = combo.currentData()
        return self.session.get(cls, obj_id) if obj_id else None

    def _auto_title_if_empty(self) -> None:
        if not self.title_edit.text().strip():
            self._auto_title()

    def _auto_title(self) -> None:
        title = suggested_sample_title(
            self._combo_obj(self.pen_combo, Pen),
            self._combo_obj(self.ink_combo, Ink),
            self._combo_obj(self.paper_combo, Paper),
        )
        self.title_edit.setText(title)

    def get_data(self) -> dict:
        qdate = self.date_edit.date()
        written_at = datetime.combine(datetime(qdate.year(), qdate.month(), qdate.day()).date(), time.min)
        return {
            "title": self.title_edit.text().strip() or t("writing_samples.untitled"),
            "sample_type": self.type_combo.currentData() or "regular",
            "written_at": written_at,
            "pen_id": self.pen_combo.currentData(),
            "ink_id": self.ink_combo.currentData(),
            "paper_id": self.paper_combo.currentData(),
            "nib_id": self.nib_combo.currentData(),
            "sample_text": self.sample_text.toPlainText().strip() or None,
            "image_path": self.image_edit.text().strip() or None,
            "line_width_mm": self.line_width.value() or None,
            "dry_time_seconds": self.dry_time.value() or None,
            "feathering_level": self.feathering.value(),
            "bleedthrough_level": self.bleedthrough.value(),
            "shading_level": self.shading.value(),
            "sheen_level": self.sheen.value(),
            "flow_level": self.flow.value(),
            "feedback_level": self.feedback.value(),
            "overall_rating": self.rating.value(),
            "tags": self.tags_edit.text().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }


class WritingSampleComparisonDialog(QDialog):
    """Grid-Vergleich für 2–4 Schreibproben."""

    def __init__(self, parent=None, *, comparison):
        super().__init__(parent)
        self.setWindowTitle(t("writing_samples.compare_title"))
        self.setMinimumSize(scale_px(900), scale_px(520))
        root = QVBoxLayout(self)

        hint = QLabel(t("writing_samples.compare_hint"))
        hint.setWordWrap(True)
        root.addWidget(hint)

        table = QTableWidget()
        metrics = [
            ("combo", t("writing_samples.compare_fields.combo")),
            ("score", t("writing_samples.compare_fields.score")),
            ("rating", t("writing_samples.compare_fields.rating")),
            ("dry", t("writing_samples.compare_fields.dry")),
            ("feathering", t("writing_samples.compare_fields.feathering")),
            ("bleedthrough", t("writing_samples.compare_fields.bleedthrough")),
            ("shading", t("writing_samples.compare_fields.shading")),
            ("sheen", t("writing_samples.compare_fields.sheen")),
            ("flow", t("writing_samples.compare_fields.flow")),
            ("feedback", t("writing_samples.compare_fields.feedback")),
            ("verdict", t("writing_samples.compare_fields.verdict")),
        ]
        rows = comparison.rows
        table.setRowCount(len(metrics))
        table.setColumnCount(max(1, len(rows)))
        table.setVerticalHeaderLabels([label for _, label in metrics])
        table.setHorizontalHeaderLabels([r.title for r in rows] or [t("writing_samples.compare_no_samples")])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for col, row in enumerate(rows):
            values = {
                "combo": f"{row.pen_label}\n{row.ink_label}\n{row.paper_label}",
                "score": str(row.quality_score),
                "rating": f"{row.overall_rating}/5",
                "dry": "—" if row.dry_time_seconds is None else f"{row.dry_time_seconds:.0f} s",
                "feathering": f"{row.feathering_level}/5",
                "bleedthrough": f"{row.bleedthrough_level}/5",
                "shading": f"{row.shading_level}/5",
                "sheen": f"{row.sheen_level}/5",
                "flow": f"{row.flow_level}/5",
                "feedback": f"{row.feedback_level}/5",
                "verdict": t(f"writing_samples.compare_verdicts.{row.verdict}"),
            }
            for r_idx, (key, _) in enumerate(metrics):
                item = QTableWidgetItem(values[key])
                if row.sample_id == comparison.winner_id:
                    item.setToolTip(t("writing_samples.compare_winner"))
                table.setItem(r_idx, col, item)
        root.addWidget(table, 1)

        if comparison.winner_id is not None:
            winner = next((r for r in rows if r.sample_id == comparison.winner_id), None)
            if winner:
                winner_label = QLabel(t("writing_samples.compare_winner_line", title=winner.title))
                winner_label.setWordWrap(True)
                root.addWidget(winner_label)
        if comparison.warnings:
            warnings = QLabel(t("writing_samples.compare_warning_line"))
            warnings.setWordWrap(True)
            root.addWidget(warnings)

        close = QPushButton(t("common.ok"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(close)
        root.addLayout(row)
