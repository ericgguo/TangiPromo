"""Main application window — three-panel layout."""
from __future__ import annotations

import os
from functools import partial
from typing import Optional

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressDialog, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter,
    QStackedWidget, QStatusBar, QTextEdit, QVBoxLayout, QWidget,
)

from .backgrounds import ALL_BACKGROUNDS, BACKGROUND_MAP
from .backgrounds.custom import CustomCodeBackground
from .custom_bg_store import CustomBgStore
from .canvas import Canvas
from .exporter import Exporter, ExportWorker, RESOLUTIONS
from .iphone import MODELS
from .iphone_manifest import DEVICE_PNG
from .text_layer import TextLayer
from .watermark import make_watermark_from_path
from .i18n import (
    EN,
    RESOLUTION_I18N_KEY,
    ZH,
    bg_display_name,
    custom_code_is_builtin_sample,
    default_custom_code,
    iphone_model_label,
    set_locale,
    theme_display_name,
    tr,
)

# 与 CustomCodeBackground.name 一致，用作 _bg_instances 字典键
_CUSTOM_BG_NAME = CustomCodeBackground().name


# ── Helpers ────────────────────────────────────────────────────────────────

def _group(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    gb = QGroupBox(title)
    lay = QVBoxLayout(gb)
    lay.setContentsMargins(10, 14, 10, 10)
    lay.setSpacing(8)
    return gb, lay


def _color_btn(color: QColor) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(32, 24)
    btn.setStyleSheet(
        f"background:{color.name()};border-radius:5px;border:1px solid #48484a;"
    )
    return btn


def _slider(lo: int, hi: int, val: int, step: int = 1) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    s.setSingleStep(step)
    return s


def _labeled_slider(lo: int, hi: int, val: int, fmt: str = "{v}") -> tuple[QWidget, QSlider, QLabel]:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    sl = _slider(lo, hi, val)
    lbl = QLabel(fmt.format(v=val))
    lbl.setFixedWidth(46)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    hl.addWidget(sl)
    hl.addWidget(lbl)
    return row, sl, lbl


class SectionLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "color:#8e8e93;font-size:10px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.7px;"
            "padding:8px 0 4px 0;background:transparent;border:none;"
        )


# ── Scroll panel builder ────────────────────────────────────────────────────

