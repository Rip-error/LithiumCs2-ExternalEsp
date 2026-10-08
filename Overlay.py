import os
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

import sys
from pathlib import Path

import win32gui
import win32con
import win32api
import win32com.client
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QLabel, QColorDialog,
)

from Lithium.ESP import ESP
from Lithium.Offsets import Offsets
from Lithium.Config import Config


MENU_STYLE = """
QWidget#root          { background: #16161b; border: 1px solid #2a2a35; }
QWidget#child         { background: #1a1a20; border: 1px solid #26262e; border-radius: 4px; }
QLabel                { color: #c8c8d4; font-family: 'Segoe UI'; font-size: 11px; }
QLabel#section        { color: #6a6a7a; font-size: 9px; font-weight: 600;
                        letter-spacing: 1.5px; padding: 4px 0; }
QLabel#state_on       { color: #4ade80; font-weight: 600; }
QLabel#state_off      { color: #ef4444; font-weight: 600; }
QCheckBox             { color: #b8b8c4; font-size: 11px; padding: 2px 0; spacing: 8px; }
QCheckBox::indicator  { width: 14px; height: 14px; border: 1px solid #3a3a48;
                        background: #1c1c24; border-radius: 3px; }
QCheckBox::indicator:checked { background: #64a0ff; border-color: #64a0ff; }
QCheckBox::indicator:hover   { border-color: #5a5a70; }
QPushButton           { background: #1c1c24; color: #c8c8d4; border: 1px solid #2e2e3c;
                        padding: 5px 8px; font-size: 11px; border-radius: 3px; }
QPushButton:hover     { background: #24242e; border-color: #3a3a48; }
QPushButton#color     { text-align: left; padding-left: 8px; min-height: 20px; }
QPushButton#reset     { color: #ef4444; border-color: #3a2020; }
QPushButton#reset:hover { background: #241518; }
QPushButton#titlebar  { background: transparent; border: none; color: #ffffff;
                        font-size: 13px; font-weight: 600; text-align: left;
                        padding-left: 10px; letter-spacing: 1px; }
QPushButton#titlebar:hover { background: #22222a; }
"""

FEATURES = [
    ("draw_box",       "Box ESP"),
    ("draw_names",     "Name ESP"),
    ("draw_health",    "Health Bar"),
    ("draw_distance",  "Distance"),
    ("draw_skeleton",  "Skeleton ESP"),
    ("draw_head",      "Head Dot"),
    ("draw_lines",     "Snaplines"),
    ("draw_teammates", "Team ESP"),
    ("draw_bomb",      "Bomb Timer"),
]

BONE_IDS = {
    "head": 6, "neck": 5, "waist": 0,
    "l_shoulder": 13, "r_shoulder": 8,
    "l_arm": 14, "r_arm": 9,
    "l_hand": 16, "r_hand": 11,
    "l_knee": 26, "r_knee": 23,
    "l_foot": 27, "r_foot": 24,
}

SKELETON_LINES = [
    ("head", "neck"), ("neck", "waist"),
    ("neck", "l_shoulder"), ("l_shoulder", "l_arm"), ("l_arm", "l_hand"),
    ("neck", "r_shoulder"), ("r_shoulder", "r_arm"), ("r_arm", "r_hand"),
    ("waist", "l_knee"), ("l_knee", "l_foot"),
    ("waist", "r_knee"), ("r_knee", "r_foot"),
]


