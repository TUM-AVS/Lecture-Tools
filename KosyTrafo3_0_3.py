import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider, Button, RadioButtons
from matplotlib.patches import FancyBboxPatch, Arc

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
BOX_TRANS  = "#E8F4E8"
BOX_ROT    = "#FFF3E0"
BOX_PNT    = "#FCE8E8"
PANEL_INFO = "#EEF3F9"
# Modusspezifische Hintergrundfarben
BG_AKTIV      = "#FFF8F0"   # warmes Orange → Punkt bewegt sich
BG_PASSIV     = "#F0F8FF"   # kühles Blau  → KoSy dreht sich
BG_VERGLEICH  = "#F0FFF4"   # helles Pastellgrün → Vergleichsmodus

# ── Hilfsfunktionen Rotation ──────────────────────────
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

# ── Koordinatensystem 2D zeichnen ────────────────────
def draw_frame_2d(ax, origin, angle_deg, color, label, scale=1.2, lw=2.5, alpha=1.0):
    R = R2(angle_deg)
    ex = R @ np.array([scale, 0])
    ey = R @ np.array([0, scale])
    ox, oy = origin

    for vec, lbl in [(ex, "X"), (ey, "Y")]:
        ax.annotate("", xy=(ox+vec[0], oy+vec[1]), xytext=(ox, oy),
                    arrowprops=dict(
                        arrowstyle="->, head_width=0.2, head_length=0.2",
                        color=color, lw=lw, alpha=alpha))
        ax.text(ox+vec[0]*1.18, oy+vec[1]*1.18,
                f"${lbl}_{{{label}}}$",
                color=color, fontsize=10, fontweight="bold",
                ha="center", va="center", alpha=alpha)

    ax.plot(ox, oy, "o", color=color, ms=8, zorder=6, alpha=alpha)
    ax.text(ox+0.05, oy-0.3, f"{{{label}}}",
            color=color, fontsize=9, ha="center", alpha=alpha)

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

def draw_quiver(ax, ox, oy, dx, dy, color, lw=2.0, ls="-", alpha=1.0, label=""):
    ax.quiver(ox, oy, dx, dy,
              angles="xy", scale_units="xy", scale=1,
              color=color, width=0.008,
              headwidth=4.5, headlength=6, headaxislength=5,
              linewidth=lw, linestyle=ls, alpha=alpha,
              label=label, zorder=4)

