"""
========================================================
 Interaktives Koordinatentransformations-Tool
 Grundlagen Autonomer Fahrzeuge – TUM (Prof. Betz)
 Vorlesung 3: Koordinatensysteme & Transformation

 Streamlit-Version
 Starten lokal: streamlit run kosytrafo_streamlit.py
========================================================
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

# ── Page-Konfiguration ────────────────────────────────
st.set_page_config(
    page_title="Koordinatentransformation – TUM",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Farben ────────────────────────────────────────────
TUM_BLUE   = "#003070"
TUM_LIGHT  = "#5B8DB8"
TUM_ORANGE = "#E37222"
TUM_GREEN  = "#A2AD00"
TUM_RED    = "#8B0000"
TUM_PURPLE = "#5B0072"
TUM_GRAY   = "#606060"
TUM_LGRAY  = "#AAAAAA"
BG         = "#F0F4F8"
PANEL      = "#FFFFFF"

# ══════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ══════════════════════════════════════════════════════

def Rx(a):
    a = np.radians(a)
    return np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])

def Ry(a):
    a = np.radians(a)
    return np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])

def Rz(a):
    a = np.radians(a)
    return np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])

def R2(theta_deg):
    t = np.radians(theta_deg)
    return np.array([[np.cos(t), -np.sin(t)],
                     [np.sin(t),  np.cos(t)]])

def draw_frame_2d(ax, origin, angle_deg, color, label, scale=1.2, lw=2.5):
    R = R2(angle_deg)
    ex = R @ np.array([scale, 0])
    ey = R @ np.array([0, scale])
    ox, oy = origin
    for vec, lbl in [(ex, "X"), (ey, "Y")]:
        ax.annotate("", xy=(ox+vec[0], oy+vec[1]), xytext=(ox, oy),
                    arrowprops=dict(
                        arrowstyle="->, head_width=0.2, head_length=0.2",
                        color=color, lw=lw))
        ax.text(ox+vec[0]*1.18, oy+vec[1]*1.18,
                f"${lbl}_{{{label}}}$",
                color=color, fontsize=10, fontweight="bold",
                ha="center", va="center")
    ax.plot(ox, oy, "o", color=color, ms=8, zorder=6)
    ax.text(ox+0.05, oy-0.3, f"{{{label}}}",
            color=color, fontsize=9, ha="center")

def draw_angle_arc(ax, origin, angle_deg, color):
    if abs(angle_deg) < 1:
        return
    arc = mpatches.Arc(origin, 0.9, 0.9, angle=0,
                       theta1=min(0, angle_deg), theta2=max(0, angle_deg),
                       color=color, lw=1.8, linestyle=":")
    ax.add_patch(arc)
    mid_rad = np.radians(angle_deg / 2)
    ax.text(origin[0] + 0.7*np.cos(mid_rad),
            origin[1] + 0.7*np.sin(mid_rad),
            f"$\\theta={angle_deg:.0f}°$",
            fontsize=8, color=color, ha="center", va="center",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1))

def frame_3d(ax, R, t, color, label, scale=1.1):
    for vec, lbl, ls in [
        (R @ [scale, 0, 0], "X", "-"),
        (R @ [0, scale, 0], "Y", "--"),
        (R @ [0, 0, scale], "Z", ":"),
    ]:
        ax.quiver(*t, *vec, color=color,
                  arrow_length_ratio=0.25, linewidth=2.2, linestyle=ls)
        ax.text(*(t + np.array(vec)*1.25),
                f"{lbl}$_{{{label}}}$", color=color, fontsize=8)
    ax.scatter(*t, color=color, s=50, zorder=5)

def block(ax, x, y, lines, sz=9.5, dy=0.115):
    cy = y
    for txt, color, bold in lines:
        ax.text(x, cy, txt, transform=ax.transAxes,
                fontsize=sz, color=color, va="top",
                fontweight="bold" if bold else "normal",
                fontfamily="monospace")
        cy -= dy

# ══════════════════════════════════════════════════════
# SIDEBAR – SCHIEBEREGLER
# ══════════════════════════════════════════════════════

DEFAULTS = {
    "tx": 2.0, "ty": 1.5,
    "rot_z": 30, "rot_x": 0, "rot_y": 0,
    "px": 1.5,  "py": 1.0,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.sidebar.title("Schieberegler")

if st.sidebar.button("↺  Reset auf Standardwerte"):
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**📍 Translation (Verschiebung)**")
tx    = st.sidebar.slider("Δx", -5.0, 5.0, step=0.05, key="tx")
ty    = st.sidebar.slider("Δy", -5.0, 5.0, step=0.05, key="ty")

st.sidebar.markdown("---")
st.sidebar.markdown("**🔄 Rotation – Yaw / Gieren**")
rot_z = st.sidebar.slider("Yaw  θz (°)", -180, 180, step=1, key="rot_z")

st.sidebar.markdown("---")
st.sidebar.markdown("**🔄 Rotation 3D – Roll / Pitch**")
rot_x = st.sidebar.slider("Roll   θx (°)", -180, 180, step=1, key="rot_x")
rot_y = st.sidebar.slider("Pitch θy (°)", -180, 180, step=1, key="rot_y")

st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Messpunkt P (in KoSy B)**")
px    = st.sidebar.slider("Px", -4.0, 5.0, step=0.05, key="px")
py    = st.sidebar.slider("Py", -4.0, 5.0, step=0.05, key="py")

# ══════════════════════════════════════════════════════
# SEITENTITEL
# ══════════════════════════════════════════════════════

st.markdown(
    "<h2 style='text-align:center; color:#003070; margin-bottom:0;'>"
    "Koordinatentransformation &nbsp;|&nbsp; GAV Vorlesung 3 – TUM (Prof. Betz)"
    "</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center; color:#606060; margin-top:2px;'>"
    "Schieberegler (links) verstellen → Plots und Matrizen aktualisieren sich live"
    "</p>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════
# FIGURE AUFBAUEN
# ══════════════════════════════════════════════════════

fig = plt.figure(figsize=(14, 9), facecolor=BG)

main_gs = gridspec.GridSpec(
    2, 2,
    left=0.04, right=0.98,
    top=0.96, bottom=0.04,
    hspace=0.30, wspace=0.22,
    height_ratios=[1.8, 1],
    width_ratios=[1.3, 1.7],
)

ax_2d  = fig.add_subplot(main_gs[0, 0])
ax_3d  = fig.add_subplot(main_gs[0, 1], projection="3d")
ax_mat = fig.add_subplot(main_gs[1, 0])
ax_leg = fig.add_subplot(main_gs[1, 1])

for ax, fc in [(ax_2d, PANEL), (ax_mat, PANEL), (ax_leg, PANEL)]:
    ax.set_facecolor(fc)

# ── 2D-PLOT ───────────────────────────────────────────
lim = 7
ax_2d.set_xlim(-lim, lim)
ax_2d.set_ylim(-lim+1, lim)
ax_2d.set_aspect("equal")
ax_2d.grid(True, alpha=0.2, color=TUM_LGRAY, lw=0.6)
ax_2d.axhline(0, color=TUM_LGRAY, lw=0.8, alpha=0.5)
ax_2d.axvline(0, color=TUM_LGRAY, lw=0.8, alpha=0.5)
ax_2d.set_title(
    "2D-Ansicht  –  KoSy A (Welt-Frame)  →  KoSy B (Sensor/Fahrzeug-Frame)",
    fontsize=9.5, fontweight="bold", color=TUM_BLUE, pad=6,
)

draw_frame_2d(ax_2d, (0, 0), 0, TUM_BLUE, "A", scale=1.3, lw=3)

origin_B = np.array([tx, ty])
draw_frame_2d(ax_2d, origin_B, rot_z, TUM_ORANGE, "B", scale=1.3, lw=3)

ax_2d.annotate("", xy=origin_B, xytext=(0, 0),
               arrowprops=dict(
                   arrowstyle="->, head_width=0.18, head_length=0.18",
                   color=TUM_GREEN, lw=2.0, linestyle="dashed"))
mid = origin_B / 2
ax_2d.text(mid[0]+0.15, mid[1]+0.22,
           f"$^A D_B = [{tx:.1f},\\ {ty:.1f}]^T$",
           fontsize=8, color=TUM_GREEN, ha="center",
           bbox=dict(facecolor="white", edgecolor=TUM_GREEN,
                     alpha=0.8, pad=2, boxstyle="round,pad=0.2"))

draw_angle_arc(ax_2d, tuple(origin_B), rot_z, TUM_ORANGE)

Rm     = R2(rot_z)
p_B_v  = np.array([px, py])
p_world = origin_B + Rm @ p_B_v

ax_2d.annotate("", xy=p_world, xytext=origin_B,
               arrowprops=dict(
                   arrowstyle="->, head_width=0.15, head_length=0.15",
                   color=TUM_RED, lw=1.5, linestyle="dotted"))
ax_2d.plot(*p_world, "D", color=TUM_RED, ms=10, zorder=7)
ax_2d.plot([p_world[0], p_world[0]], [0, p_world[1]],
           ":", color=TUM_BLUE, lw=0.9, alpha=0.45)
ax_2d.plot([0, p_world[0]], [p_world[1], p_world[1]],
           ":", color=TUM_BLUE, lw=0.9, alpha=0.45)
ax_2d.text(p_world[0]+0.18, p_world[1]+0.25,
           f"$^AP=[{p_world[0]:.2f},\\ {p_world[1]:.2f}]^T$",
           fontsize=8.5, color=TUM_BLUE, fontweight="bold",
           bbox=dict(facecolor="#EEF4FF", edgecolor=TUM_BLUE,
                     alpha=0.9, pad=2, boxstyle="round,pad=0.3"))
ax_2d.text(0.5, 0.02,
           r"$^AP = R(\theta)\cdot\,^BP + D_B$",
           transform=ax_2d.transAxes, fontsize=9,
           ha="center", va="bottom", color=TUM_PURPLE,
           bbox=dict(facecolor="#F4EEFF", edgecolor=TUM_PURPLE,
                     alpha=0.85, pad=3, boxstyle="round,pad=0.3"))
ax_2d.set_xlabel("X", fontsize=9, color=TUM_GRAY)
ax_2d.set_ylabel("Y", fontsize=9, color=TUM_GRAY)

# ── 3D-PLOT ───────────────────────────────────────────
ax_3d.set_title("3D-Ansicht  –  Roll / Pitch / Yaw",
                fontsize=9.5, fontweight="bold", color=TUM_BLUE, pad=6)
ax_3d.set_xlim(-3, 6); ax_3d.set_ylim(-3, 6); ax_3d.set_zlim(-2, 4)
ax_3d.set_xlabel("X", fontsize=8, labelpad=1)
ax_3d.set_ylabel("Y", fontsize=8, labelpad=1)
ax_3d.set_zlabel("Z", fontsize=8, labelpad=1)
ax_3d.tick_params(labelsize=7, pad=1)
ax_3d.grid(True, alpha=0.15)
ax_3d.set_facecolor("#F8F9FF")

frame_3d(ax_3d, np.eye(3), np.zeros(3), TUM_BLUE, "A")

R_total = Rz(rot_z) @ Ry(rot_y) @ Rx(rot_x)
t_B     = np.array([tx, ty, 0.0])
ax_3d.quiver(0, 0, 0, *t_B, color=TUM_GREEN, alpha=0.7,
             arrow_length_ratio=0.12, linewidth=1.8, linestyle="--")
frame_3d(ax_3d, R_total, t_B, TUM_ORANGE, "B")

p_B3 = np.array([px, py, 0.0])
p_A3 = R_total @ p_B3 + t_B
ax_3d.scatter(*p_A3, color=TUM_RED, s=90, zorder=6)
ax_3d.text(p_A3[0]+0.1, p_A3[1]+0.1, p_A3[2]+0.1,
           f"P\n[{p_A3[0]:.1f},{p_A3[1]:.1f},{p_A3[2]:.1f}]",
           fontsize=7, color=TUM_RED)

# ── MATRIZEN (2×2) ────────────────────────────────────
ax_mat.axis("off")
ax_mat.set_title("Formeln & Matrizen", fontsize=10,
                 fontweight="bold", color=TUM_BLUE, pad=5)

c_z  = np.cos(np.radians(rot_z))
s_z  = np.sin(np.radians(rot_z))
p_A_v = R2(rot_z) @ p_B_v + np.array([tx, ty])

block(ax_mat, 0.03, 0.92, [
    ("R(θz) =",                          TUM_ORANGE, True),
    (f"[ {c_z:+.3f}  {-s_z:+.3f} ]",    TUM_ORANGE, False),
    (f"[ {s_z:+.3f}   {c_z:+.3f} ]",    TUM_ORANGE, False),
])
block(ax_mat, 0.53, 0.92, [
    ("Translation D_B =",                TUM_GREEN, True),
    (f"[ {tx:+.3f} ]",                   TUM_GREEN, False),
    (f"[ {ty:+.3f} ]",                   TUM_GREEN, False),
])
block(ax_mat, 0.03, 0.44, [
    ("Punkt-Transformation:",             TUM_RED,    True),
    (f"ᴮP = [{px:.2f}, {py:.2f}]ᵀ",     "#333333",  False),
    ("ᴬP  = R · ᴮP + D_B",              "#333333",  False),
    (f"ᴬPx = {p_A_v[0]:+.4f}",          TUM_BLUE,   False),
    (f"ᴬPy = {p_A_v[1]:+.4f}",          TUM_BLUE,   False),
])
block(ax_mat, 0.53, 0.44, [
    ("Homogene Matrix H:",                TUM_PURPLE, True),
    (f"[ {c_z:+.3f} {-s_z:+.3f} {tx:+.2f} ]", TUM_PURPLE, False),
    (f"[ {s_z:+.3f}  {c_z:+.3f} {ty:+.2f} ]",  TUM_PURPLE, False),
    ("[ 0.000  0.000  1.000 ]",          TUM_PURPLE, False),
])

# ── LEGENDE ───────────────────────────────────────────
ax_leg.axis("off")
ax_leg.set_title("Legende – Farben, Symbole & Bedeutung",
                 fontsize=10, fontweight="bold", color=TUM_BLUE, pad=5)

legend_items = [
    (TUM_BLUE,   "o", "KoSy A – Welt-Frame",
     "Inertialsystem, global fixiert. Alle absoluten",
     "Koordinaten werden in diesem Frame angegeben."),
    (TUM_ORANGE, "o", "KoSy B – Fahrzeug-/Sensor-Frame",
     "Bewegt sich relativ zu A. Lage durch",
     "Translation D_B und Rotation θz definiert."),
    (TUM_GREEN,  "s", "Translation D_B  (grün, gestrichelt)",
     "Verschiebungsvektor vom Ursprung A zum",
     "Ursprung B, ausgedrückt in Weltkoordinaten."),
    (TUM_RED,    "D", "Punkt P – Messpunkt  (rot, Raute)",
     "Im Sensor-Frame B gemessen (ᴮP). Über",
     "ᴬP = R·ᴮP + D_B in Weltkoord. transformiert."),
    (TUM_PURPLE, "s", "Homogene Matrix H  (lila)",
     "Fasst Rotation R und Translation t zusammen:",
     "ᴬP = H · [ᴮP; 1]ᵀ   mit H = [R|t; 0|1]."),
]

col_x    = [0.02, 0.51]
sym_dx   = 0.035
txt_dx   = 0.075
y_start  = 0.87
dy_title = 0.090
dy_expl  = 0.056

for i, (color, marker, titel, expl1, expl2) in enumerate(legend_items):
    col = i % 2
    row = i // 2
    cx  = col_x[col]
    cy  = y_start - row * (dy_title + 2*dy_expl + 0.025)

    ax_leg.plot(cx + sym_dx, cy + 0.005, marker,
                transform=ax_leg.transAxes,
                color=color, ms=9, clip_on=False, markeredgewidth=0)
    ax_leg.text(cx + txt_dx, cy, titel,
                transform=ax_leg.transAxes,
                fontsize=8.2, color=color, va="top", fontweight="bold")
    ax_leg.text(cx + txt_dx, cy - dy_expl, expl1,
                transform=ax_leg.transAxes,
                fontsize=7.7, color=TUM_GRAY, va="top")
    ax_leg.text(cx + txt_dx, cy - 2*dy_expl, expl2,
                transform=ax_leg.transAxes,
                fontsize=7.7, color=TUM_GRAY, va="top")

# ── AUSGABE ───────────────────────────────────────────
st.pyplot(fig, use_container_width=True)
plt.close(fig)