# ---------------------------------------------------------------- menu
class Menu(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowStaysOnTopHint
                            | QtCore.Qt.Tool)
        self.setFixedSize(700, 400)
        self.setObjectName("root")
        self.setStyleSheet(MENU_STYLE)
        self.checkboxes = {}
        self.color_buttons = {}
        self._drag_pos = None
        self._build()

    def _section(self, text):
        lbl = QLabel(text); lbl.setObjectName("section"); return lbl

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        title = QPushButton("  Lithium")
        title.setObjectName("titlebar")
        title.setFixedHeight(32)
        title.installEventFilter(self)
        self._title_btn = title
        outer.addWidget(title)

        body = QHBoxLayout()
        body.setContentsMargins(10, 8, 10, 10); body.setSpacing(8)
        outer.addLayout(body)

        c1 = QWidget(); c1.setObjectName("child")
        v1 = QVBoxLayout(c1); v1.setContentsMargins(10, 8, 10, 8); v1.setSpacing(2)
        v1.addWidget(self._section("VISUALS"))
        for key, label in FEATURES:
            cb = QCheckBox(label)
            cb.setChecked(bool(self.config[key]))
            cb.stateChanged.connect(lambda st, k=key: self._toggle(k, st))
            self.checkboxes[key] = cb
            v1.addWidget(cb)
        v1.addStretch()
        body.addWidget(c1, 1)

        c2 = QWidget(); c2.setObjectName("child")
        v2 = QVBoxLayout(c2); v2.setContentsMargins(10, 8, 10, 8); v2.setSpacing(6)
        v2.addWidget(self._section("COLORS"))
        v2.addWidget(QLabel("Terrorist"))
        self.color_buttons["color_t"] = self._color_button("color_t")
        v2.addWidget(self.color_buttons["color_t"])
        v2.addWidget(QLabel("Counter-Terrorist"))
        self.color_buttons["color_ct"] = self._color_button("color_ct")
        v2.addWidget(self.color_buttons["color_ct"])
        v2.addSpacing(6)
        v2.addWidget(self._section("STATUS"))
        self.state_label = QLabel("ESP: ON")
        self.state_label.setObjectName("state_on")
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        v2.addWidget(self.state_label)
        v2.addStretch()
        reset = QPushButton("RESET DEFAULTS")
        reset.setObjectName("reset")
        reset.clicked.connect(self._reset)
        v2.addWidget(reset)
        body.addWidget(c2, 1)

        c3 = QWidget(); c3.setObjectName("child")
        v3 = QVBoxLayout(c3); v3.setContentsMargins(10, 8, 10, 8); v3.setSpacing(4)
        v3.addWidget(self._section("KEYBINDS"))
        v3.addWidget(QLabel("INSERT   —   toggle menu"))
        v3.addWidget(QLabel("F1          —   toggle ESP"))
        v3.addSpacing(10)
        v3.addWidget(self._section("INFO"))
        v3.addWidget(QLabel("Lithium ESP"))
        v3.addStretch()
        body.addWidget(c3, 1)

    def _color_button(self, key):
        btn = QPushButton()
        btn.setObjectName("color")
        btn.setFixedHeight(22)
        c = self.config[key]
        btn.setStyleSheet(f"background-color: {c.name()}; border-radius: 3px;")
        btn.clicked.connect(lambda _, k=key, b=btn: self._pick_color(k, b))
        return btn

    def _toggle(self, key, state):
        self.config[key] = bool(state); self.config.save()

    def _pick_color(self, key, button):
        c = QColorDialog.getColor(initial=self.config[key], parent=self)
        if c.isValid():
            self.config[key] = c
            button.setStyleSheet(f"background-color: {c.name()}; border-radius: 3px;")
            self.config.save()

    def _reset(self):
        for k, cb in self.checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(self.config.default_config[k])
            cb.blockSignals(False)
            self.config[k] = self.config.default_config[k]
        for k, btn in self.color_buttons.items():
            default = self.config._dict_to_qcolor(self.config.default_config[k])
            self.config[k] = default
            btn.setStyleSheet(f"background-color: {default.name()}; border-radius: 3px;")
        self.config.save()

    def set_esp_state(self, on):
        self.state_label.setText("ESP: ON" if on else "ESP: OFF")
        self.state_label.setObjectName("state_on" if on else "state_off")
        self.setStyleSheet(MENU_STYLE)

    def eventFilter(self, obj, ev):
        if obj is self._title_btn:
            if ev.type() == QtCore.QEvent.MouseButtonPress:
                self._drag_pos = ev.globalPos() - self.frameGeometry().topLeft()
            elif ev.type() == QtCore.QEvent.MouseMove and self._drag_pos is not None:
                self.move(ev.globalPos() - self._drag_pos)
            elif ev.type() == QtCore.QEvent.MouseButtonRelease:
                self._drag_pos = None
        return super().eventFilter(obj, ev)


