"""
Lineares Einspurmodell – Live-Simulation
==========================================
Fahrendes Auto in Echtzeit mit vollständiger Visualisierung aller
Fahrdynamikgrößen aus der GAV-Vorlesung (TUM).

Bewegungsgleichungen (Folie 04-66):
    ẋ     = v · cos(θ + β)
    ẏ     = v · sin(θ + β)
    β̇     = -(CV+CH)/(m·v) · β  +  [(CH·lH - CV·lV)/(m·v²) - 1] · θ̇  +  CV/(m·v) · δ
    θ̈     = (CH·lH - CV·lV)/Jz · β  -  (CH·lH² + CV·lV²)/(Jz·v) · θ̇  +  CV·lV/Jz · δ

Schräglaufwinkel (Folie 04-63):
    αV = δ - β - (lV/v)·θ̇
    αH =   - β + (lH/v)·θ̇

Seitenkräfte (linear):
    FYV = CV · αV
    FYH = CH · αH

Querbeschleunigung:
    ay = v · (θ̇ + β̇)  ≈  v · θ̇  (stationär)

Benötigt: pip install PyQt6 matplotlib numpy
"""

import sys
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QFrame, QTabWidget,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

# ── Farben ────────────────────────────────────────────────────────────────────
# Zeile 44–54: Farben ersetzen
TUM_BLUE   = "#0065BD"
TUM_ORANGE = "#E37222"
TUM_GREEN  = "#3A7D44"
TUM_RED    = "#C0392B"
PURPLE     = "#7B2D8B"
BG_DARK    = "#F0F2F5"    
BG_PANEL   = "#FFFFFF"    
BG_WIDGET  = "#E8ECF0"    
TEXT_LIGHT = "#1A1A1A"   
TEXT_DIM   = "#6B7280"

PLOT_BG   = "#FFFFFF"   
PLOT_GRID = "#E5E7EB"     


matplotlib.rcParams.update({
    "axes.facecolor":   "#FFFFFF",
    "figure.facecolor": "#F0F2F5",
    "axes.edgecolor":   "#9CA3AF",
    "axes.labelcolor":  "#111827",
    "xtick.color":      "#374151",
    "ytick.color":      "#374151",
    "text.color":       "#111827",
    "grid.color":       "#D1D5DB",
    "grid.linestyle":   "--",
    "axes.grid":        True,
    "legend.facecolor": "#FFFFFF",
    "legend.edgecolor": "#CCCCCC",
    "legend.fontsize":  7,
})


# ── Zeitschritt ───────────────────────────────────────────────────────────────
DT = 0.04   # 25 Hz

# ─────────────────────────────────────────────────────────────────────────────
# HILFS-WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

def lbl(text, bold=False, size=9, color=TEXT_LIGHT):
    w = QLabel(text)
    f = QFont("Helvetica Neue", size)
    f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color}; background:transparent;")
    return w


SLIDER_CSS = f"""
    QSlider::groove:horizontal {{
        height:10px; background:#D1D5DB;
        border-radius:5px;
    }}
    QSlider::handle:horizontal {{
        width:22px; height:22px; margin:-6px 0;
        background:{TUM_BLUE};
        border-radius:11px;
    }}
    QSlider::sub-page:horizontal {{
        background:{TUM_BLUE};
        border-radius:5px;
    }}
    QSlider::add-page:horizontal {{
        background:#D1D5DB;
        border-radius:5px;
    }}
"""

GB_CSS = f"""
    QGroupBox {{
        color:{TEXT_LIGHT}; font-weight:bold; font-size:11pt;
        border:1px solid {BG_WIDGET}; border-radius:6px;
        margin-top:10px; padding:6px;
    }}
    QGroupBox::title {{ subcontrol-origin:margin; left:8px; }}
"""

BTN_CSS = lambda c: f"""
    QPushButton {{
        background:{c}; color:#fff; border:none;
        border-radius:6px; padding:9px; font-size:11pt; font-weight:bold;
    }}
    QPushButton:hover   {{ background:{c}CC; }}
    QPushButton:pressed {{ background:{c}88; }}
"""


def make_slider(lo, hi, default, scale=10):
    s = QSlider(Qt.Orientation.Horizontal)
    s.setMinimum(int(lo * scale))
    s.setMaximum(int(hi * scale))
    s.setValue(int(default * scale))
    s.setStyleSheet(SLIDER_CSS)
    return s


def add_slider_row(layout, title, unit, lo, hi, default,
                   scale=10, color=TEXT_LIGHT, decimals=1):
    """Fügt Titel + Slider + Wertlabel ein. Gibt (slider, val_label) zurück."""
    layout.addWidget(lbl(title, bold=True, size=10, color=color))
    row = QHBoxLayout()
    sl = make_slider(lo, hi, default, scale)
    row.addWidget(sl, stretch=1)
    vl = lbl(f"{default:.{decimals}f} {unit}", size=10,
              bold=True, color=color)
    vl.setFixedWidth(110)
    row.addWidget(vl)
    layout.addLayout(row)
    return sl, vl


# ─────────────────────────────────────────────────────────────────────────────
# FAHRZEUG-ZEICHNER
# ─────────────────────────────────────────────────────────────────────────────

def rot2(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s], [s, c]])


def draw_moment_arc(ax, cx, cy, moment, theta, color, label):
    """Zeichnet einen Kreisbogen-Pfeil für ein Moment um (cx, cy)."""
    if abs(moment) <= 200:
        return
    radius = 1.5
    if moment > 0:
        theta1, theta2 = 0, 90
    else:
        theta1, theta2 = 90, 180
    arc = mpatches.Arc((cx, cy), 2*radius, 2*radius,
                        angle=np.rad2deg(theta),
                        theta1=theta1, theta2=theta2,
                        color=color, lw=1.8, zorder=14)
    ax.add_patch(arc)
    # Pfeilkopf am Ende des Bogens
    if moment > 0:
        tip_angle = theta + np.deg2rad(theta2)
    else:
        tip_angle = theta + np.deg2rad(theta2)
    tip_x = cx + radius * np.cos(tip_angle)
    tip_y = cy + radius * np.sin(tip_angle)
    dx = -np.sin(tip_angle) * 0.001 * (1 if moment > 0 else -1)
    dy =  np.cos(tip_angle) * 0.001 * (1 if moment > 0 else -1)
    ax.annotate("", xy=(tip_x + dx, tip_y + dy),
                xytext=(tip_x, tip_y),
                arrowprops=dict(arrowstyle="->", color=color,
                                lw=1.5, mutation_scale=10), zorder=15)
    mid_angle = theta + np.deg2rad((theta1 + theta2) / 2)
    lx = cx + (radius + 0.6) * np.cos(mid_angle)
    ly = cy + (radius + 0.6) * np.sin(mid_angle)
    ax.text(lx, ly, f"{label}\n{moment:.0f}Nm",
            fontsize=7, color=color, ha="center", va="center", zorder=15)