def _scroll_panel() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setMinimumWidth(232)
    area.setMaximumWidth(312)

    inner = QWidget()
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(12, 14, 12, 14)
    lay.setSpacing(6)
    area.setWidget(inner)
    return area, inner, lay


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    _RATIO_I18N_KEYS = ["16_9", "9_16", "1_1", "4_3", "4_5", "21_9"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(1440, 900)

        self._canvas = Canvas()
        self._export_worker: Optional[ExportWorker] = None
        self._current_bg_name: Optional[str] = None

        self._bg_instances: dict[str, object] = {
            cls().name: cls() for cls in ALL_BACKGROUNDS
        }
        self._custom_store = CustomBgStore()
        self._settings = QSettings()

        self._build_ui()
        self._connect_signals()
        self._on_model_index_changed(max(0, self._model_combo.currentIndex()))

        last_raw = self._settings.value("custom_bg_last_id", "")
        last_id = str(last_raw).strip() if last_raw else ""
        self._refresh_custom_preset_combo(last_id if last_id else None)

        # Default background
        first_name = ALL_BACKGROUNDS[0]().name
        ix = self._bg_combo.findData(first_name)
        self._bg_combo.blockSignals(True)
        self._bg_combo.setCurrentIndex(max(0, ix))
        self._bg_combo.blockSignals(False)
        self._apply_background(first_name)
        self._canvas.text_layers.append(
            TextLayer(
                name=tr("textlayer.name", n=1),
                text=tr("default.app_name"),
                y=0.88,
            )
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._build_right_panel())

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 900, 280])

        self.setCentralWidget(splitter)

        # Status bar
        sb = QStatusBar()
        sb.setStyleSheet(
            "background:#141416;color:#636366;font-size:12px;"
            "border-top:1px solid rgba(255,255,255,0.06);"
        )
        self._status_lbl = QLabel(tr("status.ready"))
        sb.addWidget(self._status_lbl)
        self.setStatusBar(sb)

    # ── Left panel ──────────────────────────────────────────────────────

    def _build_left_panel(self) -> QScrollArea:
        area, _, lay = _scroll_panel()

        self._sec_lang = SectionLabel(tr("lang.label"))
        lay.addWidget(self._sec_lang)
        self._lang_combo = QComboBox()
        self._lang_combo.blockSignals(True)
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("中文", "zh")
        self._lang_combo.setCurrentIndex(0)
        self._lang_combo.blockSignals(False)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lay.addWidget(self._lang_combo)

        # ── Output ratio
        self._gb_ratio, vl = _group(tr("group.ratio"))
        self._ratio_combo = QComboBox()
        for i, rk in enumerate(self._RATIO_I18N_KEYS):
            self._ratio_combo.addItem(tr(f"ratio.{rk}"), i)
        vl.addWidget(self._ratio_combo)
        lay.addWidget(self._gb_ratio)

        # ── Background preset
        self._gb_bg, vl_bg = _group(tr("group.bg"))
        self._bg_combo = QComboBox()
        for cls in ALL_BACKGROUNDS:
            key = cls().name
            self._bg_combo.addItem(bg_display_name(key), key)
        vl_bg.addWidget(self._bg_combo)

        row_spd, self._spd_slider, self._spd_lbl = _labeled_slider(
            10, 300, 100, "{v}%"
        )
        self._sec_bg_speed = SectionLabel(tr("bg.speed"))
        vl_bg.addWidget(self._sec_bg_speed)
        vl_bg.addWidget(row_spd)

        btn_row = QWidget()
        bhl = QHBoxLayout(btn_row)
        bhl.setContentsMargins(0, 0, 0, 0)
        self._pause_btn = QPushButton(tr("btn.pause"))
        self._reset_btn = QPushButton(tr("btn.reset"))
        bhl.addWidget(self._pause_btn)
        bhl.addWidget(self._reset_btn)
        vl_bg.addWidget(btn_row)

        lay.addWidget(self._gb_bg)

        self._code_group, vl_code = _group(tr("group.code"))
        self._sec_code_presets = SectionLabel(tr("code.preset_section"))
        vl_code.addWidget(self._sec_code_presets)
        self._preset_combo = QComboBox()
        vl_code.addWidget(self._preset_combo)

        preset_actions = QWidget()
        pal = QHBoxLayout(preset_actions)
        pal.setContentsMargins(0, 0, 0, 0)
        pal.setSpacing(8)
        self._preset_name = QLineEdit()
        self._preset_name.setPlaceholderText(tr("code.preset_name_ph"))
        self._preset_save_btn = QPushButton(tr("code.save_preset"))
        self._preset_save_btn.setObjectName("primaryBtn")
        self._preset_save_btn.setMinimumWidth(72)
        self._preset_del_btn = QPushButton(tr("code.delete_preset"))
        self._preset_del_btn.setObjectName("ghostBtn")
        self._preset_del_btn.setMinimumWidth(72)
        self._preset_del_btn.setEnabled(False)
        pal.addWidget(self._preset_name, 1)
        pal.addWidget(self._preset_save_btn)
        pal.addWidget(self._preset_del_btn)
        vl_code.addWidget(preset_actions)

        self._code_edit = QTextEdit()
        self._code_edit.setPlaceholderText(tr("code.placeholder"))
        self._code_edit.setMinimumHeight(200)
        self._code_edit.setPlainText(default_custom_code())
        vl_code.addWidget(self._code_edit)

        self._code_err_lbl = QLabel()
        self._code_err_lbl.setStyleSheet(
            "color:#ff453a;font-size:11px;background:transparent;border:none;"
            "padding:4px;"
        )
        self._code_err_lbl.setWordWrap(True)
        self._code_err_lbl.hide()
        vl_code.addWidget(self._code_err_lbl)

        self._code_apply_btn = QPushButton(tr("code.apply"))
        self._code_apply_btn.setObjectName("primaryBtn")
        self._code_apply_btn.clicked.connect(self._apply_custom_code)
        self._code_apply_btn.setToolTip(tr("code.apply_tip"))
        vl_code.addWidget(self._code_apply_btn)

        self._code_group.hide()
        lay.addWidget(self._code_group)

        lay.addStretch()
        return area

    # ── Right panel ─────────────────────────────────────────────────────

    def _build_right_panel(self) -> QScrollArea:
        area, _, lay = _scroll_panel()

        self._gb_ph, vl_ph = _group(tr("group.phone"))

        self._model_combo = QComboBox()
        for m in MODELS:
            self._model_combo.addItem(iphone_model_label(m), m)
        self._sec_phone_model = SectionLabel(tr("sec.phone_model"))
        vl_ph.addWidget(self._sec_phone_model)
        vl_ph.addWidget(self._model_combo)

        self._theme_combo = QComboBox()
        self._sec_phone_theme = SectionLabel(tr("sec.phone_theme"))
        vl_ph.addWidget(self._sec_phone_theme)
        vl_ph.addWidget(self._theme_combo)

        ph_form = QFormLayout()
        ph_form.setContentsMargins(0, 0, 0, 0)
        ph_form.setSpacing(6)
        self._phone_scale_spin = QDoubleSpinBox()
        self._phone_scale_spin.setRange(20, 100)
        self._phone_scale_spin.setDecimals(1)
        self._phone_scale_spin.setSuffix(" %")
        self._phone_scale_spin.setValue(72)
        self._phone_scale_spin.setToolTip(tr("phone.tip.size"))
        self._lbl_phone_size = QLabel(tr("phone.size"))
        ph_form.addRow(self._lbl_phone_size, self._phone_scale_spin)

        self._phone_x_spin = QDoubleSpinBox()
        self._phone_x_spin.setRange(0, 100)
        self._phone_x_spin.setDecimals(2)
        self._phone_x_spin.setSuffix(" %")
        self._phone_x_spin.setValue(50)
        self._phone_x_spin.setToolTip(tr("phone.tip.x"))
        self._lbl_phone_x = QLabel(tr("phone.x"))
        ph_form.addRow(self._lbl_phone_x, self._phone_x_spin)

        self._phone_y_spin = QDoubleSpinBox()
        self._phone_y_spin.setRange(0, 100)
        self._phone_y_spin.setDecimals(2)
        self._phone_y_spin.setSuffix(" %")
        self._phone_y_spin.setValue(50)
        self._phone_y_spin.setToolTip(tr("phone.tip.y"))
        self._lbl_phone_y = QLabel(tr("phone.y"))
        ph_form.addRow(self._lbl_phone_y, self._phone_y_spin)

        ph_wrap = QWidget()
        ph_wrap.setLayout(ph_form)
        self._sec_phone_pos = SectionLabel(tr("sec.phone_pos"))
        vl_ph.addWidget(self._sec_phone_pos)
        vl_ph.addWidget(ph_wrap)

        self._center_phone_btn = QPushButton(tr("phone.center"))
        self._center_phone_btn.setToolTip(tr("phone.center_tip"))
        vl_ph.addWidget(self._center_phone_btn)

        self._show_phone_cb = QCheckBox(tr("phone.show"))
        self._show_phone_cb.setChecked(True)
        vl_ph.addWidget(self._show_phone_cb)

        lay.addWidget(self._gb_ph)

        self._gb_sc, vl_sc = _group(tr("group.screen"))

        self._load_img_btn = QPushButton(tr("screen.load_img"))
        self._load_vid_btn = QPushButton(tr("screen.load_vid"))
        self._clear_content_btn = QPushButton(tr("screen.clear"))
        self._content_lbl = QLabel(tr("screen.none"))
        self._content_lbl.setStyleSheet(
            "color:#636366;font-size:11px;background:transparent;border:none;"
        )
        self._content_lbl.setWordWrap(True)

        vl_sc.addWidget(self._load_img_btn)
        vl_sc.addWidget(self._load_vid_btn)
        vl_sc.addWidget(self._clear_content_btn)
        vl_sc.addWidget(self._content_lbl)
        lay.addWidget(self._gb_sc)

        self._gb_wm, vl_wm = _group(tr("group.wm"))
        self._wm_hint = QLabel(tr("wm.hint"))
        self._wm_hint.setWordWrap(True)
        self._wm_hint.setStyleSheet("color:#8e8e93;font-size:11px;")
        vl_wm.addWidget(self._wm_hint)
        self._wm_rows_host = QWidget()
        self._wm_rows_layout = QVBoxLayout(self._wm_rows_host)
        self._wm_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._wm_rows_layout.setSpacing(6)
        vl_wm.addWidget(self._wm_rows_host)
        self._wm_checks: list[QCheckBox] = []
        self._wm_color_btns: list[QPushButton] = []
        self._wm_x: list[QDoubleSpinBox] = []
        self._wm_y: list[QDoubleSpinBox] = []
        self._wm_w: list[QDoubleSpinBox] = []
        self._add_wm_btn = QPushButton(tr("wm.add"))
        self._add_wm_btn.setToolTip(tr("wm.add_tip"))
        self._add_wm_btn.clicked.connect(self._add_watermark_from_file)
        vl_wm.addWidget(self._add_wm_btn)
        self._rebuild_watermark_panel()
        lay.addWidget(self._gb_wm)

        self._gb_txt, vl_txt = _group(tr("group.text"))

        self._layer_list = QListWidget()
        self._layer_list.setMaximumHeight(130)
        vl_txt.addWidget(self._layer_list)

        btn_row2 = QWidget()
        bhl2 = QHBoxLayout(btn_row2)
        bhl2.setContentsMargins(0, 0, 0, 0)
        self._add_text_layer_btn = QPushButton(tr("text.add"))
        self._add_text_layer_btn.setObjectName("primaryBtn")
        self._del_layer_btn = QPushButton(tr("text.del"))
        self._del_layer_btn.setObjectName("dangerBtn")
        bhl2.addWidget(self._add_text_layer_btn)
        bhl2.addWidget(self._del_layer_btn)
        vl_txt.addWidget(btn_row2)

        # Text edit fields
        self._txt_stack = QStackedWidget()
        self._txt_empty = QLabel(tr("text.pick_layer"))
        self._txt_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._txt_empty.setStyleSheet("color:#636366;background:transparent;border:none;")
        self._txt_stack.addWidget(self._txt_empty)   # index 0

        self._txt_editor = self._build_text_editor()
        self._txt_stack.addWidget(self._txt_editor)  # index 1

        vl_txt.addWidget(self._txt_stack)
        lay.addWidget(self._gb_txt)

        self._gb_exp, vl_exp = _group(tr("group.export"))

        self._exp_format = QComboBox()
        self._exp_format.addItem(tr("fmt.png"), 0)
        self._exp_format.addItem(tr("fmt.jpg"), 1)
        self._exp_format.addItem(tr("fmt.mp4"), 2)
        self._sec_exp_fmt = SectionLabel(tr("export.format"))
        vl_exp.addWidget(self._sec_exp_fmt)
        vl_exp.addWidget(self._exp_format)

        self._exp_res = QComboBox()
        for res_key in RESOLUTIONS.keys():
            i18n_k = RESOLUTION_I18N_KEY.get(res_key, "")
            label = tr(i18n_k) if i18n_k else res_key
            self._exp_res.addItem(label, res_key)
        self._sec_exp_res = SectionLabel(tr("export.res"))
        vl_exp.addWidget(self._sec_exp_res)
        vl_exp.addWidget(self._exp_res)

        self._vid_options = QWidget()
        vl_vid = QFormLayout(self._vid_options)
        vl_vid.setContentsMargins(0, 0, 0, 0)
        self._fps_spin = QDoubleSpinBox()
        self._fps_spin.setRange(12, 60)
        self._fps_spin.setValue(30)
        self._fps_spin.setSuffix(" fps")
        self._dur_spin = QDoubleSpinBox()
        self._dur_spin.setRange(1, 120)
        self._dur_spin.setValue(10)
        self._dur_spin.setSuffix(tr("export.suffix.sec"))
        self._lbl_vid_fps = QLabel(tr("export.fps"))
        self._lbl_vid_dur = QLabel(tr("export.dur"))
        vl_vid.addRow(self._lbl_vid_fps, self._fps_spin)
        vl_vid.addRow(self._lbl_vid_dur, self._dur_spin)
        self._full_import_cb = QCheckBox(tr("export.full_vid"))
        self._full_import_cb.setToolTip(tr("export.full_vid_tip"))
        vl_vid.addRow("", self._full_import_cb)
        self._vid_src_lbl = QLabel("")
        self._vid_src_lbl.setStyleSheet("color:#8e8e93;font-size:11px;")
        self._vid_src_lbl.setWordWrap(True)
        vl_vid.addRow("", self._vid_src_lbl)
        self._vid_options.hide()
        vl_exp.addWidget(self._vid_options)

        self._export_btn = QPushButton(tr("export.btn"))
        self._export_btn.setObjectName("primaryBtn")
        self._export_btn.setMinimumHeight(38)
        vl_exp.addWidget(self._export_btn)

        lay.addWidget(self._gb_exp)
        lay.addStretch()

        # Connect text layer signals
        self._add_text_layer_btn.clicked.connect(self._add_text_layer)
        self._del_layer_btn.clicked.connect(self._delete_text_layer)
        self._layer_list.currentRowChanged.connect(self._on_layer_row_changed)

        return area

    def _build_text_editor(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)
        fl.setContentsMargins(0, 4, 0, 0)
        fl.setSpacing(6)

        self._te_name = QLineEdit()
        self._te_text = QTextEdit()
        self._te_text.setMaximumHeight(70)
        self._te_font = QComboBox()
        self._te_font.addItems([
            "Helvetica Neue", "SF Pro Display",
            "PingFang SC", "Hiragino Sans GB", "Arial", "Georgia",
        ])
        self._te_size = QSpinBox()
        self._te_size.setRange(6, 300)
        self._te_size.setValue(36)
        self._te_size.setSuffix(" pt")

        self._te_bold = QCheckBox(tr("te.bold"))
        self._te_italic = QCheckBox(tr("te.italic"))
        self._te_shadow = QCheckBox(tr("te.shadow"))
        self._te_outline = QCheckBox(tr("te.outline"))
        self._te_shadow.setChecked(True)

        chk_row = QWidget()
        chl = QHBoxLayout(chk_row)
        chl.setContentsMargins(0, 0, 0, 0)
        chl.addWidget(self._te_bold)
        chl.addWidget(self._te_italic)
        chl.addWidget(self._te_shadow)
        chl.addWidget(self._te_outline)

        self._te_color = _color_btn(QColor(255, 255, 255))
        self._te_color_lbl = QLabel(tr("te.color.white"))
        clr_row = QWidget()
        clr_hl = QHBoxLayout(clr_row)
        clr_hl.setContentsMargins(0, 0, 0, 0)
        clr_hl.addWidget(self._te_color)
        clr_hl.addWidget(self._te_color_lbl)
        clr_hl.addStretch()

        self._te_align = QComboBox()
        self._te_align.addItem(tr("te.align.center"), 0)
        self._te_align.addItem(tr("te.align.left"), 1)
        self._te_align.addItem(tr("te.align.right"), 2)

        self._lbl_te_name = QLabel(tr("te.name"))
        self._lbl_te_text = QLabel(tr("te.text"))
        self._lbl_te_font = QLabel(tr("te.font"))
        self._lbl_te_size = QLabel(tr("te.size"))
        self._lbl_te_color = QLabel(tr("te.color"))
        self._lbl_te_align = QLabel(tr("te.align"))
        fl.addRow(self._lbl_te_name, self._te_name)
        fl.addRow(self._lbl_te_text, self._te_text)
        fl.addRow(self._lbl_te_font, self._te_font)
        fl.addRow(self._lbl_te_size, self._te_size)
        fl.addRow(self._lbl_te_color, clr_row)
        fl.addRow(self._lbl_te_align, self._te_align)
        fl.addRow("", chk_row)

        # Bind changes
        self._te_text.textChanged.connect(self._sync_text_layer)
        self._te_name.textChanged.connect(self._sync_text_layer)
        self._te_font.currentTextChanged.connect(self._sync_text_layer)
        self._te_size.valueChanged.connect(self._sync_text_layer)
        self._te_bold.toggled.connect(self._sync_text_layer)
        self._te_italic.toggled.connect(self._sync_text_layer)
        self._te_shadow.toggled.connect(self._sync_text_layer)
        self._te_outline.toggled.connect(self._sync_text_layer)
        self._te_align.currentIndexChanged.connect(self._sync_text_layer)
        self._te_color.clicked.connect(self._pick_text_color)

        return w

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._ratio_combo.currentIndexChanged.connect(self._on_ratio_changed)
        self._bg_combo.currentIndexChanged.connect(self._on_bg_combo_changed)
        self._spd_slider.valueChanged.connect(self._on_speed_changed)
        self._pause_btn.clicked.connect(self._toggle_pause)
        self._reset_btn.clicked.connect(self._canvas.reset_time)

        self._model_combo.currentIndexChanged.connect(self._on_model_index_changed)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_index_changed)
        self._phone_scale_spin.valueChanged.connect(self._on_phone_scale_spin)
        self._phone_x_spin.valueChanged.connect(self._on_phone_pos_spin)
        self._phone_y_spin.valueChanged.connect(self._on_phone_pos_spin)
        self._show_phone_cb.toggled.connect(
            lambda v: setattr(self._canvas, "show_iphone", v)
        )
        self._center_phone_btn.clicked.connect(self._on_center_phone_clicked)
        self._canvas.iphone_moved.connect(self._sync_phone_pos_spinboxes)
        self._canvas.watermark_moved.connect(self._sync_watermark_pos_from_canvas)

        self._load_img_btn.clicked.connect(self._load_image)
        self._load_vid_btn.clicked.connect(self._load_video)
        self._clear_content_btn.clicked.connect(self._clear_content)
        self._full_import_cb.toggled.connect(self._update_vid_src_hint)

        self._exp_format.currentIndexChanged.connect(self._on_format_changed)
        self._export_btn.clicked.connect(self._export)

        self._canvas.layer_selected.connect(self._on_canvas_layer_selected)

        # Error polling for custom code
        self._err_timer = QTimer(self)
        self._err_timer.timeout.connect(self._poll_code_error)
        self._err_timer.start(500)

        self._code_apply_timer = QTimer(self)
        self._code_apply_timer.setSingleShot(True)
        self._code_apply_timer.setInterval(400)
        self._code_apply_timer.timeout.connect(self._apply_custom_code)
        self._code_edit.textChanged.connect(self._on_custom_code_text_changed)

        self._preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        self._preset_save_btn.clicked.connect(self._save_custom_preset)
        self._preset_del_btn.clicked.connect(self._delete_custom_preset)

    def _on_bg_combo_changed(self, idx: int) -> None:
        if idx < 0:
            return
        key = self._bg_combo.itemData(idx)
        if key:
            self._apply_background(str(key))

    def _on_language_changed(self, idx: int) -> None:
        if idx < 0:
            return
        loc = self._lang_combo.itemData(idx)
        set_locale(loc if loc in ("zh", "en") else "en")
        self.apply_ui_language()

    def apply_ui_language(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self._status_lbl.setText(tr("status.ready"))
        self._sec_lang.setText(tr("lang.label"))
        self._gb_ratio.setTitle(tr("group.ratio"))
        for i, rk in enumerate(self._RATIO_I18N_KEYS):
            if i < self._ratio_combo.count():
                self._ratio_combo.setItemText(i, tr(f"ratio.{rk}"))
        self._gb_bg.setTitle(tr("group.bg"))
        for i in range(self._bg_combo.count()):
            key = self._bg_combo.itemData(i)
            if key:
                self._bg_combo.setItemText(i, bg_display_name(str(key)))
        self._sec_bg_speed.setText(tr("bg.speed"))
        self._reset_btn.setText(tr("btn.reset"))
        self._refresh_pause_btn()
        self._code_group.setTitle(tr("group.code"))
        self._code_edit.setPlaceholderText(tr("code.placeholder"))
        self._code_apply_btn.setText(tr("code.apply"))
        self._code_apply_btn.setToolTip(tr("code.apply_tip"))
        self._sec_code_presets.setText(tr("code.preset_section"))
        self._preset_name.setPlaceholderText(tr("code.preset_name_ph"))
        self._preset_save_btn.setText(tr("code.save_preset"))
        self._preset_del_btn.setText(tr("code.delete_preset"))
        if self._preset_combo.count() > 0 and self._preset_combo.itemData(0) is None:
            self._preset_combo.setItemText(0, tr("code.draft"))
        self._gb_ph.setTitle(tr("group.phone"))
        self._sec_phone_model.setText(tr("sec.phone_model"))
        self._sec_phone_theme.setText(tr("sec.phone_theme"))
        self._lbl_phone_size.setText(tr("phone.size"))
        self._lbl_phone_x.setText(tr("phone.x"))
        self._lbl_phone_y.setText(tr("phone.y"))
        self._phone_scale_spin.setToolTip(tr("phone.tip.size"))
        self._phone_x_spin.setToolTip(tr("phone.tip.x"))
        self._phone_y_spin.setToolTip(tr("phone.tip.y"))
        self._sec_phone_pos.setText(tr("sec.phone_pos"))
        self._center_phone_btn.setText(tr("phone.center"))
        self._center_phone_btn.setToolTip(tr("phone.center_tip"))
        self._show_phone_cb.setText(tr("phone.show"))
        self._gb_sc.setTitle(tr("group.screen"))
        self._load_img_btn.setText(tr("screen.load_img"))
        self._load_vid_btn.setText(tr("screen.load_vid"))
        self._clear_content_btn.setText(tr("screen.clear"))
        self._gb_wm.setTitle(tr("group.wm"))
        self._wm_hint.setText(tr("wm.hint"))
        self._add_wm_btn.setText(tr("wm.add"))
        self._add_wm_btn.setToolTip(tr("wm.add_tip"))
        self._gb_txt.setTitle(tr("group.text"))
        self._add_text_layer_btn.setText(tr("text.add"))
        self._del_layer_btn.setText(tr("text.del"))
        self._txt_empty.setText(tr("text.pick_layer"))
        self._lbl_te_name.setText(tr("te.name"))
        self._lbl_te_text.setText(tr("te.text"))
        self._lbl_te_font.setText(tr("te.font"))
        self._lbl_te_size.setText(tr("te.size"))
        self._lbl_te_color.setText(tr("te.color"))
        self._lbl_te_align.setText(tr("te.align"))
        self._te_bold.setText(tr("te.bold"))
        self._te_italic.setText(tr("te.italic"))
        self._te_shadow.setText(tr("te.shadow"))
        self._te_outline.setText(tr("te.outline"))
        self._te_align.setItemText(0, tr("te.align.center"))
        self._te_align.setItemText(1, tr("te.align.left"))
        self._te_align.setItemText(2, tr("te.align.right"))
        self._gb_exp.setTitle(tr("group.export"))
        self._sec_exp_fmt.setText(tr("export.format"))
        self._exp_format.setItemText(0, tr("fmt.png"))
        self._exp_format.setItemText(1, tr("fmt.jpg"))
        self._exp_format.setItemText(2, tr("fmt.mp4"))
        self._sec_exp_res.setText(tr("export.res"))
        for i in range(self._exp_res.count()):
            rk = self._exp_res.itemData(i)
            if rk:
                ik = RESOLUTION_I18N_KEY.get(str(rk), "")
                self._exp_res.setItemText(i, tr(ik) if ik else str(rk))
        self._lbl_vid_fps.setText(tr("export.fps"))
        self._lbl_vid_dur.setText(tr("export.dur"))
        self._dur_spin.setSuffix(tr("export.suffix.sec"))
        self._full_import_cb.setText(tr("export.full_vid"))
        self._full_import_cb.setToolTip(tr("export.full_vid_tip"))
        self._export_btn.setText(tr("export.btn"))
        self._update_vid_src_hint()
        self._refresh_phone_combo_language()
        self._maybe_refresh_builtin_code_sample()
        self._sync_builtin_text_layers_locale()
        self._rebuild_watermark_panel()
        self._refresh_layer_list()

    def _refresh_phone_combo_language(self) -> None:
        """机型 / 颜色下拉的显示文案随语言更新（内部仍用英文机型名与 theme_id）。"""
        cur_m = self._model_combo.currentData()
        if cur_m is None and MODELS:
            cur_m = MODELS[0]
        cur_m = str(cur_m) if cur_m else ""
        cur_t = self._canvas.iphone_theme

        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for m in MODELS:
            self._model_combo.addItem(iphone_model_label(m), m)
        ix = self._model_combo.findData(cur_m)
        if ix < 0:
            ix = 0
        self._model_combo.setCurrentIndex(ix)
        self._model_combo.blockSignals(False)

        model = str(self._model_combo.currentData() or (MODELS[0] if MODELS else ""))
        self._canvas.iphone_model = model
        self._repopulate_theme_combo(select_theme_id=cur_t)

    def _sync_builtin_text_layers_locale(self) -> None:
        """若图层名/正文仍是另一语言的默认占位，则换成当前语言。"""
        for i, layer in enumerate(self._canvas.text_layers):
            n = i + 1
            names = {ZH["textlayer.name"].format(n=n), EN["textlayer.name"].format(n=n)}
            if layer.name in names:
                layer.name = tr("textlayer.name", n=n)
            if i == 0:
                bodies = {ZH["default.app_name"], EN["default.app_name"]}
                if layer.text in bodies:
                    layer.text = tr("default.app_name")
            else:
                bodies = {
                    ZH["textlayer.body"].format(n=n),
                    EN["textlayer.body"].format(n=n),
                }
                if layer.text in bodies:
                    layer.text = tr("textlayer.body", n=n)
        row = self._layer_list.currentRow()
        if 0 <= row < len(self._canvas.text_layers):
            self._load_layer_into_editor(self._canvas.text_layers[row])

    def _maybe_refresh_builtin_code_sample(self) -> None:
        """若编辑区仍是内置中英示例之一，则换成当前语言的示例注释。"""
        if not custom_code_is_builtin_sample(self._code_edit.toPlainText()):
            return
        self._code_edit.blockSignals(True)
        self._code_edit.setPlainText(default_custom_code())
        self._code_edit.blockSignals(False)
        bg = self._bg_instances.get(_CUSTOM_BG_NAME)
        if isinstance(bg, CustomCodeBackground):
            bg.code = default_custom_code()
            bg._last_code = None
        self._canvas.update()

    def _repopulate_theme_combo(self, select_theme_id: Optional[str] = None) -> None:
        model = self._model_combo.currentData()
        model = str(model) if model else (MODELS[0] if MODELS else "")
        order = list(DEVICE_PNG.get(model, {}).keys())
        self._theme_combo.blockSignals(True)
        self._theme_combo.clear()
        sel = 0
        for i, tid in enumerate(order):
            self._theme_combo.addItem(theme_display_name(tid), tid)
            if select_theme_id is not None and tid == select_theme_id:
                sel = i
        if order:
            self._theme_combo.setCurrentIndex(sel)
            tid = self._theme_combo.itemData(sel)
            if tid:
                self._canvas.iphone_theme = str(tid)
        self._theme_combo.blockSignals(False)

    def _refresh_pause_btn(self) -> None:
        p = self._canvas._paused
        self._pause_btn.setText(tr("btn.resume") if p else tr("btn.pause"))

    def _on_model_index_changed(self, idx: int) -> None:
        if idx < 0:
            return
        model = self._model_combo.itemData(idx)
        if model is None:
            return
        model = str(model)
        self._canvas.iphone_model = model
        self._repopulate_theme_combo(select_theme_id=None)
        self._canvas.update()

    def _on_theme_index_changed(self, idx: int) -> None:
        if idx < 0:
            return
        tid = self._theme_combo.itemData(idx)
        if tid:
            self._canvas.iphone_theme = str(tid)
            self._canvas.update()

    def _on_phone_scale_spin(self, val: float) -> None:
        self._canvas.iphone_scale = val / 100.0
        self._canvas.update()

    def _on_phone_pos_spin(self) -> None:
        x = self._phone_x_spin.value() / 100.0
        y = self._phone_y_spin.value() / 100.0
        self._canvas.iphone_pos = (x, y)
        self._canvas.update()

    def _on_center_phone_clicked(self) -> None:
        self._canvas.center_iphone()

    def _sync_phone_pos_spinboxes(self, x: float, y: float) -> None:
        self._phone_x_spin.blockSignals(True)
        self._phone_y_spin.blockSignals(True)
        self._phone_x_spin.setValue(round(x * 100.0, 2))
        self._phone_y_spin.setValue(round(y * 100.0, 2))
        self._phone_x_spin.blockSignals(False)
        self._phone_y_spin.blockSignals(False)

    def _rebuild_watermark_panel(self) -> None:
        while self._wm_rows_layout.count():
            it = self._wm_rows_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        self._wm_checks.clear()
        self._wm_color_btns.clear()
        self._wm_x.clear()
        self._wm_y.clear()
        self._wm_w.clear()

        for i, st in enumerate(self._canvas.watermark_states):
            sub = QGroupBox(st.title)
            sub.setToolTip(st.image_path)
            sub.setStyleSheet(
                "QGroupBox { font-size: 12px; color: #a1a1a6; padding-top: 8px; }"
            )
            sf = QFormLayout(sub)
            sf.setContentsMargins(6, 10, 6, 6)
            cb = QCheckBox(tr("wm.show"))
            cb.setChecked(st.enabled)
            cbtn = QPushButton()
            cbtn.setFixedSize(44, 26)
            cbtn.setStyleSheet(
                f"background:{st.color.name(QColor.NameFormat.HexArgb)};"
                "border-radius:6px;border:1px solid #48484a;"
            )
            sx = QDoubleSpinBox()
            sx.setRange(0, 100)
            sx.setDecimals(2)
            sx.setSuffix(" %")
            sx.setValue(st.center_x_pct)
            sx.setToolTip(tr("wm.tip.cx"))
            sy = QDoubleSpinBox()
            sy.setRange(0, 100)
            sy.setDecimals(2)
            sy.setSuffix(" %")
            sy.setValue(st.center_y_pct)
            sy.setToolTip(tr("wm.tip.cy"))
            sw = QDoubleSpinBox()
            sw.setRange(0.5, 95)
            sw.setDecimals(2)
            sw.setSuffix(" %")
            sw.setValue(st.width_pct)
            sw.setToolTip(tr("wm.tip.w"))
            sf.addRow("", cb)
            clr_row = QWidget()
            cr = QHBoxLayout(clr_row)
            cr.setContentsMargins(0, 0, 0, 0)
            cr.addWidget(QLabel(tr("wm.color")))
            cr.addWidget(cbtn)
            cr.addStretch()
            sf.addRow(clr_row)
            sf.addRow(tr("wm.cx"), sx)
            sf.addRow(tr("wm.cy"), sy)
            sf.addRow(tr("wm.w"), sw)
            del_btn = QPushButton(tr("wm.remove"))
            del_btn.setObjectName("dangerBtn")
            sf.addRow("", del_btn)
            self._wm_rows_layout.addWidget(sub)
            self._wm_checks.append(cb)
            self._wm_color_btns.append(cbtn)
            self._wm_x.append(sx)
            self._wm_y.append(sy)
            self._wm_w.append(sw)
            idx = i
            cb.toggled.connect(lambda *_: self._apply_watermarks_from_ui())
            cbtn.clicked.connect(partial(self._pick_watermark_color, idx))
            sx.valueChanged.connect(lambda *_: self._apply_watermarks_from_ui())
            sy.valueChanged.connect(lambda *_: self._apply_watermarks_from_ui())
            sw.valueChanged.connect(lambda *_: self._apply_watermarks_from_ui())
            del_btn.clicked.connect(partial(self._remove_watermark_at, idx))

    def _add_watermark_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("wm.pick_title"),
            "",
            tr("wm.pick_filter"),
        )
        if not path or not os.path.isfile(path):
            return
        self._canvas.watermark_states.append(make_watermark_from_path(path))
        self._canvas.clear_watermark_pixmap_cache()
        self._rebuild_watermark_panel()
        self._canvas.update()

    def _remove_watermark_at(self, index: int) -> None:
        states = self._canvas.watermark_states
        if not (0 <= index < len(states)):
            return
        del states[index]
        self._canvas.clear_watermark_pixmap_cache()
        self._rebuild_watermark_panel()
        self._canvas.update()

    def _apply_watermarks_from_ui(self) -> None:
        n = len(self._canvas.watermark_states)
        if len(self._wm_checks) != n:
            return
        for i, st in enumerate(self._canvas.watermark_states):
            st.enabled = self._wm_checks[i].isChecked()
            st.center_x_pct = self._wm_x[i].value()
            st.center_y_pct = self._wm_y[i].value()
            st.width_pct = self._wm_w[i].value()
        self._canvas.clear_watermark_pixmap_cache()
        self._canvas.update()

    def _sync_watermark_pos_from_canvas(self, index: int) -> None:
        if index < 0 or index >= len(self._wm_x):
            return
        st = self._canvas.watermark_states[index]
        self._wm_x[index].blockSignals(True)
        self._wm_y[index].blockSignals(True)
        self._wm_x[index].setValue(round(st.center_x_pct, 2))
        self._wm_y[index].setValue(round(st.center_y_pct, 2))
        self._wm_x[index].blockSignals(False)
        self._wm_y[index].blockSignals(False)

    def _pick_watermark_color(self, index: int) -> None:
        if index < 0 or index >= len(self._canvas.watermark_states):
            return
        st = self._canvas.watermark_states[index]
        c = QColorDialog.getColor(
            st.color,
            self,
            tr("wm.color_dialog"),
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if not c.isValid():
            return
        st.color = c
        self._wm_color_btns[index].setStyleSheet(
            f"background:{c.name(QColor.NameFormat.HexArgb)};"
            "border-radius:6px;border:1px solid #48484a;"
        )
        self._apply_watermarks_from_ui()

    # ------------------------------------------------------------------
    # Ratio
    # ------------------------------------------------------------------

    _RATIO_MAP = [
        (16, 9), (9, 16), (1, 1), (4, 3), (4, 5), (21, 9)
    ]

    def _on_ratio_changed(self, idx: int) -> None:
        self._canvas.output_ratio = self._RATIO_MAP[idx]

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _apply_background(self, name: str) -> None:
        prev = self._current_bg_name
        if prev == _CUSTOM_BG_NAME and name != _CUSTOM_BG_NAME:
            self._flush_custom_code_to_bg()

        bg = self._bg_instances.get(name)
        if bg is None:
            return
        self._canvas.background = bg
        self._current_bg_name = name

        is_custom = isinstance(bg, CustomCodeBackground)
        self._code_group.setVisible(is_custom)
        if is_custom:
            self._sync_custom_code_panel_from_preset()

    def _sync_custom_code_panel_from_preset(self) -> None:
        """打开「自定义代码」背景时：按当前预设下拉框加载编辑器与实例。"""
        bg = self._bg_instances.get(_CUSTOM_BG_NAME)
        if not isinstance(bg, CustomCodeBackground):
            return
        idx = self._preset_combo.currentIndex()
        if idx < 0:
            return
        pid = self._preset_combo.itemData(idx)
        if pid is None:
            self._code_edit.blockSignals(True)
            self._code_edit.setPlainText(bg.code)
            self._code_edit.blockSignals(False)
            return
        pr = self._custom_store.by_id(str(pid))
        if not pr:
            self._code_edit.blockSignals(True)
            self._code_edit.setPlainText(bg.code)
            self._code_edit.blockSignals(False)
            return
        self._preset_name.setText(pr.name)
        self._code_edit.blockSignals(True)
        self._code_edit.setPlainText(pr.code)
        self._code_edit.blockSignals(False)
        bg.code = pr.code
        bg._last_code = None

    def _refresh_custom_preset_combo(self, select_id: Optional[str] = None) -> None:
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItem(tr("code.draft"), None)
        for pr in self._custom_store.presets:
            self._preset_combo.addItem(pr.name, pr.id)
        sel = 0
        if select_id:
            for i in range(self._preset_combo.count()):
                if self._preset_combo.itemData(i) == select_id:
                    sel = i
                    break
        self._preset_combo.setCurrentIndex(sel)
        self._preset_combo.blockSignals(False)
        self._on_preset_combo_changed(sel)

    def _on_preset_combo_changed(self, idx: int) -> None:
        if idx < 0:
            return
        pid = self._preset_combo.itemData(idx)
        self._preset_del_btn.setEnabled(pid is not None)
        vis = self._code_group.isVisible()
        if pid is None:
            self._preset_name.clear()
            self._settings.setValue("custom_bg_last_id", "")
            if vis:
                bg = self._bg_instances.get(_CUSTOM_BG_NAME)
                if isinstance(bg, CustomCodeBackground):
                    bg.code = self._code_edit.toPlainText()
                    bg._last_code = None
                self._canvas.update()
            return
        pr = self._custom_store.by_id(str(pid))
        if not pr:
            return
        self._preset_name.setText(pr.name)
        self._settings.setValue("custom_bg_last_id", pr.id)
        if vis:
            self._code_edit.blockSignals(True)
            self._code_edit.setPlainText(pr.code)
            self._code_edit.blockSignals(False)
            bg = self._bg_instances.get(_CUSTOM_BG_NAME)
            if isinstance(bg, CustomCodeBackground):
                bg.code = pr.code
                bg._last_code = None
            self._canvas.update()

    def _save_custom_preset(self) -> None:
        name = self._preset_name.text().strip()
        if not name:
            QMessageBox.information(self, tr("err.title"), tr("code.need_name"))
            return
        code = self._code_edit.toPlainText()
        pid = self._preset_combo.currentData()
        pid_str = str(pid) if pid else None
        pr = self._custom_store.upsert(name, code, pid_str)
        self._refresh_custom_preset_combo(select_id=pr.id)
        self._settings.setValue("custom_bg_last_id", pr.id)

    def _delete_custom_preset(self) -> None:
        pid = self._preset_combo.currentData()
        if not pid:
            return
        r = QMessageBox.question(
            self,
            tr("code.delete_title"),
            tr("code.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        self._custom_store.delete(str(pid))
        self._settings.setValue("custom_bg_last_id", "")
        self._refresh_custom_preset_combo(select_id=None)

    def _flush_custom_code_to_bg(self) -> None:
        bg = self._bg_instances.get(_CUSTOM_BG_NAME)
        if bg and isinstance(bg, CustomCodeBackground):
            bg.code = self._code_edit.toPlainText()
            bg._last_code = None

    def _on_custom_code_text_changed(self) -> None:
        if not self._code_group.isVisible():
            return
        self._code_apply_timer.start()

    def _apply_custom_code(self) -> None:
        bg = self._bg_instances.get(_CUSTOM_BG_NAME)
        if bg and isinstance(bg, CustomCodeBackground):
            bg.code = self._code_edit.toPlainText()
            bg._last_code = None  # force recompile
        self._canvas.update()

    def _poll_code_error(self) -> None:
        bg = self._bg_instances.get(_CUSTOM_BG_NAME)
        if bg and isinstance(bg, CustomCodeBackground) and bg.error:
            self._code_err_lbl.setText(bg.error)
            self._code_err_lbl.show()
        else:
            self._code_err_lbl.hide()

    def _on_speed_changed(self, val: int) -> None:
        self._spd_lbl.setText(f"{val}%")
        factor = val / 100.0
        for bg in self._bg_instances.values():
            if hasattr(bg, "speed"):
                bg.speed = factor

    def _toggle_pause(self) -> None:
        p = not self._canvas._paused
        self._canvas.pause(p)
        self._refresh_pause_btn()

    # ------------------------------------------------------------------
    # iPhone / scale
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Content loading
    # ------------------------------------------------------------------

    def _load_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg.pick_img"), "",
            tr("dlg.img_filter"),
        )
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, tr("err.title"), tr("err.load_img"))
            return
        self._canvas.clear_video()
        self._canvas.screen_pixmap = pix
        self._content_lbl.setText(os.path.basename(path))

    def _load_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg.pick_vid"), "",
            tr("dlg.vid_filter"),
        )
        if not path:
            return
        try:
            self._canvas.set_video(path)
            self._content_lbl.setText(os.path.basename(path))
            self._update_vid_src_hint()
        except Exception as e:
            QMessageBox.warning(self, tr("err.title"), str(e))

    def _clear_content(self) -> None:
        self._canvas.clear_video()
        self._canvas.screen_pixmap = None
        self._content_lbl.setText(tr("screen.none"))
        self._update_vid_src_hint()

    def _update_vid_src_hint(self) -> None:
        d = self._canvas.imported_video_duration_sec()
        if d is not None and d > 0:
            self._vid_src_lbl.setText(tr("export.vid_hint", d=d))
        else:
            self._vid_src_lbl.setText("")

    # ------------------------------------------------------------------
    # Text layers
    # ------------------------------------------------------------------

    def _refresh_layer_list(self) -> None:
        self._layer_list.blockSignals(True)
        self._layer_list.clear()
        for layer in self._canvas.text_layers:
            self._layer_list.addItem(layer.name)
        self._layer_list.blockSignals(False)

    def _add_text_layer(self) -> None:
        n = len(self._canvas.text_layers) + 1
        layer = TextLayer(
            name=tr("textlayer.name", n=n),
            text=tr("textlayer.body", n=n),
            y=max(0.1, 0.85 - (n - 1) * 0.08),
        )
        self._canvas.text_layers.append(layer)
        self._refresh_layer_list()
        self._layer_list.setCurrentRow(len(self._canvas.text_layers) - 1)

    def _delete_text_layer(self) -> None:
        row = self._layer_list.currentRow()
        if row < 0 or row >= len(self._canvas.text_layers):
            return
        self._canvas.text_layers.pop(row)
        self._canvas.selected_layer = -1
        self._refresh_layer_list()
        self._txt_stack.setCurrentIndex(0)

    def _on_layer_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._canvas.text_layers):
            self._txt_stack.setCurrentIndex(0)
            return
        self._canvas.selected_layer = row
        self._load_layer_into_editor(self._canvas.text_layers[row])
        self._txt_stack.setCurrentIndex(1)

    def _on_canvas_layer_selected(self, idx: int) -> None:
        if idx < 0:
            self._txt_stack.setCurrentIndex(0)
            self._layer_list.clearSelection()
            return
        self._layer_list.blockSignals(True)
        self._layer_list.setCurrentRow(idx)
        self._layer_list.blockSignals(False)
        self._load_layer_into_editor(self._canvas.text_layers[idx])
        self._txt_stack.setCurrentIndex(1)
        self._refresh_layer_list()

    def _load_layer_into_editor(self, layer: TextLayer) -> None:
        self._block_editor(True)
        self._te_name.setText(layer.name)
        self._te_text.setPlainText(layer.text)
        idx = self._te_font.findText(layer.font_family)
        if idx >= 0:
            self._te_font.setCurrentIndex(idx)
        self._te_size.setValue(layer.font_size_pt)
        self._te_bold.setChecked(layer.bold)
        self._te_italic.setChecked(layer.italic)
        self._te_shadow.setChecked(layer.shadow)
        self._te_outline.setChecked(layer.outline)
        ALIGN_MAP = {
            Qt.AlignmentFlag.AlignHCenter: 0,
            Qt.AlignmentFlag.AlignLeft: 1,
            Qt.AlignmentFlag.AlignRight: 2,
        }
        self._te_align.setCurrentIndex(ALIGN_MAP.get(layer.align, 0))
        self._te_color.setStyleSheet(
            f"background:{layer.color.name()};border-radius:5px;border:1px solid #48484a;"
        )
        self._block_editor(False)

    def _block_editor(self, block: bool) -> None:
        for w in [
            self._te_name, self._te_text, self._te_font,
            self._te_size, self._te_bold, self._te_italic,
            self._te_shadow, self._te_outline, self._te_align,
        ]:
            w.blockSignals(block)

    def _sync_text_layer(self, *_) -> None:
        row = self._layer_list.currentRow()
        if row < 0 or row >= len(self._canvas.text_layers):
            return
        layer = self._canvas.text_layers[row]
        layer.name = self._te_name.text() or tr("textlayer.unnamed", n=row + 1)
        layer.text = self._te_text.toPlainText()
        layer.font_family = self._te_font.currentText()
        layer.font_size_pt = self._te_size.value()
        layer.bold = self._te_bold.isChecked()
        layer.italic = self._te_italic.isChecked()
        layer.shadow = self._te_shadow.isChecked()
        layer.outline = self._te_outline.isChecked()
        ALIGN_LIST = [
            Qt.AlignmentFlag.AlignHCenter,
            Qt.AlignmentFlag.AlignLeft,
            Qt.AlignmentFlag.AlignRight,
        ]
        layer.align = ALIGN_LIST[self._te_align.currentIndex()]
        # Update list item name
        if self._layer_list.currentItem():
            self._layer_list.currentItem().setText(layer.name)

    def _pick_text_color(self) -> None:
        row = self._layer_list.currentRow()
        if row < 0 or row >= len(self._canvas.text_layers):
            return
        layer = self._canvas.text_layers[row]
        color = QColorDialog.getColor(
            layer.color, self, tr("te.color.pick"),
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            layer.color = color
            self._te_color.setStyleSheet(
                f"background:{color.name()};border-radius:5px;border:1px solid #48484a;"
            )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_format_changed(self, idx: int) -> None:
        self._vid_options.setVisible(idx == 2)
        if idx == 2:
            self._update_vid_src_hint()

    def _export(self) -> None:
        fmt_idx = self._exp_format.currentIndex()
        res_key = self._exp_res.currentData()
        if res_key is None:
            res_key = self._exp_res.currentText()

        if res_key == "自定义…":
            # Simple fallback: ask user
            w, h = 1920, 1080
        else:
            w, h = RESOLUTIONS.get(res_key, (1920, 1080))

        # Adjust W/H to match selected output ratio
        rw, rh = self._canvas.output_ratio
        # Keep height, recompute width
        h_new = h
        w_new = int(h_new * rw / rh)
        w, h = w_new, h_new

        if fmt_idx == 0:
            path, _ = QFileDialog.getSaveFileName(
                self, tr("dlg.save_png"), "promo.png", tr("dlg.filter_png")
            )
            if path:
                Exporter.export_image(self._canvas, path, w, h)
                self._status_lbl.setText(tr("status.exported", path=path))

        elif fmt_idx == 1:
            path, _ = QFileDialog.getSaveFileName(
                self, tr("dlg.save_jpg"), "promo.jpg", tr("dlg.filter_jpg")
            )
            if path:
                Exporter.export_image(self._canvas, path, w, h, quality=95)
                self._status_lbl.setText(tr("status.exported", path=path))

        elif fmt_idx == 2:
            path, _ = QFileDialog.getSaveFileName(
                self, tr("dlg.save_mp4"), "promo.mp4", tr("dlg.filter_mp4")
            )
            if not path:
                return

            fps = self._fps_spin.value()
            dur = self._dur_spin.value()

            prog = QProgressDialog(
                tr("export.progress"),
                tr("export.progress_cancel"),
                0,
                100,
                self,
            )
            prog.setWindowTitle(tr("export.title"))
            prog.setWindowModality(Qt.WindowModality.WindowModal)
            prog.show()

            def on_progress(v: int) -> None:
                prog.setValue(v)

            def on_done(p: str) -> None:
                prog.close()
                self._status_lbl.setText(tr("status.exported_vid", path=p))
                QMessageBox.information(
                    self, tr("export.done_title"), tr("export.done_msg", p=p)
                )

            def on_err(msg: str) -> None:
                prog.close()
                QMessageBox.critical(self, tr("export.fail_title"), msg)

            prog.canceled.connect(lambda: self._export_worker and self._export_worker.terminate())

            self._export_worker = Exporter.start_video_export(
                self._canvas,
                path,
                w,
                h,
                fps,
                dur,
                ensure_full_import_video=self._full_import_cb.isChecked(),
                on_progress=on_progress,
                on_finished=on_done,
                on_error=on_err,
            )