# ══════════════════════════════════════════════════════
class TransformationTool:

    def __init__(self):
        self.tx    = 2.0
        self.ty    = 1.5
        self.rot_z = 30.0
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.px    = 1.0
        self.py    = 0.8
        self.mode  = "Passiv"   # "Aktiv" | "Passiv" | "Vergleich"
        self._cmp_axes  = []
        self._cmp_title = None

        self._build_layout()
        self._build_sliders()
        self._update(None)

    def _build_layout(self):
        self.fig = plt.figure(figsize=(17, 10), facecolor=BG)
        try:
            self.fig.canvas.manager.set_window_title(
                "GAV Vorlesung 3 – Koordinatentransformation v3 (Aktiv / Passiv)")
        except Exception:
            pass

        main_gs = gridspec.GridSpec(
            2, 3,
            left=0.02, right=0.99,
            top=0.93, bottom=0.03,
            hspace=0.30, wspace=0.22,
            height_ratios=[1.85, 1],
            width_ratios=[1.45, 1.45, 0.82]
        )

        self.ax_2d  = self.fig.add_subplot(main_gs[0, 0])
        self.ax_3d  = self.fig.add_subplot(main_gs[0, 1], projection="3d")
        self.ax_mat = self.fig.add_subplot(main_gs[1, 0])
        self.ax_leg = self.fig.add_subplot(main_gs[1, 1:])

        # Slider-Hintergrund
        self.ax_slider_bg = self.fig.add_subplot(main_gs[0, 2])
        self.ax_slider_bg.set_facecolor(PANEL_INFO)
        self.ax_slider_bg.axis("off")

        for ax, fc in [(self.ax_2d, PANEL), (self.ax_mat, PANEL),
                       (self.ax_leg, PANEL)]:
            ax.set_facecolor(fc)

        self.fig.text(0.50, 0.968,
            "Koordinatentransformation  |  GAV Vorlesung 3",
            ha="center", fontsize=13, fontweight="bold", color=TUM_BLUE)

    # ─────────────────────────────────────────────────
    def _build_sliders(self):
        fig = self.fig
        pos = self.ax_slider_bg.get_position()
        x0  = pos.x0 + 0.010
        x1  = pos.x1 - 0.008
        sw  = x1 - x0
        sh  = 0.022
        gap = 0.010
        grp = 0.018


        def sl(y, label, vmin, vmax, vinit, color):
            ax = fig.add_axes([x0, y, sw, sh], facecolor=color)
            s  = Slider(ax, label, vmin, vmax, valinit=vinit,
                        color=TUM_BLUE, track_color="#C8D8EC")
            s.label.set_fontsize(8.5)
            s.valtext.set_fontsize(8.5)
            s.on_changed(self._update)
            return s

        # ── Preset-Buttons (Szenarien) ──
        y_preset  = pos.y0 + 0.008
        preset_bw = sw / 4 - 0.003
        preset_h  = 0.022
        preset_labels = ["Nur Transl.", "45° Yaw", "Rot+Transl.", "Gegenrot."]
        preset_vals = [
            dict(tx=2.0, ty=1.0, rz=0,   rx=0, ry=0, px=0.5, py=0.5),
            dict(tx=0.0, ty=0.0, rz=45,  rx=0, ry=0, px=1.0, py=0.0),
            dict(tx=1.5, ty=0.8, rz=30,  rx=0, ry=0, px=0.5, py=0.3),
            dict(tx=0.0, ty=0.0, rz=-45, rx=0, ry=0, px=1.0, py=0.0),
        ]
        self.btn_presets = []
        for i, (lbl, pv) in enumerate(zip(preset_labels, preset_vals)):
            bx = x0 + i * (preset_bw + 0.003)
            ax_p = fig.add_axes([bx, y_preset, preset_bw, preset_h],
                                 facecolor="#E0E8F0")
            btn = Button(ax_p, lbl, color="#E0E8F0")
            btn.label.set_fontsize(7.5)
            btn.on_clicked(lambda event, v=pv: self._apply_preset(**v))
            self.btn_presets.append(btn)

        # SZENARIEN-Label: zentriert zwischen Preset-Buttons und Reset-Button
        y_sz_label = y_preset + preset_h + 0.003
        fig.text((x0 + x1) / 2, y_sz_label,
                 "── Szenarien ──",
                 ha="center", va="bottom", fontsize=7,
                 color=TUM_GRAY)

        # Reset-Button (oberhalb des SZENARIEN-Labels)
        y_reset = y_sz_label + 0.014
        ax_reset = fig.add_axes([x0 + sw*0.15, y_reset, sw*0.70, 0.024])
        self.btn_reset = Button(ax_reset, "↺  Reset", color="#DDDDDD")
        self.btn_reset.label.set_fontsize(9)
        self.btn_reset.on_clicked(self._reset)

        # ── Messpunkt ──
        y = y_reset + 0.024 + 0.010
        fig.text(x0, y + 2*(sh+gap) + 0.005,
                 "MESSPUNKT  (in KoSy B / Welt)", fontsize=8,
                 fontweight="bold", color=TUM_RED)
        self.s_py = sl(y,            "Py", -1.5, 1.5, self.py, BOX_PNT)
        self.s_px = sl(y + sh + gap, "Px", -1.5, 1.5, self.px, BOX_PNT)
        y += 2*(sh+gap) + grp + 0.025

        # ── Rotation 3D ──
        fig.text(x0, y + 2*(sh+gap) + 0.005,
                 "ROTATION  (3D: Roll / Pitch)", fontsize=8,
                 fontweight="bold", color=TUM_ORANGE)
        self.s_rx = sl(y,            "Roll  θx", -180, 180, self.rot_x, BOX_ROT)
        self.s_ry = sl(y + sh + gap, "Pitch θy", -180, 180, self.rot_y, BOX_ROT)
        y += 2*(sh+gap) + grp + 0.010

        # ── Rotation 2D/Yaw ──
        fig.text(x0, y + sh + gap + 0.005,
                 "ROTATION  (Yaw / Gieren)", fontsize=8,
                 fontweight="bold", color=TUM_GREEN)
        self.s_rz = sl(y, "Yaw  θz", -180, 180, self.rot_z, BOX_ROT)
        y += sh + gap + grp + 0.010

        # ── Translation ──
        fig.text(x0, y + 2*(sh+gap) + 0.005,
                 "TRANSLATION  (Verschiebung)", fontsize=8,
                 fontweight="bold", color=TUM_GREEN)
        self.s_ty = sl(y,            "Δy", -5, 5, self.ty, BOX_TRANS)
        self.s_tx = sl(y + sh + gap, "Δx", -5, 5, self.tx, BOX_TRANS)
        y += 2*(sh+gap) + grp + 0.015

        # ══════════════════════════════════════════════
        # AKTIV / PASSIV  Radio-Button  (prominente Box)
        # ══════════════════════════════════════════════
        radio_h = 0.092
        radio_y = y
        ax_radio = fig.add_axes([x0, radio_y, sw, radio_h],
                                facecolor="#E8F0FC")
        ax_radio.set_title("Transformations-Modus", fontsize=8.5,
                            fontweight="bold", color=TUM_BLUE, pad=3)

        self.radio = RadioButtons(
            ax_radio,
            ("Passiv  (KoSy dreht sich)", "Aktiv  (Punkt dreht sich)",
             "Vergleich (Aktiv | Passiv)"),
            active=0,
            activecolor=TUM_BLUE,
        )
        for lbl in self.radio.labels:
            lbl.set_fontsize(9)
        self.radio.on_clicked(self._on_mode_change)

    # ─────────────────────────────────────────────────
    def _on_mode_change(self, label):
        if "Aktiv" in label and "Vergleich" not in label:
            self.mode = "Aktiv"
        elif "Vergleich" in label:
            self.mode = "Vergleich"
        else:
            self.mode = "Passiv"
        self._update(None)

    # ─────────────────────────────────────────────────
    def _cleanup_cmp(self):
        """Vergleich-Axes und Titel entfernen."""
        for a in self._cmp_axes:
            try:
                a.remove()
            except Exception:
                pass
        self._cmp_axes = []
        if self._cmp_title is not None:
            try:
                self._cmp_title.remove()
            except Exception:
                pass
            self._cmp_title = None

    # ─────────────────────────────────────────────────
    def _update(self, val):
        self.tx    = self.s_tx.val
        self.ty    = self.s_ty.val
        self.rot_z = self.s_rz.val
        self.rot_x = self.s_rx.val
        self.rot_y = self.s_ry.val
        self.px    = self.s_px.val
        self.py    = self.s_py.val
        # Hintergrundfarbe je nach Modus
        if self.mode == "Aktiv":
            bg = BG_AKTIV
        elif self.mode == "Passiv":
            bg = BG_PASSIV
        else:
            bg = BG_VERGLEICH
        self.fig.set_facecolor(bg)
        self._draw_2d()
        if self.mode != "Vergleich":
            self._draw_3d()
            self._draw_matrix()
            self._draw_legend()
        self.fig.canvas.draw_idle()

    # ─────────────────────────────────────────────────
    #  2D-PLOT  (modusabhängig)
    # ─────────────────────────────────────────────────
    def _draw_2d(self):
        ax = self.ax_2d

        Rm = R2(self.rot_z)
        origin_B = np.array([self.tx, self.ty])
        p_world_start = np.array([self.px, self.py])

        if self.mode == "Aktiv":
            self._cleanup_cmp()
            self.ax_3d.set_visible(True)
            self.ax_mat.set_visible(True)
            self.ax_leg.set_visible(True)
            ax.set_visible(True)
            ax.cla()
            ax.set_facecolor(PANEL)
            lim = 1.5
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.75)
            ax.axhline(0, color="0.25", linewidth=1.0)
            ax.axvline(0, color="0.25", linewidth=1.0)
            ax.set_xlabel("Welt-x", fontsize=9)
            ax.set_ylabel("Welt-y", fontsize=9)
            self._draw_2d_aktiv(ax, Rm, origin_B, p_world_start)

        elif self.mode == "Passiv":
            self._cleanup_cmp()
            self.ax_3d.set_visible(True)
            self.ax_mat.set_visible(True)
            self.ax_leg.set_visible(True)
            ax.set_visible(True)
            ax.cla()
            ax.set_facecolor(PANEL)
            lim = 1.5
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.75)
            ax.axhline(0, color="0.25", linewidth=1.0)
            ax.axvline(0, color="0.25", linewidth=1.0)
            ax.set_xlabel("Welt-x", fontsize=9)
            ax.set_ylabel("Welt-y", fontsize=9)
            self._draw_2d_passiv(ax, Rm, p_world_start)

        else:  # Vergleich – nur Slider + 2 große 2D-Plots
            self._cleanup_cmp()
            ax.set_visible(False)
            self.ax_3d.set_visible(False)
            self.ax_mat.set_visible(False)
            self.ax_leg.set_visible(False)

            # Gesamtfläche: von ax_2d (links) bis ax_3d (rechts),
            # von ax_mat (unten) bis ax_2d (oben)
            pos_2d  = self.ax_2d.get_position()
            pos_3d  = self.ax_3d.get_position()
            pos_mat = self.ax_mat.get_position()

            x0_big = pos_2d.x0
            x1_big = pos_3d.x1
            y0_big = pos_mat.y0
            y1_big = pos_2d.y1

            total_w = x1_big - x0_big
            total_h = y1_big - y0_big
            gap = 0.018
            half_w = (total_w - gap) / 2

            ax_p = self.fig.add_axes([x0_big,              y0_big, half_w, total_h], facecolor=PANEL)
            ax_a = self.fig.add_axes([x0_big + half_w + gap, y0_big, half_w, total_h], facecolor=PANEL)
            self._cmp_axes = [ax_p, ax_a]

            lim = 1.5
            for a in self._cmp_axes:
                a.set_xlim(-lim, lim)
                a.set_ylim(-lim, lim)
                a.set_aspect("equal", adjustable="box")
                a.grid(True, linestyle=":", linewidth=0.8, alpha=0.75)
                a.axhline(0, color="0.25", linewidth=1.0)
                a.axvline(0, color="0.25", linewidth=1.0)
                a.set_xlabel("Welt-x", fontsize=9)
                a.set_ylabel("Welt-y", fontsize=9)

            self._draw_2d_passiv(ax_p, Rm, p_world_start)
            self._draw_2d_aktiv(ax_a, Rm, origin_B, p_world_start)

            # Titel zentriert über beiden Plots
            mid_x = x0_big + total_w / 2
            self._cmp_title = self.fig.text(
                mid_x, y1_big + 0.005,
                "◀  PASSIV  |  AKTIV  ▶",
                ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=TUM_BLUE
            )

    # ---- AKTIV: gleicher Stil wie Passiv-Referenzbild ----
    def _draw_2d_aktiv(self, ax, Rm, origin_B, p_start):
        """
        Aktiver Plot im gleichen clean Stil wie das Passiv-Referenzbild:
          - Schwarze Weltachsen vom Ursprung
          - Blauer Originalvektor p (fix im KoSy, wird gleich gedreht)
          - Roter rotierter Vektor p' = R·p
          - Gestrichelter Bogenpfeil p→p' (physische Bewegung)
          - Winkel-Arc θ in Rot (der Punkt dreht sich, nicht das KoSy)
          - Koordinaten-Box unten links
          - Legende oben links
        KoSy bleibt fix → kein grünes lokales KoSy.
        """
        theta = self.rot_z
        sign  = "+" if theta >= 0 else ""
        ax.set_title(
            f"Aktiv: Vektor wird um ${sign}{theta:.0f}°$ gedreht, KoSy bleibt fix",
            fontsize=11, pad=12)

        # ── Schwarze Weltachsen ───────────────────────
        scale_world = 1.15
        draw_quiver(ax, 0, 0, scale_world, 0, "black", lw=2.5, label="_nolegend_")
        draw_quiver(ax, 0, 0, 0, scale_world, "black", lw=2.5, label="_nolegend_")
        ax.text(scale_world + 0.05, -0.05, "Welt-x", fontsize=9, ha="left", va="top")
        ax.text(0.04, scale_world + 0.06, "Welt-y", fontsize=9, ha="left", va="bottom")

        # ── Originalvektor p (blau, gestrichelt/transparent) ─
        p0 = p_start
        norm = np.linalg.norm(p0)
        if norm < 1e-6:
            p0 = np.array([1.0, 0.0])   # Fallback

        draw_quiver(ax, 0, 0, p0[0], p0[1],
                    "tab:blue", lw=2.5, ls="--", alpha=0.55,
                    label=r"${}^W p$ (original)")
        ax.text(p0[0] + 0.03, p0[1] + 0.05,
                r"${}^W p$", color="tab:blue", fontsize=12, alpha=0.7,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))

        # ── Rotierter Vektor p' = R·p (rot) ──────────
        p_rot = Rm @ p0
        draw_quiver(ax, 0, 0, p_rot[0], p_rot[1],
                    "tab:red", lw=2.5,
                    label=r"${}^W p' = R(\theta)\,{}^W p$")
        ax.text(p_rot[0] + 0.03, p_rot[1] + 0.05,
                r"${}^W p'$", color="tab:red", fontsize=12,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))

        # ── Gebogener Bewegungspfeil p→p' ────────────
        # Manuelle Bogen-Annotation zwischen Vektorspitzen
        ax.annotate("",
                    xy=(p_rot[0], p_rot[1]),
                    xytext=(p0[0], p0[1]),
                    arrowprops=dict(
                        arrowstyle="->, head_width=0.25, head_length=0.25",
                        color="tab:red", lw=1.8, alpha=0.6,
                        connectionstyle="arc3,rad=0.30"))

        # ── Winkel-Arc (rot, zwischen p und p') ──────
        if abs(theta) >= 1:
            r_arc = max(norm * 0.38, 0.22)
            angle_start = np.degrees(np.arctan2(p0[1], p0[0]))
            t1 = angle_start + min(0, theta)
            t2 = angle_start + max(0, theta)
            arc = Arc((0, 0), 2*r_arc, 2*r_arc, theta1=t1, theta2=t2,
                      color="tab:red", linewidth=1.8, zorder=5)
            ax.add_patch(arc)
            mid_rad = np.radians(angle_start + theta / 2)
            sign_str = "+" if theta >= 0 else ""
            ax.text((r_arc + 0.08) * np.cos(mid_rad),
                    (r_arc + 0.08) * np.sin(mid_rad),
                    f"${sign_str}{theta:.0f}°$",
                    color="tab:red", fontsize=11, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15",
                              facecolor="white", edgecolor="none", alpha=0.85))

        # ── Hilfslinie: Radiuslinien zu p und p' ─────
        ax.plot([0, p0[0]], [0, p0[1]],
                color="0.75", linewidth=0.8, linestyle=":", zorder=1)
        ax.plot([0, p_rot[0]], [0, p_rot[1]],
                color="0.75", linewidth=0.8, linestyle=":", zorder=1)

        # ── "KoSy bleibt fix" Hinweis ─────────────────
        ax.text(0.5, 0.02,
                "KoSy bleibt fix  –  Vektor bewegt sich!",
                color="tab:red", fontsize=9, ha="center", va="bottom",
                transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="tab:red", alpha=0.85))

        # ── Koordinaten-Box ───────────────────────────
        coord_x = -1.42
        coord_y = -1.10
        ax.text(coord_x, coord_y,
                f"${{}}^W p = \\binom{{{p0[0]:.3f}}}{{{p0[1]:.3f}}}$"
                f"     ${{}}^W p' = \\binom{{{p_rot[0]:.3f}}}{{{p_rot[1]:.3f}}}$",
                fontsize=10,
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="white", edgecolor="0.78"))

        # ── Legende ───────────────────────────────────
        handles, labels = ax.get_legend_handles_labels()
        filtered = [(h, l) for h, l in zip(handles, labels)
                    if not l.startswith("_")]
        ax.legend([h for h, _ in filtered], [l for _, l in filtered],
                  loc="upper left", frameon=True, fontsize=9,
                  borderpad=0.35, labelspacing=0.35,
                  handlelength=1.6, handletextpad=0.55, borderaxespad=0.35)

    # ---- PASSIV: exakt im Stil des Referenzbildes ----
    def _draw_2d_passiv(self, ax, Rm, p_world):
        """
        Passiver Plot 1:1 nach Referenzbild:
          - Schwarze Weltachsen vom Ursprung (Pfeile)
          - Grüne lokale Achsen (L-x, L-y) vom Ursprung (kein Translation)
          - Blauer Vektor p (geometrisch fix)
          - Orange Komponentenpfeile entlang lokaler Achsen
          - Winkel-Arc mit θ-Label
          - Koordinaten-Box unten links
          - Legende oben links
        Lokales KoSy dreht sich um den Ursprung (tx=0, ty=0 implizit für
        die reine Visualisierung; Translation weiterhin in 3D/Formeln sichtbar).
        """
        theta = self.rot_z

        # Titel im Stil des Referenzbildes
        sign = "+" if theta >= 0 else ""
        ax.set_title(
            f"Passiv: lokales KoSy ist um ${sign}{theta:.0f}°$ gegen Welt gedreht",
            fontsize=11, pad=12)

        # ── Schwarze Weltachsen ───────────────────────
        scale_world = 1.15
        draw_quiver(ax, 0, 0, scale_world, 0, "black", lw=2.5, label="_nolegend_")
        draw_quiver(ax, 0, 0, 0, scale_world, "black", lw=2.5, label="_nolegend_")
        ax.text(scale_world + 0.05, -0.05, "Welt-x", fontsize=9, ha="left", va="top")
        ax.text(0.04, scale_world + 0.06, "Welt-y", fontsize=9, ha="left", va="bottom")

        # ── Lokale Achsen (grün) ──────────────────────
        local_x = Rm @ np.array([1.0, 0.0])
        local_y = Rm @ np.array([0.0, 1.0])
        scale_local = 1.18
        draw_quiver(ax, 0, 0,
                    scale_local * local_x[0], scale_local * local_x[1],
                    "forestgreen", lw=2.5, label="lokale Achsen")
        draw_quiver(ax, 0, 0,
                    scale_local * local_y[0], scale_local * local_y[1],
                    "forestgreen", lw=2.5, label="_nolegend_")
        lx_tip = 1.24 * local_x
        ly_tip = 1.24 * local_y
        ax.text(lx_tip[0], lx_tip[1], "L-x",
                color="forestgreen", fontsize=12, ha="center", va="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))
        ax.text(ly_tip[0], ly_tip[1], "L-y",
                color="forestgreen", fontsize=12, ha="center", va="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))

        # ── Lokales Koordinatengitter ─────────────────
        t_vals = np.array([-3.0, 3.0])
        for k in np.arange(-3.0, 3.1, 0.5):
            p1 = k * local_x + t_vals[0] * local_y
            p2 = k * local_x + t_vals[1] * local_y
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                    color="forestgreen", alpha=0.13, lw=0.65, zorder=0)
            p1 = k * local_y + t_vals[0] * local_x
            p2 = k * local_y + t_vals[1] * local_x
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                    color="forestgreen", alpha=0.13, lw=0.65, zorder=0)

        # ── Blauer geometrischer Vektor p ─────────────
        p_w = p_world
        draw_quiver(ax, 0, 0, p_w[0], p_w[1],
                    "tab:blue", lw=2.5, label=r"geometrischer Vektor $p$")
        ax.text(p_w[0] + 0.03, p_w[1] - 0.07,
                r"${}^W p$", color="tab:blue", fontsize=12,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))

        # ── Koordinaten im lokalen System ─────────────
        # ᴸp = Rᵀ · p_world  (Ursprung bei 0,0 — reine Rotation)
        p_local = Rm.T @ p_w
        comp_x = p_local[0] * local_x   # Vektor entlang L-x mit Länge comp_x
        comp_y = p_local[1] * local_y   # Vektor entlang L-y mit Länge comp_y

        # Orange Komponentenpfeile
        draw_quiver(ax, 0, 0, comp_x[0], comp_x[1],
                    "darkorange", lw=2.2, alpha=0.85, label="_nolegend_")
        draw_quiver(ax, comp_x[0], comp_x[1], comp_y[0], comp_y[1],
                    "darkorange", lw=2.2, alpha=0.85, label="_nolegend_")

        # Gestrichelte Hilfslinie (Parallelogramm-Abschluss)
        ax.plot([comp_x[0], p_w[0]], [comp_x[1], p_w[1]],
                color="darkorange", linestyle="--", linewidth=1.3, alpha=0.65)
        ax.plot([0, comp_x[0]], [0, comp_x[1]],
                color="forestgreen", linestyle="--", linewidth=1.3, alpha=0.35)

        # Komponentenbeschriftung (Mittelposition der Pfeile)
        mid_cx = comp_x / 2
        mid_cy = comp_x + comp_y / 2
        sign_x = "+" if p_local[0] >= 0 else ""
        sign_y = "+" if p_local[1] >= 0 else ""
        ax.text(mid_cx[0] + 0.04, mid_cx[1] + 0.04,
                f"${sign_x}{p_local[0]:.3f}\\,\\mathbf{{e}}_{{x,L}}$",
                color="darkorange", fontsize=10, ha="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.82, pad=1))
        ax.text(mid_cy[0] + 0.04, mid_cy[1] - 0.04,
                f"${sign_y}{p_local[1]:.3f}\\,\\mathbf{{e}}_{{y,L}}$",
                color="darkorange", fontsize=10, ha="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.82, pad=1))

        # "p bleibt geometrisch gleich" Hinweis
        ax.text(0.5, 0.02, r"$p$ bleibt geometrisch gleich",
                color="tab:blue", fontsize=9, ha="center", va="bottom",
                transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="tab:blue", alpha=0.85))

        # ── Winkel-Arc ────────────────────────────────
        if abs(theta) >= 1:
            t1 = min(0, theta)
            t2 = max(0, theta)
            arc = Arc((0, 0), 0.46, 0.46, theta1=t1, theta2=t2,
                      color="forestgreen", linewidth=1.8, zorder=5)
            ax.add_patch(arc)
            mid_rad = np.radians(theta / 2)
            sign_str = "+" if theta >= 0 else ""
            ax.text(0.30 * np.cos(mid_rad), 0.30 * np.sin(mid_rad),
                    f"${sign_str}{theta:.0f}°$",
                    color="forestgreen", fontsize=11, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15",
                              facecolor="white", edgecolor="none", alpha=0.85))

        # ── Koordinaten-Box (unten links im Bild) ─────
        coord_x = -1.42
        coord_y = -1.10
        ax.text(coord_x, coord_y,
                f"Koordinaten im lokalen System:  "
                f"${{}}^L p=\\binom{{{p_local[0]:.3f}}}{{{p_local[1]:.3f}}}$",
                fontsize=10,
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="white", edgecolor="0.78"))

        # ── Legende ───────────────────────────────────
        handles, labels = ax.get_legend_handles_labels()
        filtered = [(h, l) for h, l in zip(handles, labels)
                    if not l.startswith("_")]
        ax.legend([h for h, _ in filtered], [l for _, l in filtered],
                  loc="upper left", frameon=True, fontsize=9,
                  borderpad=0.35, labelspacing=0.35,
                  handlelength=1.6, handletextpad=0.55, borderaxespad=0.35)

    # ─────────────────────────────────────────────────
    #  3D-PLOT  (Rotation in allen Achsen, große gut lesbare KoSys)
    # ─────────────────────────────────────────────────
    def _draw_3d(self):
        ax = self.ax_3d
        ax.cla()
        mode_str = "AKTIV" if self.mode == "Aktiv" else "PASSIV"
        # For Vergleich mode, fall back to Passiv in 3D view
        ax.set_title(f"3D-Ansicht  –  Roll / Pitch / Yaw  [{mode_str}]",
                     fontsize=9.5, fontweight="bold", color=TUM_BLUE, pad=8)

        R_total = Rz(self.rot_z) @ Ry(self.rot_y) @ Rx(self.rot_x)
        t_B     = np.array([self.tx, self.ty, 0.0])
        p_start = np.array([self.px, self.py, 0.0])

        # Achsenbereich dynamisch: umschließt Ursprung W, Ursprung L und Punkt
        all_pts = [np.zeros(3), t_B, p_start, R_total @ p_start + t_B]
        mins = np.min(all_pts, axis=0) - 2.2
        maxs = np.max(all_pts, axis=0) + 2.2
        pad  = max(maxs - mins) / 2 + 0.5
        cx   = (mins + maxs) / 2
        ax.set_xlim(cx[0]-pad, cx[0]+pad)
        ax.set_ylim(cx[1]-pad, cx[1]+pad)
        ax.set_zlim(cx[2]-pad*0.7, cx[2]+pad*0.7)

        ax.set_xlabel("X", fontsize=9, labelpad=2)
        ax.set_ylabel("Y", fontsize=9, labelpad=2)
        ax.set_zlabel("Z", fontsize=9, labelpad=2)
        ax.tick_params(labelsize=7, pad=1)
        ax.grid(True, alpha=0.18)
        ax.set_facecolor("#F8F9FF")

        # Achsenlänge: ~40% der Plotbreite → immer gut sichtbar
        scale = max((maxs - mins).max() * 0.40, 2.0)

        def frame_3d(R, t, color, label, alpha=1.0):
            axes_def = [
                (R @ np.array([scale, 0, 0]), "X", "-"),
                (R @ np.array([0, scale, 0]), "Y", "--"),
                (R @ np.array([0, 0, scale]), "Z", ":"),
            ]
            for vec, lbl, ls in axes_def:
                ax.quiver(*t, *vec,
                          color=color,
                          arrow_length_ratio=0.18,
                          linewidth=2.8,
                          linestyle=ls,
                          alpha=alpha,
                          zorder=4)
                tip = t + vec
                ax.text(tip[0], tip[1], tip[2],
                        f" {lbl}$_{{{label}}}$",
                        color=color, fontsize=10,
                        fontweight="bold", alpha=alpha, zorder=5)
            ax.scatter(*t, color=color, s=70, zorder=6, alpha=alpha,
                       edgecolors="white", linewidths=0.8)
            ax.text(t[0], t[1], t[2] - scale*0.12,
                    f" {{{label}}}",
                    color=color, fontsize=8, alpha=alpha)

        if self.mode == "Aktiv":   # Vergleich falls back to Passiv branch below
            # Welt-KoSy W (voll sichtbar, fix)
            frame_3d(np.eye(3), np.zeros(3), TUM_BLUE, "W")

            # Originalvektor (blau, transparent)
            p0 = p_start
            ax.quiver(*np.zeros(3), *p0,
                      color="tab:blue", arrow_length_ratio=0.18,
                      linewidth=2.2, alpha=0.45, linestyle="--", zorder=3)
            ax.scatter(*p0, color="tab:blue", s=60, alpha=0.45, zorder=5)
            ax.text(p0[0]+0.1, p0[1]+0.1, p0[2]+0.1,
                    f" $p$\n [{p0[0]:.1f},{p0[1]:.1f},{p0[2]:.1f}]",
                    fontsize=8, color="tab:blue", alpha=0.6)

            # Rotierter Vektor p' (rot, voll)
            p_rot = R_total @ p0
            ax.quiver(*np.zeros(3), *p_rot,
                      color="tab:red", arrow_length_ratio=0.18,
                      linewidth=2.8, zorder=4)
            ax.scatter(*p_rot, color="tab:red", s=90, zorder=6,
                       edgecolors="white", linewidths=0.8)
            ax.text(p_rot[0]+0.1, p_rot[1]+0.1, p_rot[2]+0.1,
                    f" $p'$\n [{p_rot[0]:.1f},{p_rot[1]:.1f},{p_rot[2]:.1f}]",
                    fontsize=8, color="tab:red", fontweight="bold")

        else:
            # Beide KoSys voll sichtbar
            frame_3d(np.eye(3), np.zeros(3), TUM_BLUE, "W")
            frame_3d(R_total, t_B, TUM_ORANGE, "L")

            # Translation D_L als gestrichelter Pfeil
            ax.quiver(0, 0, 0, *t_B,
                      color=TUM_GREEN, alpha=0.8,
                      arrow_length_ratio=0.10,
                      linewidth=2.0, linestyle="--", zorder=3)
            mid_t = t_B / 2
            ax.text(mid_t[0]+0.1, mid_t[1]+0.1, mid_t[2]+0.15,
                    f"$D_L$=[{self.tx:.1f},{self.ty:.1f}]",
                    fontsize=8, color=TUM_GREEN)

            # Punkt fix in Welt
            p_w = p_start
            ax.scatter(*p_w, color=TUM_RED, s=110, zorder=7,
                       edgecolors="white", linewidths=1.0)
            ax.text(p_w[0]+0.12, p_w[1]+0.12, p_w[2]+0.18,
                    " P",
                    fontsize=10, color=TUM_RED, fontweight="bold")

    # ─────────────────────────────────────────────────
    #  FORMELN & MATRIZEN  (unten links)
    # ─────────────────────────────────────────────────
    def _draw_matrix(self):
        ax = self.ax_mat
        ax.cla()
        ax.axis("off")
        ax.set_facecolor(PANEL)

        c = np.cos(np.radians(self.rot_z))
        s = np.sin(np.radians(self.rot_z))
        R  = R2(self.rot_z)
        origin_B = np.array([self.tx, self.ty])
        p_start  = np.array([self.px, self.py])

        if self.mode == "Aktiv":   # Vergleich uses Passiv branch
            ax.set_title("Formeln & Matrizen  –  AKTIV", fontsize=10,
                         fontweight="bold", color=TUM_ORANGE, pad=5)
            p_result = R @ p_start
            formula_top_l  = r"$R(\theta_z) =$"
            formula_result = "Aktive Transformation:"
            result_label   = r"${}^W\!p' = R \cdot {}^W\!p$"
            res_str        = f"${{}}^W\\!p' = ({p_result[0]:+.4f},\\ {p_result[1]:+.4f})^\\top$"
            h_label        = "Homogene Darstellung:"
            h1 = f"[ {c:+.3f} {-s:+.3f}  0.000 ]"
            h2 = f"[ {s:+.3f}  {c:+.3f}  0.000 ]"
            h3 = "[ 0.000  0.000  1.000 ]"
            note = "(keine Translation bei reiner Rotation!)"
            p_input_str = f"${{}}^W\\!p = ({self.px:.2f},\\ {self.py:.2f})^\\top$"
        else:
            ax.set_title("Formeln & Matrizen  –  PASSIV", fontsize=10,
                         fontweight="bold", color=TUM_BLUE, pad=5)
            p_local = R.T @ (p_start - origin_B)
            formula_top_l  = r"$R^\top(\theta_z) =$"
            formula_result = "Passive Transformation:"
            result_label   = r"${}^L\!p = R^\top \cdot ({}^W\!p - D_L)$"
            res_str        = f"${{}}^L\\!p = ({p_local[0]:+.4f},\\ {p_local[1]:+.4f})^\\top$"
            h_label        = r"Homogene Matrix $H$:"
            h1 = f"[ {c:+.3f} {-s:+.3f} {self.tx:+.2f} ]"
            h2 = f"[ {s:+.3f}  {c:+.3f} {self.ty:+.2f} ]"
            h3 = "[ 0.000  0.000  1.000 ]"
            note = r"${}^L\!p = H^{-1} \cdot [{}^W\!p;\,1]^\top$"
            p_input_str = f"${{}}^W\\!p = ({self.px:.2f},\\ {self.py:.2f})^\\top$"

        sz = 9.5
        dy = 0.115
        color_main = TUM_ORANGE if self.mode == "Aktiv" else TUM_BLUE  # Vergleich → Passiv

        def block(x, y, lines):
            cy = y
            for item in lines:
                txt, color, bold = item[:3]
                mono = item[3] if len(item) > 3 else False
                kw = dict(transform=ax.transAxes, fontsize=sz, color=color, va="top",
                          fontweight="bold" if bold else "normal")
                if mono:
                    kw["fontfamily"] = "monospace"
                ax.text(x, cy, txt, **kw)
                cy -= dy

        block(0.03, 0.92, [
            (formula_top_l,               color_main, True),
            (f"[ {c:+.3f}  {-s:+.3f} ]", color_main, False, True),
            (f"[ {s:+.3f}   {c:+.3f} ]",  color_main, False, True),
        ])

        block(0.53, 0.92, [
            (r"Translation $D_L$ =",      TUM_GREEN, True),
            (f"[ {self.tx:+.3f} ]",       TUM_GREEN, False, True),
            (f"[ {self.ty:+.3f} ]",       TUM_GREEN, False, True),
        ])

        block(0.03, 0.44, [
            (formula_result,              TUM_RED, True),
            (p_input_str,                 "#333333", False),
            (result_label,                "#333333", False),
            (res_str,                     color_main, False),
        ])

        block(0.53, 0.44, [
            (h_label,                     TUM_PURPLE, True),
            (h1,                          TUM_PURPLE, False, True),
            (h2,                          TUM_PURPLE, False, True),
            (h3,                          TUM_PURPLE, False, True),
            (note,                        TUM_GRAY,   False),
        ])

    # ─────────────────────────────────────────────────
    #  LEGENDE  (unten, 2 Spalten breit)
    # ─────────────────────────────────────────────────
    def _draw_legend(self):
        ax = self.ax_leg
        ax.cla()
        ax.axis("off")
        ax.set_facecolor(PANEL)

        if self.mode == "Aktiv":   # Vergleich uses Passiv branch
            ax.set_title(
                "AKTIVE Transformation  –  Das Objekt bewegt sich, das Koordinatensystem bleibt fix",
                fontsize=10, fontweight="bold", color=TUM_ORANGE, pad=5)
            items = [
                (TUM_BLUE,   "o",
                 "KoSy W – Welt-Frame (fix)",
                 "Bleibt ortsfest. Alle Weltkoordinaten",
                 "werden in diesem System gemessen."),
                (TUM_ORANGE, "o",
                 "KoSy L – Lokal/Fahrzeug (fix, transparent)",
                 "Bei aktiver Transformation dreht sich das",
                 "KoSy NICHT – nur der Punkt bewegt sich."),
                (TUM_GRAY,   "o",
                 r"Punkt $P$ (original, ${}^W\!p$)",
                 "Ausgangsposition des Punktes",
                 "in Weltkoordinaten."),
                (TUM_RED,    "D",
                 r"Punkt $P'$ (rotiert, ${}^W\!p'$)",
                 r"$p' = R(\theta) \cdot p$ – Koordinaten in $W$ ändern",
                 "sich, weil der Punkt physisch bewegt wird."),
                (TUM_PURPLE, "s",
                 "Homogene Matrix (reine Rotation)",
                 "Keine Translation bei aktiver Rotation",
                 "um den Ursprung: H = [R | 0; 0 | 1]."),
            ]
            key_insight = (
                "► Schlüssel: Gleiche Matrix $R$ – aber Interpretation anders!\n"
                r"   Aktiv:  $p' = R\cdot p$   (Punkt wandert im selben KoSy)" + "\n"
                r"   Passiv: ${}^L\!p = R^\top(p - t)$  (Punkt bleibt, KoSy dreht)"
            )
        else:
            ax.set_title(
                "PASSIVE Transformation  –  Punkt bleibt fix, Koordinatensystem dreht sich (Robotik!)",
                fontsize=10, fontweight="bold", color=TUM_BLUE, pad=5)
            items = [
                (TUM_BLUE,   "o",
                 "KoSy W – Welt-Frame",
                 "Inertialsystem, global fixiert. Alle absoluten",
                 "Koordinaten werden in diesem Frame angegeben."),
                (TUM_ORANGE, "o",
                 "KoSy L – Lokal/Fahrzeug-Frame",
                 "Dreht und verschiebt sich relativ zu W. Lage",
                 r"durch Translation $D_L$ und Rotation $\theta_z$ definiert."),
                (TUM_GREEN,  "s",
                 r"Translation $D_L$",
                 "Verschiebungsvektor vom Ursprung W zum",
                 "Ursprung L, ausgedrückt in Weltkoordinaten."),
                (TUM_RED,    "D",
                 "Punkt P – fix im Raum",
                 "Bleibt geometrisch an seiner Stelle. Koordinaten",
                 r"${}^L\!p = R^\top({}^W\!p - D_L)$ ändert sich durch KoSy-Wechsel."),
                (TUM_PURPLE, "s",
                 r"Homogene Matrix $H$",
                 r"Fasst $R$ und $t$ zusammen: ${}^W\!p = H\cdot[{}^L\!p;\,1]^\top$",
                 r"Inversion: ${}^L\!p = H^{-1}\cdot[{}^W\!p;\,1]^\top$ (passive Sichtweise)."),
            ]
            key_insight = (
                "► In der Robotik = Passive Sichtweise!\n"
                r"   Sensor misst ${}^L\!p$  →  Welt braucht ${}^W\!p = H\cdot[{}^L\!p;\,1]^\top$" + "\n"
                "   Gleiche Zahlen  –  andere Frage: 'Wo ist das Objekt?' vs. 'Wo bin ich?'"
            )

        col_x  = [0.02, 0.51]
        sym_dx = 0.035
        txt_dx = 0.075
        y_start = 0.87
        dy_title = 0.090
        dy_expl  = 0.056

        for i, (color, marker, titel, expl1, expl2) in enumerate(items):
            col = i % 2
            row = i // 2
            cx = col_x[col]
            cy = y_start - row * (dy_title + 2 * dy_expl + 0.025)

            ax.plot(cx + sym_dx, cy + 0.005, marker,
                    transform=ax.transAxes,
                    color=color, ms=9, clip_on=False, markeredgewidth=0)
            ax.text(cx + txt_dx, cy, titel,
                    transform=ax.transAxes,
                    fontsize=8.2, color=color, va="top", fontweight="bold")
            ax.text(cx + txt_dx, cy - dy_expl, expl1,
                    transform=ax.transAxes,
                    fontsize=7.7, color=TUM_GRAY, va="top")
            ax.text(cx + txt_dx, cy - 2*dy_expl, expl2,
                    transform=ax.transAxes,
                    fontsize=7.7, color=TUM_GRAY, va="top")

        # Key Insight Box – innerhalb der Axes
        ax.text(0.5, 0.18, key_insight,
                transform=ax.transAxes,
                fontsize=8, ha="center", va="top",
                color=TUM_BLUE,
                bbox=dict(boxstyle="round,pad=0.45",
                          facecolor="#DDE8F5" if self.mode != "Aktiv" else BG_AKTIV,
                          edgecolor=TUM_BLUE if self.mode != "Aktiv" else TUM_ORANGE,
                          alpha=0.92))

    # ─────────────────────────────────────────────────
    def _apply_preset(self, tx, ty, rz, rx, ry, px, py):
        self.s_tx.set_val(tx)
        self.s_ty.set_val(ty)
        self.s_rz.set_val(rz)
        self.s_rx.set_val(rx)
        self.s_ry.set_val(ry)
        self.s_px.set_val(px)
        self.s_py.set_val(py)

    # ─────────────────────────────────────────────────
    def _reset(self, event):
        for s in [self.s_tx, self.s_ty, self.s_rz,
                  self.s_rx, self.s_ry, self.s_px, self.s_py]:
            s.reset()

    def show(self):
        plt.show()


# ── Start ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  GAV Vorlesung 3 – Koordinatentransformation  v3")
    print("  NEU: Aktiv / Passiv Toggle")
    print("=" * 60)
    print()
    print("  LAYOUT:")
    print("  Oben links    → 2D-Plot (modusabhängig)")
    print("  Oben mitte    → 3D-Plot (Roll / Pitch / Yaw)")
    print("  Oben rechts   → Schieberegler + Aktiv/Passiv-Switch")
    print("  Unten links   → Formeln & Matrizen (live, je nach Modus)")
    print("  Unten mitte+r → Legende mit Erklärung (je nach Modus)")
    print()
    print("  Startet im PASSIV-Modus (Robotik-Standard).")
    print("  RadioButton oben rechts → Modus umschalten.")
    print()
    tool = TransformationTool()
    tool.show()