# ---------------------------------------------------------------- canvas
class ESPCanvas(QWidget):
    """Direct QPainter canvas. Cached fonts + pens, single view-matrix read."""

    _HUD_FONT = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        self.esp = None
        self.config = None
        self.window_size = (0, 0)

        self._view_matrix = None
        self._bone_array = {}
        self._bones = {}
        self._pens = {}
        self._fonts = {}

    def _pen(self, color, width=1):
        key = (color.rgb(), int(width))
        pen = self._pens.get(key)
        if pen is None:
            pen = QtGui.QPen(color, width)
            self._pens[key] = pen
        return pen

    def _font(self, size):
        f = self._fonts.get(size)
        if f is None:
            f = QtGui.QFont("Arial", size)
            self._fonts[size] = f
        return f

    def paintEvent(self, event):
        if not self.esp or not self.config or not self._view_matrix:
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        try:
            self._paint(p)
        finally:
            p.end()

    def _refresh(self):
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if not hwnd or win32gui.GetForegroundWindow() != hwnd:
            if self._view_matrix is not None:
                self._view_matrix = None
                self.update()
            return

        # reset per-frame caches
        self._bone_array.clear()
        self._bones.clear()

        try:
            self._view_matrix = [
                self.esp.pm.read_float(self.esp.client + Offsets.dwViewMatrix + i * 4)
                for i in range(16)
            ]
        except Exception:
            self._view_matrix = None
            return

        self.esp.update_entities()
        self.update()

    def _paint(self, p):
        if not self.esp.local_player:
            return

        cfg = self.config
        if cfg["draw_bomb"]:
            self._paint_bomb(p)

        local_team = self.esp.local_player.team
        local_pos = self.esp.local_player.pos

        for e in self.esp.entities:
            if not e.pos:
                continue
            if e.lifestate == 258:
                continue
            is_team = (e.team == local_team)
            if is_team and not cfg["draw_teammates"]:
                continue

            head = self._bone(e, 6)
            feet = self._bone(e, 24) or self._bone(e, 27) or self._bone(e, 0)
            if not head or not feet:
                continue
            hs = self._w2s(head)
            fs = self._w2s(feet)
            if not hs or not fs:
                continue

            col = cfg["color_t"] if e.team == 2 else cfg["color_ct"]

            if any(cfg[k] for k in ("draw_box", "draw_health", "draw_names", "draw_distance")):
                self._paint_box(p, hs, fs, e, col, local_pos)

            if cfg["draw_skeleton"] or cfg["draw_head"]:
                self._paint_skeleton(p, e, is_team)

            if cfg["draw_lines"]:
                self._paint_snapline(p, fs, col)

    def _paint_box(self, p, hs, fs, e, col, local_pos):
        cfg = self.config
        top = hs[1] - 8
        bottom = fs[1]
        height = bottom - top
        if height < 6:
            return
        width = height / 2.2
        x = hs[0] - width / 2
        y = top

        if cfg["draw_box"]:
            p.setPen(self._pen(col, 2))
            p.drawRect(QtCore.QRectF(x, y, width, height))

        if cfg["draw_health"]:
            hh = height * (e.health / 100)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(self._hp_color(e.health))
            p.drawRect(QtCore.QRectF(x - 10, y + height - hh, 3, hh))
            ah = height * (e.armor / 100)
            p.setBrush(QtGui.QColor(0, 150, 255, 180))
            p.drawRect(QtCore.QRectF(x - 6, y + height - ah, 3, ah))
            p.setBrush(QtCore.Qt.NoBrush)

        p.setFont(self._font(8))
        fm = p.fontMetrics()

        if cfg["draw_names"]:
            p.setPen(QtGui.QColor(255, 255, 255))
            tw = fm.horizontalAdvance(e.name)
            p.drawText(QtCore.QPointF(x + width / 2 - tw / 2, y - 3), e.name)

        if cfg["draw_distance"] and local_pos:
            p.setPen(QtGui.QColor(255, 255, 255))
            d = self._dist(local_pos, e.pos)
            tw = fm.horizontalAdvance(d)
            p.drawText(QtCore.QPointF(x + width / 2 - tw / 2, y + height + 11), d)

    def _paint_snapline(self, p, fs, col):
        cx = self.window_size[0] / 2
        cy = self.window_size[1] - 150
        p.setPen(self._pen(col, 1))
        p.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(fs[0], fs[1]))

    def _paint_skeleton(self, p, e, is_team):
        pts = {}
        for name, idx in BONE_IDS.items():
            b = self._bone(e, idx)
            if b is None:
                continue
            s = self._w2s(b)
            if s is None:
                continue
            pts[name] = s

        if self.config["draw_skeleton"]:
            p.setPen(self._pen(QtGui.QColor(255, 255, 255, 160), 1))
            for a, b in SKELETON_LINES:
                if a in pts and b in pts:
                    p.drawLine(QtCore.QPointF(*pts[a]), QtCore.QPointF(*pts[b]))

        if self.config["draw_head"] and "head" in pts:
            hx, hy = pts["head"]
            if is_team:
                p.setPen(self._pen(QtGui.QColor(0, 255, 0), 2))
                p.setBrush(QtGui.QColor(0, 255, 0, 80))
            else:
                p.setPen(self._pen(QtGui.QColor(255, 0, 0), 2))
                p.setBrush(QtGui.QColor(255, 0, 0, 80))
            p.drawEllipse(QtCore.QPointF(hx, hy), 5, 5)
            p.setBrush(QtCore.Qt.NoBrush)

    def _paint_bomb(self, p):
        try:
            info = self.esp.get_bomb_info()
            if not info or not info["planted"] or info["is_defused"] or info["has_exploded"]:
                return
            scr = self._w2s(info["position"])
            if not scr:
                return
            if info["time_remaining"] <= 0:
                return
            if info["being_defused"]:
                txt = f'BOMB {info["time_remaining"]:.1f}s | DEF {info["defuse_time_remaining"]:.1f}s'
            else:
                txt = f'BOMB {info["time_remaining"]:.1f}s'
            p.setPen(QtGui.QColor(255, 0, 0))
            p.setFont(self._font(10))
            p.drawText(QtCore.QPointF(*scr), txt)
        except Exception:
            pass

    def _hp_color(self, hp):
        if hp > 75:  return QtGui.QColor(0, 255, 0, 180)
        if hp > 50:  return QtGui.QColor(255, 255, 0, 180)
        if hp > 25:  return QtGui.QColor(255, 165, 0, 180)
        return QtGui.QColor(255, 0, 0, 180)

    def _bone(self, e, idx):
        key = (e.pawn, idx)
        if key in self._bones:
            return self._bones[key]

        arr = self._bone_array.get(e.pawn)
        if arr is None:
            try:
                s = self.esp.pm.read_ulonglong(e.pawn + Offsets.m_pGameSceneNode)
                arr = self.esp.pm.read_ulonglong(s + Offsets.m_pBoneArray)
            except Exception:
                arr = 0
            self._bone_array[e.pawn] = arr

        if not arr:
            self._bones[key] = None
            return None

        try:
            pos = (self.esp.pm.read_float(arr + idx * 32),
                   self.esp.pm.read_float(arr + idx * 32 + 4),
                   self.esp.pm.read_float(arr + idx * 32 + 8))
        except Exception:
            pos = None
        self._bones[key] = pos
        return pos

    def _w2s(self, pos):
        m = self._view_matrix
        if not m:
            return None
        x = m[0]*pos[0] + m[1]*pos[1] + m[2]*pos[2] + m[3]
        y = m[4]*pos[0] + m[5]*pos[1] + m[6]*pos[2] + m[7]
        w = m[12]*pos[0] + m[13]*pos[1] + m[14]*pos[2] + m[15]
        if w < 0.01:
            return None
        inv = 1.0 / w
        W, H = self.window_size
        return (W / 2 * (1 + x * inv), H / 2 * (1 - y * inv))

    def _dist(self, a, b):
        dx = b[0] - a[0]; dy = b[1] - a[1]; dz = b[2] - a[2]
        return f"{(dx*dx + dy*dy + dz*dz) ** 0.5:.0f}m"


class ESPOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.esp = ESP()
        if not self.esp.initialize():
            sys.exit("[Overlay] Failed to init ESP")

        self.window_size = self._get_game_window_size()
        if not self.window_size[0]:
            sys.exit("[Overlay] CS2 window not found")

        self.config = Config(Path(__file__).parent / "options.json")
        self.canvas = ESPCanvas(self)
        self.canvas.esp = self.esp
        self.canvas.config = self.config
        self.canvas.window_size = (self.window_size[0], self.window_size[1])

        self.menu = Menu(self.config, self)

        self.menu_visible = False
        self.esp_enabled = True
        self._insert_pressed = False
        self._toggle_pressed = False

        self._setup_overlay_window()
        self._setup_timers()

    def _setup_overlay_window(self):
        w, h, x, y = self.window_size

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowStaysOnTopHint
                            | QtCore.Qt.Tool)

        # position AFTER the native window exists
        self.show()
        win32gui.SetWindowPos(
            int(self.winId()), win32con.HWND_TOPMOST,
            x, y, w, h,
            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW,
        )

        self.canvas.setGeometry(0, 0, w, h)

        ex = win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE,
                               ex | win32con.WS_EX_LAYERED
                                  | win32con.WS_EX_TRANSPARENT
                                  | win32con.WS_EX_TOOLWINDOW)

    def _setup_timers(self):
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.timeout.connect(self._tick)
        self._update_timer.start(33)   # 30 Hz — plenty for ESP

        self._insert_timer = QtCore.QTimer(self)
        self._insert_timer.timeout.connect(self._check_insert)
        self._insert_timer.start(80)

        self._toggle_timer = QtCore.QTimer(self)
        self._toggle_timer.timeout.connect(self._check_toggle)
        self._toggle_timer.start(80)

    def _tick(self):
        if self.esp_enabled:
            self.canvas._refresh()
        else:
            if self.canvas._view_matrix is not None:
                self.canvas._view_matrix = None
                self.canvas.update()

    def _check_insert(self):
        d = bool(win32api.GetAsyncKeyState(win32con.VK_INSERT) & 0x8000)
        if d and not self._insert_pressed:
            if self._is_focused("Counter-Strike 2") or self._is_focused(hwnd=int(self.menu.winId())):
                self._toggle_menu()
        self._insert_pressed = d

    def _check_toggle(self):
        if not self._is_focused("Counter-Strike 2"):
            return
        name = self.config["toggle_keybind"]
        if not name:
            return
        seq = QtGui.QKeySequence(name)
        if seq.isEmpty():
            return
        vk = self._qt_key_to_vk(seq[0])
        if vk and win32api.GetAsyncKeyState(vk) & 0x8000:
            if not self._toggle_pressed:
                self._toggle_pressed = True
                self.esp_enabled = not self.esp_enabled
                self.menu.set_esp_state(self.esp_enabled)
        else:
            self._toggle_pressed = False

    def _qt_key_to_vk(self, qk):
        k = qk.key()
        if QtCore.Qt.Key_F1 <= k <= QtCore.Qt.Key_F24:
            return win32con.VK_F1 + (k - QtCore.Qt.Key_F1)
        if k == QtCore.Qt.Key_Insert:   return win32con.VK_INSERT
        if k == QtCore.Qt.Key_Delete:   return win32con.VK_DELETE
        if k == QtCore.Qt.Key_Home:     return win32con.VK_HOME
        if k == QtCore.Qt.Key_End:      return win32con.VK_END
        if k == QtCore.Qt.Key_PageUp:   return win32con.VK_PRIOR
        if k == QtCore.Qt.Key_PageDown: return win32con.VK_NEXT
        if QtCore.Qt.Key_A <= k <= QtCore.Qt.Key_Z: return ord(chr(k).upper())
        if QtCore.Qt.Key_0 <= k <= QtCore.Qt.Key_9: return ord(chr(k))
        return None

    def _toggle_menu(self):
        self.menu_visible = not self.menu_visible
        self.menu.setVisible(self.menu_visible)
        ex = win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE)
        if self.menu_visible:
            self.menu.move(40, 40)
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE,
                                   ex & ~win32con.WS_EX_TRANSPARENT)
            win32com.client.Dispatch("WScript.Shell").SendKeys('%')
            win32gui.SetForegroundWindow(int(self.menu.winId()))
        else:
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE,
                                   ex | win32con.WS_EX_TRANSPARENT)
            h = win32gui.FindWindow(None, "Counter-Strike 2")
            if h:
                win32gui.SetForegroundWindow(h)

    def _get_game_window_size(self):
        h = win32gui.FindWindow(None, "Counter-Strike 2")
        if not h:
            return (None, None)
        l, t, r, b = win32gui.GetClientRect(h)
        sx, sy = win32gui.ClientToScreen(h, (l, t))
        return (r - l, b - t, sx, sy)

    def _is_focused(self, title=None, hwnd=None):
        if title:
            hwnd = win32gui.FindWindow(None, title)
        elif hwnd is None:
            return False
        return hwnd and win32gui.GetForegroundWindow() == hwnd