def draw_vehicle(ax, x, y, theta, beta, delta, alpha_f, alpha_r,
                 FYV, FYH, lf, lr, v=1.0, dtheta=0.0):
    """
    Zeichnet Fahrzeug-Silhouette mit allen fahrdynamischen Vektoren:
      - Heading θ (grün)
      - Schwimmwinkel β  → absolute Fahrtrichtung v_abs (orange)
      - Lenkwinkel δ     → Vorderachspfeil (hellblau)
      - Schräglaufwinkel αV, αH (rote Bögen an den Achsen)
      - Seitenkräfte FYV, FYH (magenta Pfeile)
      - Schwerpunkt SP mit lV/lH-Pfeilen
      - Momentenbögen MV, MH
      - Geschwindigkeitsvektoren an den Reifen
    """
    W   = 1.5
    R   = rot2(theta)

    # ── Karosserie ────────────────────────────────────────────────────────────
    body = np.array([[-lr,-W/2],[lf,-W/2],[lf,W/2],[-lr,W/2],[-lr,-W/2]])
    br   = body @ R.T + np.array([x, y])
    ax.fill(br[:,0], br[:,1], color=TUM_BLUE, alpha=0.55, zorder=5)
    ax.plot(br[:,0], br[:,1], color=TUM_BLUE, lw=1.5, zorder=6)

    # Windschutzscheibe
    ws = np.array([[lf*0.55,-W/2*0.7],[lf*0.95,-W/2*0.7],
                   [lf*0.95, W/2*0.7],[lf*0.55, W/2*0.7]])
    wr = ws @ R.T + np.array([x, y])
    ax.fill(wr[:,0], wr[:,1], color="#89CFF0", alpha=0.35, zorder=7)

    # ── Räder ─────────────────────────────────────────────────────────────────
    wl, ww = 0.7, 0.18
    wheel_local = [( lf, W/2+0.14, delta),
                   ( lf,-W/2-0.14, delta),
                   (-lr, W/2+0.14, 0.0),
                   (-lr,-W/2-0.14, 0.0)]
    for (wx, wy, wa) in wheel_local:
        Rw  = rot2(theta + wa)
        wc  = np.array([[-wl/2,-ww/2],[wl/2,-ww/2],
                         [wl/2, ww/2],[-wl/2, ww/2],[-wl/2,-ww/2]])
        wrc = wc @ Rw.T
        wp  = np.array([wx, wy]) @ R.T
        ax.fill(wrc[:,0]+x+wp[0], wrc[:,1]+y+wp[1],
                color="#111133", zorder=8)
        ax.plot(wrc[:,0]+x+wp[0], wrc[:,1]+y+wp[1],
                color="#556677", lw=0.8, zorder=9)

    # ── Achsmittelpunkte ───────────────────────────────────────────────────────
    front_c = np.array([lf, 0]) @ R.T + np.array([x, y])
    rear_c  = np.array([-lr, 0]) @ R.T + np.array([x, y])

    # ── Schwerpunkt SP ────────────────────────────────────────────────────────
    ax.plot(x, y, "o", color="#111827", ms=9, zorder=20)
    perp_dir = np.array([-np.sin(theta), np.cos(theta)])
    ax.text(x + perp_dir[0]*0.4, y + perp_dir[1]*0.4 + 0.3,
            "SP", fontsize=7, color="#111827", ha="center", zorder=21)

    # lV Pfeil: SP → front_c
    ax.annotate("", xy=(front_c[0], front_c[1]),
                xytext=(x, y),
                arrowprops=dict(arrowstyle="<->", color="#374151",
                                lw=1.0, linestyle="dashed",
                                mutation_scale=10), zorder=11)
    mid_f = np.array([(x + front_c[0])/2, (y + front_c[1])/2])
    ax.text(mid_f[0] + perp_dir[0]*0.35,
            mid_f[1] + perp_dir[1]*0.35,
            f"lV={lf:.1f}m", fontsize=7, color="#374151",
            ha="center", va="center", zorder=21)

    # lH Pfeil: SP → rear_c
    ax.annotate("", xy=(rear_c[0], rear_c[1]),
                xytext=(x, y),
                arrowprops=dict(arrowstyle="<->", color="#374151",
                                lw=1.0, linestyle="dashed",
                                mutation_scale=10), zorder=11)
    mid_r = np.array([(x + rear_c[0])/2, (y + rear_c[1])/2])
    ax.text(mid_r[0] - perp_dir[0]*0.35,
            mid_r[1] - perp_dir[1]*0.35,
            f"lH={lr:.1f}m", fontsize=7, color="#374151",
            ha="center", va="center", zorder=21)

    # ── Heading-Vektor (grün) ─────────────────────────────────────────────────
    hlen = 5.0
    ax.annotate("", xy=(x + hlen*np.cos(theta), y + hlen*np.sin(theta)),
                xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=TUM_GREEN,
                                lw=2.2, mutation_scale=16), zorder=12)
    ax.text(x + hlen*np.cos(theta)*1.05,
            y + hlen*np.sin(theta)*1.05 + 0.3,
            "Heading θ", color=TUM_GREEN, fontsize=7, zorder=13)

    # ── Absolute Fahrtrichtung v mit Schwimmwinkel β (orange) ────────────────
    abs_angle = theta + beta
    ax.annotate("", xy=(x + hlen*np.cos(abs_angle),
                         y + hlen*np.sin(abs_angle)),
                xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=TUM_ORANGE,
                                lw=2.2, mutation_scale=16,
                                linestyle="dashed"), zorder=12)
    if abs(np.rad2deg(beta)) > 0.3:
        ax.text(x + hlen*np.cos(abs_angle)*1.05,
                y + hlen*np.sin(abs_angle)*1.05 - 0.5,
                f"v (Fahrtrichtung)\nβ={np.rad2deg(beta):.1f}°",
                color=TUM_ORANGE, fontsize=7, zorder=13)

    # ── Lenkrichtung Vorderachse (hellblau) ───────────────────────────────────
    if abs(delta) > 0.01:
        steer = theta + delta
        ax.annotate("", xy=(front_c[0] + 2.0*np.cos(steer),
                              front_c[1] + 2.0*np.sin(steer)),
                    xytext=(front_c[0], front_c[1]),
                    arrowprops=dict(arrowstyle="->", color="#89B4FA",
                                    lw=1.8, mutation_scale=13), zorder=12)

    # ── Schräglaufwinkel αV (roter Bogen vorne) ───────────────────────────────
    if abs(alpha_f) > 0.005:
        t_arc = np.linspace(theta + delta, theta + delta - alpha_f, 20)
        r_arc = 2.0
        ax.plot(front_c[0] + r_arc*np.cos(t_arc),
                front_c[1] + r_arc*np.sin(t_arc),
                color=TUM_RED, lw=2.5, zorder=11)
        mid = (theta + delta + theta + delta - alpha_f) / 2
        ax.text(front_c[0] + 2.4*np.cos(mid),
                front_c[1] + 2.4*np.sin(mid),
                f"αV={np.rad2deg(alpha_f):.1f}°",
                color=TUM_RED, fontsize=9, zorder=13,
                ha="center", va="center")

    # ── Schräglaufwinkel αH (roter Bogen hinten) ──────────────────────────────
    if abs(alpha_r) > 0.005:
        t_arc = np.linspace(theta, theta - alpha_r, 20)
        r_arc = 2.0
        ax.plot(rear_c[0] + r_arc*np.cos(t_arc),
                rear_c[1] + r_arc*np.sin(t_arc),
                color="#FF7043", lw=2.5, zorder=11)
        mid = (theta + theta - alpha_r) / 2
        ax.text(rear_c[0] + 2.4*np.cos(mid),
                rear_c[1] + 2.4*np.sin(mid),
                f"αH={np.rad2deg(alpha_r):.1f}°",
                color="#FF7043", fontsize=9, zorder=13,
                ha="center", va="center")

    # ── Seitenkraft FYV (magenta, senkrecht zur Fahrzeugachse) ───────────────
    perp = np.array([-np.sin(theta), np.cos(theta)])
    fy_scale = 1.5e-3
    if abs(FYV) > 50:
        fy_vec = perp * FYV * fy_scale
        ax.annotate("", xy=(front_c[0]+fy_vec[0], front_c[1]+fy_vec[1]),
                    xytext=(front_c[0], front_c[1]),
                    arrowprops=dict(arrowstyle="->", color=PURPLE,
                                    lw=2.0, mutation_scale=13), zorder=12)
        ax.text(front_c[0]+fy_vec[0]*1.1,
                front_c[1]+fy_vec[1]*1.1,
                f"FYV\n{FYV:.0f}N",
                color=PURPLE, fontsize=8.5, ha="center", zorder=13)

    # ── Seitenkraft FYH (lila, Hinterachse) ──────────────────────────────────
    if abs(FYH) > 50:
        fy_vec = perp * FYH * fy_scale
        ax.annotate("", xy=(rear_c[0]+fy_vec[0], rear_c[1]+fy_vec[1]),
                    xytext=(rear_c[0], rear_c[1]),
                    arrowprops=dict(arrowstyle="->", color="#89DCEB",
                                    lw=2.0, mutation_scale=13), zorder=12)
        ax.text(rear_c[0]+fy_vec[0]*1.1,
                rear_c[1]+fy_vec[1]*1.1,
                f"FYH\n{FYH:.0f}N",
                color="#89DCEB", fontsize=8.5, ha="center", zorder=13)

    # ── Geschwindigkeitsvektoren an den Reifen (Feature 7) ───────────────────
    vel_len = 2.0
    _first_vr_label = True
    for (ac, angle_tire, angle_vel, vcol, alpha_val) in [
        (front_c, theta + delta, theta + delta - alpha_f, TUM_RED,    alpha_f),
        (rear_c,  theta,         theta - alpha_r,          "#FF7043",  alpha_r),
    ]:
        # Grauer Pfeil: Reifenrichtung
        ax.annotate("", xy=(ac[0] + vel_len*np.cos(angle_tire),
                              ac[1] + vel_len*np.sin(angle_tire)),
                    xytext=(ac[0], ac[1]),
                    arrowprops=dict(arrowstyle="->", color="#9CA3AF",
                                    lw=1.4, mutation_scale=10), zorder=12)
        # Farbiger gestrichelter Pfeil: Geschwindigkeitsrichtung
        if abs(alpha_val) > 0.01:
            ax.annotate("", xy=(ac[0] + vel_len*np.cos(angle_vel),
                                  ac[1] + vel_len*np.sin(angle_vel)),
                        xytext=(ac[0], ac[1]),
                        arrowprops=dict(arrowstyle="->", color=vcol,
                                        lw=1.4, mutation_scale=10,
                                        linestyle="dashed"), zorder=12)
            vr_x = ac[0] + vel_len*np.cos(angle_vel)*1.15
            vr_y = ac[1] + vel_len*np.sin(angle_vel)*1.15
            if _first_vr_label:
                ax.text(vr_x, vr_y, "v_R", fontsize=7, color=vcol,
                        ha="center", zorder=13)
                _first_vr_label = False

    # ── Momentenbögen MV, MH (Feature 2) ─────────────────────────────────────
    M_V = FYV * lf
    M_H = FYH * lr
    draw_moment_arc(ax, front_c[0], front_c[1], M_V, theta, TUM_GREEN,
                    f"MV={M_V:.0f}Nm")
    draw_moment_arc(ax, rear_c[0],  rear_c[1],  M_H, theta, TUM_RED,
                    f"MH={M_H:.0f}Nm")


# ─────────────────────────────────────────────────────────────────────────────
# HAUPTFENSTER
# ─────────────────────────────────────────────────────────────────────────────

class LinearSimWindow(QMainWindow):

    # ── feste Fahrzeugparameter ────────────────────────────────────────────────
    M   = 1500.0   # kg
    JZ  = 2500.0   # kg·m²
    LF  = 1.3      # m  (SP → Vorderachse)
    LR  = 1.4      # m  (SP → Hinterachse)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Lineares Einspurmodell – Live-Simulation  |  TUM GAV")
        self.showMaximized()
        self._dark_palette()

        # ── Simulationszustand ────────────────────────────────────────────────
        self.x      = 0.0
        self.y      = 0.0
        self.theta  = 0.0   # Heading [rad]
        self.dtheta = 0.0   # Gierrate [rad/s]
        self.beta   = 0.0   # Schwimmwinkel [rad]
        self.t      = 0.0

        self.trail_x = [0.0]
        self.trail_y = [0.0]

        # Zeitreihen (max 400 Punkte)
        self._hist: dict = {k: [] for k in
                            ["t","beta","dtheta","alpha_f","alpha_r",
                             "FYV","FYH","ay","delta"]}

        self.running = False
        self._ss_beta   = None   # stationärer Schwimmwinkel
        self._ss_dtheta = None   # stationäre Gierrate

        # ── Layout ────────────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._header())

        body = QHBoxLayout()
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(8)

        # ── linke Spalte in ScrollArea ────────────────────────────────────────
        ctrl_widget = QWidget()
        ctrl_widget.setLayout(self._controls())
        ctrl_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        scroll = QScrollArea()
        scroll.setWidget(ctrl_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFixedWidth(360)
        scroll.setStyleSheet(
            "QScrollArea { border:none; background:transparent; }"
            "QScrollBar:vertical { width:6px; background:#E5E7EB; border-radius:3px; }"
            "QScrollBar::handle:vertical { background:#9CA3AF; border-radius:3px; }"
        )
        body.addWidget(scroll)
        body.addWidget(self._canvas_widget(), stretch=1)
        root.addLayout(body)

        # ── Timer ─────────────────────────────────────────────────────────────
        self.timer = QTimer()
        self.timer.setInterval(int(DT * 1000))
        self.timer.timeout.connect(self._step)

        self._redraw(0, 0, 0, 0, 0, 0)

    # ─────────────────────────────────────────────────────────────────────────
    def _dark_palette(self):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor(BG_DARK))
        p.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_LIGHT))
        p.setColor(QPalette.ColorRole.Base,            QColor(BG_PANEL))
        p.setColor(QPalette.ColorRole.Text,            QColor(TEXT_LIGHT))
        p.setColor(QPalette.ColorRole.Button,          QColor(BG_WIDGET))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT_LIGHT))
        p.setColor(QPalette.ColorRole.Highlight,       QColor(TUM_BLUE))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(p)

    # ─────────────────────────────────────────────────────────────────────────
    def _header(self):
        f = QFrame()
        f.setFixedHeight(54)
        f.setStyleSheet(
            f"background:{BG_PANEL}; border-bottom:2px solid {TUM_BLUE};")
        hl = QHBoxLayout(f)
        hl.setContentsMargins(18, 0, 18, 0)
        hl.addWidget(lbl("🚗  Lineares Einspurmodell – Live-Simulation",
                          bold=True, size=13))
        hl.addStretch()
        hl.addWidget(lbl(
            "β̇ = f(β, θ̇, δ, v, CV, CH)   |   "
            "θ̈ = g(β, θ̇, δ, v, CV, CH)   |   "
            "αV = δ − β − (lV/v)·θ̇   |   αH = −β + (lH/v)·θ̇",
            size=8, color=TEXT_DIM))
        return f

    # ─────────────────────────────────────────────────────────────────────────
    def _controls(self):
        col = QVBoxLayout()
        col.setSpacing(8)

        # ── Eingaben ──────────────────────────────────────────────────────────
        gb_in = QGroupBox("Eingabe  u = [δ, v]")
        gb_in.setStyleSheet(GB_CSS)
        lay_in = QVBoxLayout(gb_in)
        lay_in.setSpacing(6)

        self.sl_delta, self.vl_delta = add_slider_row(
            lay_in, "Lenkwinkel  δ", "°", -15, 15, 0,
            scale=10, color=TUM_ORANGE)
        self.sl_v, self.vl_v = add_slider_row(
            lay_in, "Geschwindigkeit  v", "m/s", 5, 40, 15,
            scale=10, color=TUM_GREEN)
        col.addWidget(gb_in)

        # ── Reifenparameter ───────────────────────────────────────────────────
        gb_tire = QGroupBox("Reifenparameter (Schräglaufsteifigkeit)")
        gb_tire.setStyleSheet(GB_CSS)
        lay_t = QVBoxLayout(gb_tire)
        lay_t.setSpacing(6)

        self.sl_cv, self.vl_cv = add_slider_row(
            lay_t, "c_αV  Vorderachse", "kN/rad", 20, 120, 60,
            scale=1, color="#89B4FA", decimals=0)
        self.sl_ch, self.vl_ch = add_slider_row(
            lay_t, "c_αH  Hinterachse", "kN/rad", 20, 120, 60,
            scale=1, color="#89DCEB", decimals=0)

        # Unter-/Übersteuern Badge
        self.lbl_steer = lbl("●  Neutral", bold=True, size=11,
                              color=TUM_GREEN)
        lay_t.addWidget(self.lbl_steer)
        col.addWidget(gb_tire)

        # ── Live-Zustände ─────────────────────────────────────────────────────
        gb_st = QGroupBox("Zustände  x = [x, y, θ, θ̇, β]")
        gb_st.setStyleSheet(GB_CSS)
        lay_s = QVBoxLayout(gb_st)
        lay_s.setSpacing(3)

        def sv(text, color=TEXT_DIM):
            w = lbl(text, size=10, color=color)
            lay_s.addWidget(w)
            return w

        self.sv_x     = sv("x       =   0.00 m")
        self.sv_y     = sv("y       =   0.00 m")
        self.sv_th    = sv("θ       =   0.0 °")
        self.sv_dth   = sv("θ̇      =   0.0 °/s",  color=TUM_ORANGE)
        self.sv_beta  = sv("β       =   0.0 °",    color=TUM_ORANGE)
        self.sv_af    = sv("αV      =   0.0 °",    color=TUM_RED)
        self.sv_ar    = sv("αH      =   0.0 °",    color="#FF7043")
        self.sv_fyv   = sv("FYV     =   0 N",      color=PURPLE)
        self.sv_fyh   = sv("FYH     =   0 N",      color="#89DCEB")
        self.sv_ay    = sv("ay      =   0.0 m/s²", color=TEXT_DIM)
        self.sv_t     = sv("t       =   0.0 s")
        col.addWidget(gb_st)

        # ── Legende ───────────────────────────────────────────────────────────
        gb_leg = QGroupBox("Legende")
        gb_leg.setStyleSheet(GB_CSS)
        ll = QVBoxLayout(gb_leg)
        ll.setSpacing(2)
        items = [
            (TUM_GREEN,  "── Heading θ  (Fahrzeuglängsachse)"),
            (TUM_ORANGE, "-- v  (Fahrtrichtung, inkl. β)"),
            ("#89B4FA",  "── Lenkrichtung δ"),
            (TUM_RED,    "⌒  αV  Schräglaufwinkel vorne"),
            ("#FF7043",  "⌒  αH  Schräglaufwinkel hinten"),
            (PURPLE,     "→  FYV  Seitenkraft vorne"),
            ("#89DCEB",  "→  FYH  Seitenkraft hinten"),
        ]
        for color, text in items:
            ll.addWidget(lbl(text, size=10, color=color))
        col.addWidget(gb_leg)

        # ── Buttons ───────────────────────────────────────────────────────────
        self.btn_go      = QPushButton("▶  Start")
        self.btn_reset   = QPushButton("↺  Reset")
        self.btn_sprung  = QPushButton("⚡  Lenksprung")
        self.btn_go.setStyleSheet(BTN_CSS(TUM_BLUE))
        self.btn_reset.setStyleSheet(BTN_CSS("#445566"))
        self.btn_sprung.setStyleSheet(BTN_CSS(TUM_GREEN))
        self.btn_go.clicked.connect(self._toggle)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_sprung.clicked.connect(self._lenksprung)
        br = QHBoxLayout()
        br.addWidget(self.btn_go)
        br.addWidget(self.btn_reset)
        col.addLayout(br)
        col.addWidget(self.btn_sprung)
        col.addStretch()

        # Signale
        for sl in (self.sl_delta, self.sl_v, self.sl_cv, self.sl_ch):
            sl.valueChanged.connect(self._slider_changed)

        return col

    # ─────────────────────────────────────────────────────────────────────────
    def _canvas_widget(self):
        """Draufsicht oben + Tab-Widget unten (Zeitplots | Bewegungsgleichungen)."""
        wrapper = QWidget()
        vl = QVBoxLayout(wrapper)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        # ── Draufsicht ────────────────────────────────────────────────────────
        self.fig_top = Figure(figsize=(10, 5.5))
        self.fig_top.patch.set_facecolor("#F0F2F5")
        self.canvas_top = FigureCanvas(self.fig_top)
        self.ax_top = self.fig_top.add_axes([0.05, 0.05, 0.90, 0.90])
        self.ax_top.set_facecolor("#F0F2F5")
        vl.addWidget(self.canvas_top, stretch=3)

        # ── Tab-Widget (unten) ────────────────────────────────────────────────
        tab = QTabWidget()
        tab.setStyleSheet(f"""
            QTabWidget::pane  {{ border:1px solid #D1D5DB; border-radius:6px;
                                 background:#F0F2F5; }}
            QTabBar::tab      {{ background:#E5E7EB; color:#374151;
                                 padding:6px 18px; font-size:10pt;
                                 border-radius:4px; margin-right:3px; }}
            QTabBar::tab:selected {{ background:{TUM_BLUE}; color:#fff;
                                     font-weight:bold; }}
        """)

        # ── Tab 1: Zeitreihen ─────────────────────────────────────────────────
        w_time = QWidget()
        vl_time = QVBoxLayout(w_time)
        vl_time.setContentsMargins(0, 0, 0, 0)
        self.fig_bot = Figure(figsize=(10, 2.8))
        self.fig_bot.patch.set_facecolor("#F0F2F5")
        self.canvas_bot = FigureCanvas(self.fig_bot)
        self.ax_b1 = self.fig_bot.add_axes([0.06, 0.20, 0.27, 0.68])
        self.ax_b2 = self.fig_bot.add_axes([0.38, 0.20, 0.27, 0.68])
        self.ax_b3 = self.fig_bot.add_axes([0.70, 0.20, 0.27, 0.68])
        for ax in (self.ax_b1, self.ax_b2, self.ax_b3):
            ax.set_facecolor("#F0F2F5")
        vl_time.addWidget(self.canvas_bot)
        tab.addTab(w_time, "📈  Zeitverläufe")

        # ── Tab 2: Reifenkennlinie ────────────────────────────────────────────
        w_tire = QWidget()
        vl_tire = QVBoxLayout(w_tire)
        vl_tire.setContentsMargins(0, 0, 0, 0)
        self.fig_tire = Figure(figsize=(10, 2.8))
        self.fig_tire.patch.set_facecolor("#F0F2F5")
        self.canvas_tire = FigureCanvas(self.fig_tire)
        self.ax_tire_f = self.fig_tire.add_axes([0.07, 0.18, 0.40, 0.72])
        self.ax_tire_r = self.fig_tire.add_axes([0.57, 0.18, 0.40, 0.72])
        for ax in (self.ax_tire_f, self.ax_tire_r):
            ax.set_facecolor("#F0F2F5")
        vl_tire.addWidget(self.canvas_tire)
        tab.addTab(w_tire, "🔵  Reifenkennlinie")

        # ── Tab 3: Kausalität ─────────────────────────────────────────────────
        w_causal = QWidget()
        vl_causal = QVBoxLayout(w_causal)
        vl_causal.setContentsMargins(0, 0, 0, 0)
        self.fig_causal = Figure(figsize=(10, 2.8))
        self.fig_causal.patch.set_facecolor("#F0F2F5")
        self.canvas_causal = FigureCanvas(self.fig_causal)
        self.ax_causal = self.fig_causal.add_axes([0.0, 0.0, 1.0, 1.0])
        self.ax_causal.set_facecolor("#F0F2F5")
        self.ax_causal.axis("off")
        vl_causal.addWidget(self.canvas_causal)
        tab.addTab(w_causal, "⚡  Kausalität")

        # ── Tab 4: Bewegungsgleichungen ───────────────────────────────────────
        w_eq = QWidget()
        vl_eq = QVBoxLayout(w_eq)
        vl_eq.setContentsMargins(0, 0, 0, 0)
        self.fig_eq = Figure(figsize=(10, 2.8))
        self.fig_eq.patch.set_facecolor("#F0F2F5")
        self.canvas_eq = FigureCanvas(self.fig_eq)
        self._draw_equations()
        vl_eq.addWidget(self.canvas_eq)
        tab.addTab(w_eq, "📐  Bewegungsgleichungen")

        # ── Tab 5: Modellannahmen ─────────────────────────────────────────────
        w_mod = QWidget()
        vl_mod = QVBoxLayout(w_mod)
        vl_mod.setContentsMargins(0, 0, 0, 0)
        self.fig_mod = Figure(figsize=(10, 2.8))
        self.fig_mod.patch.set_facecolor("#F0F2F5")
        self.canvas_mod = FigureCanvas(self.fig_mod)
        self._draw_modellannahmen()
        vl_mod.addWidget(self.canvas_mod)
        tab.addTab(w_mod, "⚠  Modellannahmen")

        # ── Tab 6: Eigenwerte ─────────────────────────────────────────────────
        w_ev = QWidget()
        w_ev.setStyleSheet("background:#F0F2F5;")
        vl_ev = QVBoxLayout(w_ev)
        vl_ev.setContentsMargins(20, 16, 20, 16)
        vl_ev.setSpacing(10)

        def ev_lbl(text, size=11, bold=False, color=TEXT_DIM):
            w = lbl(text, bold=bold, size=size, color=color)
            vl_ev.addWidget(w)
            return w

        ev_lbl("Eigenwerte  λ₁, λ₂  der Systemmatrix A", size=13,
               bold=True, color=TEXT_LIGHT)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#D1D5DB;"); vl_ev.addWidget(sep)

        self.sv_ev1     = ev_lbl("λ₁  =  –", size=12, color=TEXT_DIM)
        self.sv_ev2     = ev_lbl("λ₂  =  –", size=12, color=TEXT_DIM)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color:#D1D5DB;"); vl_ev.addWidget(sep2)

        self.sv_ev_info = ev_lbl("Re(λ) < 0  →  stabil", size=12,
                                  color=TUM_GREEN)
        self.sv_tau     = ev_lbl("τ  =  –   |   4τ  =  –", size=11,
                                  color=TEXT_DIM)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("color:#D1D5DB;"); vl_ev.addWidget(sep3)

        ev_lbl("Interpretation:", size=10, bold=True, color=TEXT_LIGHT)
        ev_lbl("Re(λ) < 0  →  Störungen klingen ab  (stabil)", size=10,
               color=TUM_GREEN)
        ev_lbl("Re(λ) > 0  →  Störungen wachsen     (instabil)", size=10,
               color=TUM_RED)
        ev_lbl("Im(λ) ≠ 0  →  gedämpfte Schwingung  (Überschwingen möglich)",
               size=10, color=TUM_ORANGE)
        ev_lbl("τ = −1/Re(λ)  →  Zeitkonstante;  4τ ≈ Einschwingzeit",
               size=10, color=TEXT_DIM)

        vl_ev.addStretch()
        tab.addTab(w_ev, "λ  Eigenwerte")

        vl.addWidget(tab, stretch=2)
        return wrapper

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_equations(self):
        """Rendert die Bewegungsgleichungen des linearen Einspurmodells als LaTeX."""
        self.fig_eq.clear()
        ax = self.fig_eq.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_facecolor("#F0F2F5")
        ax.axis("off")

        # Spalte 1 – Kinematik & Zustandsgleichungen
        col1 = (
            r"$\bf{Kinematik}$" + "\n\n"
            r"$\dot{x} = v \cdot \cos(\theta + \beta)$" + "\n\n"
            r"$\dot{y} = v \cdot \sin(\theta + \beta)$" + "\n\n\n"
            r"$\bf{Zustandsgleichungen}$" + "\n\n"
            r"$\dot{\beta} = -\dfrac{c_{\alpha V}+c_{\alpha H}}{m\,v}\,\beta"
            r"\ +\ \left(\dfrac{c_{\alpha H}\,l_H - c_{\alpha V}\,l_V}{m\,v^2}-1\right)\dot{\theta}"
            r"\ +\ \dfrac{c_{\alpha V}}{m\,v}\,\delta$" + "\n\n"
            r"$\ddot{\theta} = \dfrac{c_{\alpha H}\,l_H - c_{\alpha V}\,l_V}{J_z}\,\beta"
            r"\ -\ \dfrac{c_{\alpha H}\,l_H^2 + c_{\alpha V}\,l_V^2}{J_z\,v}\,\dot{\theta}"
            r"\ +\ \dfrac{c_{\alpha V}\,l_V}{J_z}\,\delta$"
        )

        # Spalte 2 – Schräglaufwinkel & Kräfte
        col2 = (
            r"$\bf{Schr\"{a}glaufwinkel}$" + "\n\n"
            r"$\alpha_V = \delta - \beta - \dfrac{l_V}{v}\,\dot{\theta}$" + "\n\n"
            r"$\alpha_H = -\beta + \dfrac{l_H}{v}\,\dot{\theta}$" + "\n\n\n"
            r"$\bf{Seitenkr\"{a}fte\ (linear)}$" + "\n\n"
            r"$F_{yV} = c_{\alpha V} \cdot \alpha_V$" + "\n\n"
            r"$F_{yH} = c_{\alpha H} \cdot \alpha_H$" + "\n\n\n"
            r"$\bf{Querbeschleunigung}$" + "\n\n"
            r"$a_y = v \cdot \dot{\theta}$"
        )

        ax.text(0.02, 0.97, col1, transform=ax.transAxes,
                fontsize=9.5, va="top", ha="left",
                color="#111827", linespacing=1.8,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF",
                          edgecolor="#D1D5DB", alpha=0.85))

        ax.text(0.55, 0.97, col2, transform=ax.transAxes,
                fontsize=9.5, va="top", ha="left",
                color="#111827", linespacing=1.8,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF",
                          edgecolor="#D1D5DB", alpha=0.85))

        # Trennlinie
        ax.axvline(0.52, color="#D1D5DB", lw=1.2, ls="--")

        self.canvas_eq.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_modellannahmen(self):
        """Rendert die Modellannahmen und -grenzen als strukturierten Text."""
        self.fig_mod.clear()
        ax = self.fig_mod.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_facecolor("#F0F2F5")
        ax.axis("off")

        col1 = (
            r"$\bf{Modellannahmen}$" + "\n\n"
            "① Kleine Winkel\n"
            r"   $\alpha < 5°,\quad \beta < 12°$" + "\n"
            r"   $\Rightarrow$ Linearisierung gültig" + "\n\n"
            "② Lineare Reifenkennlinie\n"
            r"   $F_Y = c_\alpha \cdot \alpha$  (kein Sättigungsbereich)" + "\n\n"
            "③ Keine Reifensättigung\n"
            "   Haftgrenze nicht modelliert\n\n"
            "④ Konstante Längsgeschwindigkeit\n"
            r"   $v = \mathrm{const}$,  keine Längsdynamik"
        )

        col2 = (
            r"$\bf{Zustandsvektor}$" + "\n\n"
            r"$x = [x_{pos},\ y_{pos},\ \theta,\ \dot{\theta},\ \beta]^T$" + "\n\n\n"
            r"$\bf{Eingangsvektor}$" + "\n\n"
            r"$u = [\delta,\ v]^T$" + "\n\n\n"
            r"$\bf{G\"{u}ltigkeitsbereich}$" + "\n\n"
            r"Querbeschleunigung $a_y \lesssim 0.4\,g$" + "\n\n"
            r"Schräglaufwinkel $|\alpha| < 5°$" + "\n\n"
            r"Schwimmwinkel $|\beta| < 12°$"
        )

        ax.text(0.02, 0.97, col1, transform=ax.transAxes,
                fontsize=9.5, va="top", ha="left", color="#111827",
                linespacing=1.7,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF3C7",
                          edgecolor="#F59E0B", alpha=0.9))

        ax.text(0.55, 0.97, col2, transform=ax.transAxes,
                fontsize=9.5, va="top", ha="left", color="#111827",
                linespacing=1.7,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF",
                          edgecolor="#D1D5DB", alpha=0.9))

        ax.axvline(0.52, color="#D1D5DB", lw=1.2, ls="--")
        self.canvas_mod.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────
    def _update_causal_tab(self, delta, v, CV, CH,
                            alpha_f, alpha_r, FYV, FYH):
        """Zeichnet die Kausalkette als annotierte Text-Boxen mit Pfeilen."""
        ax = self.ax_causal
        ax.clear()
        ax.set_facecolor("#F0F2F5")
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        lf, lr = self.LF, self.LR
        M_V = FYV * lf
        M_H = FYH * lr

        def _box_color(val, ref=None):
            if ref is None:
                ref = abs(val) + 1e-6
            if abs(val) < 0.1 * ref:
                return "#F3F4F6"
            return "#D1FAE5" if val > 0 else "#FEE2E2"

        # Referenzwerte für Nahe-Null-Prüfung
        ref_fy  = max(abs(FYV), abs(FYH), 1.0)
        ref_m   = max(abs(M_V), abs(M_H), 1.0)
        ref_af  = max(abs(alpha_f), abs(alpha_r), 1e-6)

        # Positionen der Boxes (x, y im Axes-Koordinaten)
        # Zeile 1 (oben, y=0.78): delta, alphaV, FYV, MV
        # Zeile 2 (mitte, y=0.45): ddtheta, dtheta, theta
        # Zeile 3 (unten, y=0.12): beta, alphaH, FYH, MH
        boxes = {
            "delta":   (0.05, 0.78, f"δ\n{np.rad2deg(delta):.1f}°",
                        _box_color(delta, abs(delta)+1e-6)),
            "alphaV":  (0.22, 0.78,
                        f"αV = δ−β−(lV/v)θ̇\n{np.rad2deg(alpha_f):.2f}°",
                        _box_color(alpha_f, ref_af)),
            "FYV":     (0.44, 0.78,
                        f"FYV = cV·αV\n{FYV:.0f} N",
                        _box_color(FYV, ref_fy)),
            "MV":      (0.63, 0.78,
                        f"MV = FYV·lV\n{M_V:.0f} Nm",
                        _box_color(M_V, ref_m)),
            "ddtheta": (0.63, 0.45,
                        f"θ̈ = (MV−MH)/Jz\n{(M_V-M_H)/self.JZ:.3f} rad/s²",
                        _box_color(M_V - M_H, ref_m)),
            "dtheta":  (0.78, 0.45,
                        f"θ̇\n{np.rad2deg(self.dtheta):.1f}°/s",
                        _box_color(self.dtheta, abs(self.dtheta)+1e-6)),
            "theta":   (0.90, 0.45,
                        f"θ\n{np.rad2deg(self.theta):.1f}°",
                        _box_color(self.theta, abs(self.theta)+1e-6)),
            "beta":    (0.05, 0.12,
                        f"β\n{np.rad2deg(self.beta):.2f}°",
                        _box_color(self.beta, abs(self.beta)+1e-6)),
            "alphaH":  (0.22, 0.12,
                        f"αH = −β+(lH/v)θ̇\n{np.rad2deg(alpha_r):.2f}°",
                        _box_color(alpha_r, ref_af)),
            "FYH":     (0.44, 0.12,
                        f"FYH = cH·αH\n{FYH:.0f} N",
                        _box_color(FYH, ref_fy)),
            "MH":      (0.63, 0.12,
                        f"MH = FYH·lH\n{M_H:.0f} Nm",
                        _box_color(M_H, ref_m)),
        }

        # Boxes zeichnen
        box_artists = {}
        for key, (bx, by, text, fc) in boxes.items():
            t = ax.text(bx, by, text,
                        transform=ax.transAxes,
                        fontsize=7.5, va="center", ha="center",
                        bbox=dict(boxstyle="round,pad=0.3",
                                  facecolor=fc,
                                  edgecolor=TUM_BLUE,
                                  linewidth=1.2),
                        zorder=5)
            box_artists[key] = (bx, by)

        # Pfeile zwischen Boxes
        arrow_pairs = [
            # Zeile 1
            ("delta",   "alphaV"),
            ("alphaV",  "FYV"),
            ("FYV",     "MV"),
            # MV → ddtheta (vertikal)
            ("MV",      "ddtheta"),
            # ddtheta → dtheta → theta
            ("ddtheta", "dtheta"),
            ("dtheta",  "theta"),
            # Zeile 3
            ("beta",    "alphaH"),
            ("alphaH",  "FYH"),
            ("FYH",     "MH"),
            # MH → ddtheta (vertikal)
            ("MH",      "ddtheta"),
        ]

        for (src_key, dst_key) in arrow_pairs:
            sx, sy = box_artists[src_key]
            dx, dy = box_artists[dst_key]
            # Offset: für horizontale Pfeile links/rechts an der Box-Kante
            if abs(sy - dy) < 0.01:  # horizontal
                x_start = sx + 0.07
                x_end   = dx - 0.07
                y_start = sy
                y_end   = dy
            else:  # vertikal
                x_start = sx
                x_end   = dx
                y_start = sy + (0.05 if sy < dy else -0.05)
                y_end   = dy + (0.05 if dy < sy else -0.05)
            ax.annotate("",
                        xy=(x_end, y_end),
                        xytext=(x_start, y_start),
                        xycoords="axes fraction",
                        textcoords="axes fraction",
                        arrowprops=dict(arrowstyle="->",
                                        color="#374151",
                                        lw=1.5),
                        zorder=4)

        # Titel
        ax.text(0.5, 0.97, "Kausalkette des linearen Einspurmodells",
                transform=ax.transAxes,
                fontsize=9, ha="center", va="top",
                color=TEXT_LIGHT, fontweight="bold")

        self.canvas_causal.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────
    def _compute_eigenvalues(self, v, CV, CH):
        """Eigenwerte der Systemmatrix A des linearen Einspurmodells."""
        lf, lr = self.LF, self.LR
        m,  Jz = self.M,  self.JZ
        A = np.array([
            [-(CV + CH) / (m * v),
             (CH * lr - CV * lf) / (m * v**2) - 1.0],
            [(CH * lr - CV * lf) / Jz,
             -(CH * lr**2 + CV * lf**2) / (Jz * v)]
        ])
        return np.linalg.eigvals(A)

    # ─────────────────────────────────────────────────────────────────────────
    def _compute_steady_state(self, delta, v, CV, CH):
        """Stationäre Lösung β_ss, θ̇_ss für konstantes δ, v."""
        lf, lr = self.LF, self.LR
        m,  Jz = self.M,  self.JZ
        A = np.array([
            [-(CV + CH) / (m * v),
             (CH * lr - CV * lf) / (m * v**2) - 1.0],
            [(CH * lr - CV * lf) / Jz,
             -(CH * lr**2 + CV * lf**2) / (Jz * v)]
        ])
        b = np.array([CV / (m * v) * delta,
                      CV * lf / Jz * delta])
        try:
            ss = np.linalg.solve(-A, b)
            return ss[0], ss[1]   # β_ss, θ̇_ss
        except np.linalg.LinAlgError:
            return None, None

    # ─────────────────────────────────────────────────────────────────────────
    def _update_tire_canvas(self, alpha_f, alpha_r, FYV, FYH, CV, CH):
        """Aktualisiert die Reifenkennlinie mit aktuellem Arbeitspunkt."""
        alpha_range = np.linspace(np.deg2rad(-12), np.deg2rad(12), 200)
        lim_rad = np.deg2rad(5)

        for ax, c_alpha, alpha_op, F_op, title, color in [
            (self.ax_tire_f, CV, alpha_f, FYV,
             "Vorderachse  FYV = cαV · αV", TUM_RED),
            (self.ax_tire_r, CH, alpha_r, FYH,
             "Hinterachse  FYH = cαH · αH", "#FF7043"),
        ]:
            ax.clear()
            ax.set_facecolor("#F0F2F5")

            # Ungültiger Bereich (|α| > 5°)
            ax.axvspan(np.rad2deg(lim_rad),  12, color="#FEE2E2", alpha=0.5)
            ax.axvspan(-12, -np.rad2deg(lim_rad), color="#FEE2E2", alpha=0.5)
            ax.axvline( np.rad2deg(lim_rad), color=TUM_RED, lw=1, ls="--",
                        label="Linearitätsgrenze ±5°")
            ax.axvline(-np.rad2deg(lim_rad), color=TUM_RED, lw=1, ls="--")

            # Lineare Kennlinie
            F_line = c_alpha * alpha_range
            ax.plot(np.rad2deg(alpha_range), F_line / 1000,
                    color=TUM_BLUE, lw=2, label=f"c_α = {c_alpha/1000:.0f} kN/rad")

            # Aktueller Arbeitspunkt
            ax.plot(np.rad2deg(alpha_op), F_op / 1000, "o",
                    color=color, ms=10, zorder=10,
                    label=f"Arbeitspunkt  α={np.rad2deg(alpha_op):.1f}°")

            ax.axhline(0, color="#9CA3AF", lw=0.8)
            ax.axvline(0, color="#9CA3AF", lw=0.8)
            ax.set_xlim(-12, 12)
            ax.set_xlabel("α [°]", fontsize=8)
            ax.set_ylabel("F_Y [kN]", fontsize=8)
            ax.set_title(title, fontsize=8, color="#111827")
            ax.tick_params(labelsize=7)
            ax.legend(fontsize=7, loc="upper left")

        self.canvas_tire.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────
    def _lenksprung(self):
        """Reset + sofortiger Start mit aktuellem δ als Sprungeingang."""
        # Stationäre Zielwerte berechnen und merken
        delta, v, CV, CH = self._get_params()
        self._ss_beta, self._ss_dtheta = self._compute_steady_state(
            delta, v, CV, CH)
        # Reset ohne Neustart, dann direkt starten
        if self.running:
            self.timer.stop()
            self.running = False
        self.x = self.y = self.theta = self.dtheta = self.beta = self.t = 0.0
        self.trail_x = [0.0]; self.trail_y = [0.0]
        for k in self._hist:
            self._hist[k].clear()
        self.timer.start()
        self.running = True
        self.btn_go.setText("⏸  Pause")
        self.btn_go.setStyleSheet(BTN_CSS(TUM_ORANGE))

    # ─────────────────────────────────────────────────────────────────────────
    def _get_params(self):
        delta = np.deg2rad(self.sl_delta.value() / 10)
        v     = max(self.sl_v.value() / 10, 1.0)   # v >= 1 m/s für Division
        CV    = float(self.sl_cv.value()) * 1000    # kN → N
        CH    = float(self.sl_ch.value()) * 1000
        return delta, v, CV, CH

    # ─────────────────────────────────────────────────────────────────────────
    def _compute_derived(self, delta, v, CV, CH):
        """Berechnet alle abgeleiteten Größen aus dem aktuellen Zustand."""
        lf, lr = self.LF, self.LR

        # Schräglaufwinkel (Folie 04-63)
        alpha_f = delta - self.beta - (lf / v) * self.dtheta
        alpha_r =       - self.beta + (lr / v) * self.dtheta

        # Seitenkräfte (linear)
        FYV = CV * alpha_f
        FYH = CH * alpha_r

        # Querbeschleunigung (näherungsweise stationär)
        ay = v * self.dtheta

        return alpha_f, alpha_r, FYV, FYH, ay

    # ─────────────────────────────────────────────────────────────────────────
    def _ode(self, beta, dtheta, delta, v, CV, CH):
        """
        Rechte Seite der Bewegungsgleichungen (Folie 04-66).
        Gibt (dbeta, ddtheta) zurück.
        """
        lf, lr = self.LF, self.LR
        m,  Jz = self.M,  self.JZ

        dbeta   = (-(CV + CH) / (m * v) * beta
                   + ((CH * lr - CV * lf) / (m * v**2) - 1.0) * dtheta
                   + CV / (m * v) * delta)

        ddtheta = ((CH * lr - CV * lf) / Jz * beta
                   - (CH * lr**2 + CV * lf**2) / (Jz * v) * dtheta
                   + CV * lf / Jz * delta)

        return dbeta, ddtheta

    # ─────────────────────────────────────────────────────────────────────────
    def _step(self):
        delta, v, CV, CH = self._get_params()

        # ── RK4-Integration (viel stabiler als Euler) ────────────────────────
        # Zustand: [beta, dtheta]
        b0, d0 = self.beta, self.dtheta

        db1, dd1 = self._ode(b0,            d0,            delta, v, CV, CH)
        db2, dd2 = self._ode(b0+db1*DT/2,   d0+dd1*DT/2,  delta, v, CV, CH)
        db3, dd3 = self._ode(b0+db2*DT/2,   d0+dd2*DT/2,  delta, v, CV, CH)
        db4, dd4 = self._ode(b0+db3*DT,     d0+dd3*DT,    delta, v, CV, CH)

        new_beta   = b0 + DT/6 * (db1 + 2*db2 + 2*db3 + db4)
        new_dtheta = d0 + DT/6 * (dd1 + 2*dd2 + 2*dd3 + dd4)

        # ── Physikalische Grenzen des linearen Modells ────────────────────────
        # Lineares Modell gilt nur für kleine Winkel (Vorlesung: bis ~0.4g)
        # Gierrate: reale Fahrzeuge ca. max ±50°/s (0.87 rad/s)
        new_dtheta = np.clip(new_dtheta, np.deg2rad(-60), np.deg2rad(60))
        # Schwimmwinkel: Modell verliert ab ~±12° Gültigkeit
        new_beta   = np.clip(new_beta,   np.deg2rad(-12), np.deg2rad(12))

        # ── NaN/Inf Schutz ────────────────────────────────────────────────────
        if not (np.isfinite(new_beta) and np.isfinite(new_dtheta)):
            self.timer.stop()
            self.running = False
            self.btn_go.setText("▶  Start")
            self.btn_go.setStyleSheet(BTN_CSS(TUM_BLUE))
            self.lbl_steer.setText("⚠  Numerisch instabil – Reset!")
            self.lbl_steer.setStyleSheet(
                f"color:{TUM_RED}; background:transparent; font-weight:bold;")
            return

        self.beta   = new_beta
        self.dtheta = new_dtheta

        # Position & Heading integrieren
        xdot = v * np.cos(self.theta + self.beta)
        ydot = v * np.sin(self.theta + self.beta)
        self.x     += xdot         * DT
        self.y     += ydot         * DT
        self.theta += self.dtheta  * DT
        self.t     += DT

        self.trail_x.append(self.x)
        self.trail_y.append(self.y)

        alpha_f, alpha_r, FYV, FYH, ay = self._compute_derived(
            delta, v, CV, CH)

        # Zeitreihen puffern
        for k, val in zip(
                ["t","beta","dtheta","alpha_f","alpha_r","FYV","FYH","ay","delta"],
                [self.t, np.rad2deg(self.beta), np.rad2deg(self.dtheta),
                 np.rad2deg(alpha_f), np.rad2deg(alpha_r),
                 FYV, FYH, ay, np.rad2deg(delta)]):
            self._hist[k].append(val)
            if len(self._hist[k]) > 400:
                self._hist[k].pop(0)

        self._update_state_labels(delta, v, CV, CH,
                                   alpha_f, alpha_r, FYV, FYH, ay)
        self._redraw(delta, alpha_f, alpha_r, FYV, FYH, ay)

    # ─────────────────────────────────────────────────────────────────────────
    def _update_state_labels(self, delta, v, CV, CH,
                              alpha_f, alpha_r, FYV, FYH, ay):
        self.sv_x.setText(   f"x       = {self.x:8.2f} m")
        self.sv_y.setText(   f"y       = {self.y:8.2f} m")
        self.sv_th.setText(  f"θ       = {np.rad2deg(self.theta):7.1f} °")
        self.sv_dth.setText( f"θ̇      = {np.rad2deg(self.dtheta):7.2f} °/s")
        self.sv_beta.setText(f"β       = {np.rad2deg(self.beta):7.2f} °")
        self.sv_af.setText(  f"αV      = {np.rad2deg(alpha_f):7.2f} °")
        self.sv_ar.setText(  f"αH      = {np.rad2deg(alpha_r):7.2f} °")
        self.sv_fyv.setText( f"FYV     = {FYV:8.0f} N")
        self.sv_fyh.setText( f"FYH     = {FYH:8.0f} N")
        self.sv_ay.setText(  f"ay      = {ay:7.2f} m/s²")
        self.sv_t.setText(   f"t       = {self.t:7.1f} s")

        # ── Eigenwerte ────────────────────────────────────────────────────────
        eigs = self._compute_eigenvalues(v, CV, CH)
        for sv_lbl, ev in zip((self.sv_ev1, self.sv_ev2), eigs):
            re, im = ev.real, ev.imag
            if abs(im) > 1e-6:
                txt = f"λ = {re:+.3f}  {im:+.3f}j"
            else:
                txt = f"λ = {re:+.3f}"
            color = TUM_RED if re > 0 else TUM_GREEN
            sv_lbl.setText(txt)
            sv_lbl.setStyleSheet(f"color:{color}; background:transparent;")
        max_re = max(e.real for e in eigs)
        if max_re > 0:
            self.sv_ev_info.setText("⚠  Re(λ) > 0 → instabil!")
            self.sv_ev_info.setStyleSheet(
                f"color:{TUM_RED}; background:transparent; font-weight:bold;")
        elif any(abs(e.imag) > 1e-6 for e in eigs):
            self.sv_ev_info.setText("● Re(λ) < 0, Im ≠ 0 → gedämpfte Schwingung")
            self.sv_ev_info.setStyleSheet(
                f"color:{TUM_ORANGE}; background:transparent;")
        else:
            self.sv_ev_info.setText("● Re(λ) < 0 → stabil (aperiodisch)")
            self.sv_ev_info.setStyleSheet(
                f"color:{TUM_GREEN}; background:transparent;")

        # Zeitkonstante τ
        tau_vals = [-1/e.real for e in eigs if e.real < -1e-6]
        if tau_vals:
            tau_max = max(tau_vals)
            self.sv_tau.setText(
                f"τ_max = {tau_max:.2f} s  |  4τ ≈ {4*tau_max:.2f} s")
            self.sv_tau.setStyleSheet(f"color:{TEXT_DIM}; background:transparent;")
        else:
            self.sv_tau.setText("τ nicht definiert (instabil)")
            self.sv_tau.setStyleSheet(f"color:{TUM_RED}; background:transparent;")

        # Eigenlenkgradient EG → Unter-/Übersteuern
        lf, lr = self.LF, self.LR
        l = lf + lr
        EG = self.M / l**2 * (lf / CH - lr / CV)
        if EG < -0.002:
            txt, color = "▲  Übersteuern  (EG < 0)", TUM_RED
        elif EG > 0.002:
            txt, color = "▽  Untersteuern  (EG > 0)", "#89B4FA"
        else:
            txt, color = "●  Neutralsteuern  (EG ≈ 0)", TUM_GREEN
        self.lbl_steer.setText(txt)
        self.lbl_steer.setStyleSheet(
            f"color:{color}; background:transparent; font-weight:bold;")

    # ─────────────────────────────────────────────────────────────────────────
    def _redraw(self, delta, alpha_f, alpha_r, FYV, FYH, ay):
        lf, lr = self.LF, self.LR

        # ── Draufsicht ────────────────────────────────────────────────────────
        ax = self.ax_top
        ax.clear()
        ax.set_facecolor("#F0F2F5")

        _, v, CV, CH = self._get_params()
        ax.set_title(
            f"Draufsicht  |  v={v:.1f} m/s  "
            f"δ={np.rad2deg(delta):.1f}°  "
            f"β={np.rad2deg(self.beta):.1f}°  "
            f"θ̇={np.rad2deg(self.dtheta):.1f}°/s  "
            f"MV={FYV*lf:.0f}  MH={FYH*lr:.0f} Nm  "
            f"t={self.t:.1f}s",
            color=TEXT_LIGHT, fontsize=9, pad=6)
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")

        # Fahrspur (Farbverlauf)
        trail = list(zip(self.trail_x, self.trail_y))
        n = len(trail)
        if n > 1:
            seg = min(400, n - 1)
            for i in range(n - seg - 1, n - 1):
                a = 0.1 + 0.9 * (i - (n - seg - 1)) / seg
                ax.plot([trail[i][0], trail[i+1][0]],
                        [trail[i][1], trail[i+1][1]],
                        color=TUM_BLUE, alpha=a, lw=1.8)

        ax.plot(self.trail_x[0], self.trail_y[0], "o",
                color=TUM_GREEN, ms=7, zorder=4, label="Start")

        # Fahrzeug
        draw_vehicle(ax, self.x, self.y, self.theta,
                     self.beta, delta, alpha_f, alpha_r,
                     FYV, FYH, lf, lr, v=v, dtheta=self.dtheta)

        # Stationärer Kreis (Feature 3)
        if abs(self.dtheta) > 0.015:
            R_circ = v / self.dtheta
            cx_circ = self.x - R_circ * np.sin(self.theta)
            cy_circ = self.y + R_circ * np.cos(self.theta)
            circle = mpatches.Circle((cx_circ, cy_circ), abs(R_circ),
                                     fill=False, color=TUM_BLUE,
                                     lw=1.2, ls=":", alpha=0.35, zorder=2)
            ax.add_patch(circle)
            ax.plot(cx_circ, cy_circ, "+", color=TUM_BLUE,
                    ms=8, alpha=0.5, zorder=3)
            ax.text(cx_circ, cy_circ - abs(R_circ)*0.08,
                    f"R={abs(R_circ):.1f}m", fontsize=7, color=TUM_BLUE,
                    ha="center", va="top", alpha=0.7)

        # Kamera
        vr = max(18, min(80, n * 0.08 + 15))
        ax.set_xlim(self.x - vr, self.x + vr)
        ax.set_ylim(self.y - vr*0.6, self.y + vr*0.6)
        ax.set_aspect("equal", adjustable="box")

        self.canvas_top.draw_idle()

        # ── Zeitreihen ────────────────────────────────────────────────────────
        h = self._hist
        t = h["t"]

        def plot_sub(ax, keys, colors, labels, title, ylabel,
                     ss_vals=None, ss_labels=None):
            ax.clear()
            ax.set_facecolor("#F0F2F5")
            ax.set_title(title, color=TEXT_LIGHT, fontsize=8, pad=3)
            ax.set_ylabel(ylabel, color=TEXT_LIGHT, fontsize=7)
            ax.tick_params(labelsize=6, colors=TEXT_DIM)
            for k, c, lb in zip(keys, colors, labels):
                if h[k]:
                    ax.plot(t, h[k], color=c, lw=1.5, label=lb)
            ax.axhline(0, color=TEXT_DIM, lw=0.7, ls="--")
            # Stationäre Sollwerte als gestrichelte Linien
            if ss_vals:
                for val, c, lb in zip(ss_vals, colors, ss_labels or []):
                    if val is not None:
                        ax.axhline(val, color=c, lw=1.2, ls=":",
                                   label=f"{lb} stationär")
            ax.legend(fontsize=6, loc="upper left")

        # Stationäre Zielwerte (None wenn kein Lenksprung)
        ss_b  = np.rad2deg(self._ss_beta)   if self._ss_beta   is not None else None
        ss_dt = np.rad2deg(self._ss_dtheta) if self._ss_dtheta is not None else None

        plot_sub(self.ax_b1,
                 ["beta", "dtheta"], [TUM_ORANGE, TUM_GREEN],
                 ["β [°]", "θ̇ [°/s]"],
                 "Schwimmwinkel β & Gierrate θ̇", "°  /  °/s",
                 ss_vals=[ss_b, ss_dt], ss_labels=["β", "θ̇"])

        plot_sub(self.ax_b2,
                 ["alpha_f", "alpha_r"], [TUM_RED, "#FF7043"],
                 ["αV vorne [°]", "αH hinten [°]"],
                 "Schräglaufwinkel αV & αH", "°")

        plot_sub(self.ax_b3,
                 ["FYV", "FYH"], [PURPLE, "#89DCEB"],
                 ["FYV vorne [N]", "FYH hinten [N]"],
                 "Seitenkräfte FYV & FYH", "N")

        self.canvas_bot.draw_idle()

        # ── Reifenkennlinie aktualisieren ─────────────────────────────────────
        _, v, CV, CH = self._get_params()
        self._update_tire_canvas(alpha_f, alpha_r, FYV, FYH, CV, CH)

        # ── Kausalitäts-Tab aktualisieren ─────────────────────────────────────
        delta2, v2, CV2, CH2 = self._get_params()
        self._update_causal_tab(delta2, v2, CV2, CH2,
                                 alpha_f, alpha_r, FYV, FYH)

    # ─────────────────────────────────────────────────────────────────────────
    def _slider_changed(self):
        delta, v, CV, CH = self._get_params()
        self.vl_delta.setText(f"{np.rad2deg(delta):+.1f} °")
        self.vl_v.setText(    f"{v:.1f} m/s")
        self.vl_cv.setText(   f"{CV/1000:.0f} kN/rad")
        self.vl_ch.setText(   f"{CH/1000:.0f} kN/rad")

        # Eigenlenkgradient live aktualisieren
        lf, lr, l = self.LF, self.LR, self.LF + self.LR
        EG = self.M / l**2 * (lf / CH - lr / CV)
        if EG < -0.002:
            txt, color = "▲  Übersteuern  (EG < 0)", TUM_RED
        elif EG > 0.002:
            txt, color = "▽  Untersteuern  (EG > 0)", "#89B4FA"
        else:
            txt, color = "●  Neutralsteuern  (EG ≈ 0)", TUM_GREEN
        self.lbl_steer.setText(txt)
        self.lbl_steer.setStyleSheet(
            f"color:{color}; background:transparent; font-weight:bold;")

        # Eigenwerte live bei Slider-Änderung
        eigs = self._compute_eigenvalues(v, CV, CH)
        for sv_lbl, ev in zip((self.sv_ev1, self.sv_ev2), eigs):
            re, im = ev.real, ev.imag
            txt = (f"λ = {re:+.3f}  {im:+.3f}j"
                   if abs(im) > 1e-6 else f"λ = {re:+.3f}")
            color = TUM_RED if re > 0 else TUM_GREEN
            sv_lbl.setText(txt)
            sv_lbl.setStyleSheet(f"color:{color}; background:transparent;")

        # Zeitkonstante τ live
        tau_vals = [-1/e.real for e in eigs if e.real < -1e-6]
        if tau_vals:
            tau_max = max(tau_vals)
            self.sv_tau.setText(
                f"τ_max = {tau_max:.2f} s  |  4τ ≈ {4*tau_max:.2f} s")
            self.sv_tau.setStyleSheet(f"color:{TEXT_DIM}; background:transparent;")
        else:
            self.sv_tau.setText("τ nicht definiert (instabil)")
            self.sv_tau.setStyleSheet(f"color:{TUM_RED}; background:transparent;")

        if not self.running:
            # Stationäre Sollwerte zurücksetzen wenn Slider bewegt
            self._ss_beta = self._ss_dtheta = None
            alpha_f, alpha_r, FYV, FYH, ay = self._compute_derived(
                delta, v, CV, CH)
            self._redraw(delta, alpha_f, alpha_r, FYV, FYH, ay)

    # ─────────────────────────────────────────────────────────────────────────
    def _toggle(self):
        if self.running:
            self.timer.stop()
            self.running = False
            self.btn_go.setText("▶  Start")
            self.btn_go.setStyleSheet(BTN_CSS(TUM_BLUE))
        else:
            self.timer.start()
            self.running = True
            self.btn_go.setText("⏸  Pause")
            self.btn_go.setStyleSheet(BTN_CSS(TUM_ORANGE))

    def _reset(self):
        was = self.running
        if was:
            self._toggle()
        self.x = self.y = self.theta = self.dtheta = self.beta = self.t = 0.0

        self.trail_x = [0.0]
        self.trail_y = [0.0]
        self.trail_x = [0.0]; self.trail_y = [0.0]
        for k in self._hist:
            self._hist[k].clear()
        delta, v, CV, CH = self._get_params()
        self._redraw(delta, 0, 0, 0, 0, 0)
        if was:
            self._toggle()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = LinearSimWindow()
    win.show()
    sys.exit(app.exec())
