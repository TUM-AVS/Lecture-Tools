import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
import heapq

# ──────────────────────────────────────────────────────────────────────────────
#  FARBEN (TUM-Design)
# ──────────────────────────────────────────────────────────────────────────────
TUM_BLUE        = "#0065BD"
TUM_LIGHT       = "#64A0C8"
BG_COLOR        = "#F5F5F5"
VISITED_COLOR   = "#AAAAAA"
CURRENT_COLOR   = "#FFFFFF"
UPDATED_COLOR   = "#E07B00"
UNVISITED_COLOR = "#FFFFFF"
EDGE_INACTIVE   = "#CCCCCC"
GREEN_CHECK     = "#5A9A3A"

# ──────────────────────────────────────────────────────────────────────────────
#  GRAPH (passend zum Bild)
# ──────────────────────────────────────────────────────────────────────────────
EDGES = [
    (0, 1, 3), (0, 2, 4),
    (1, 2, 3), (1, 3, 3),
    (2, 3, 2), (2, 4, 3),
    (3, 5, 4),
    (4, 6, 4),
    (5, 4, 3), (5, 6, 6),
]

POS = {
    0: (0.5, 0.0),
    1: (1.0, 1.8),
    2: (2.3, 1.3),
    3: (1.8, 3.0),
    4: (3.8, 1.3),
    5: (3.5, 3.0),
    6: (5.0, 0.2),
}

# ──────────────────────────────────────────────────────────────────────────────
#  DIJKSTRA – alle Schritte berechnen
# ──────────────────────────────────────────────────────────────────────────────
def dijkstra_steps(edges, start=0):
    G = nx.DiGraph()
    G.add_weighted_edges_from(edges)
    nodes = sorted(G.nodes)
    INF = float('inf')

    d = {v: INF for v in nodes}
    p = {v: None for v in nodes}
    visited = set()
    d[start] = 0
    pq = [(0, start)]
    steps = []

    while pq:
        dist_u, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        d_before = d.copy()
        active_edges = []
        updated_nodes = []

        for v in G.neighbors(u):
            w = G[u][v]['weight']
            active_edges.append((u, v, w))
            if d[u] + w < d[v]:
                d[v] = d[u] + w
                p[v] = u
                updated_nodes.append(v)
                heapq.heappush(pq, (d[v], v))

        steps.append({
            'current':       u,
            'd':             d.copy(),
            'd_before':      d_before,
            'p':             p.copy(),
            'visited':       visited.copy(),
            'active_edges':  active_edges,
            'updated_nodes': updated_nodes,
        })

    return steps, G


def build_description(step):
    u = step['current']
    d = step['d']
    d_b = step['d_before']
    active = step['active_edges']
    updated = step['updated_nodes']

    if not active:
        return f"v{u} wird verarbeitet (d = {d[u]}). Keine weiteren Kanten – Algorithmus fertig!"

    lines = [f"v{u} wird verarbeitet  (d[v{u}] = {d[u]})."]
    for _, dst, w in active:
        nd = d[u] + w
        old = d_b[dst]
        old_s = "∞" if old == float('inf') else str(int(old))
        if dst in updated:
            lines.append(f"   v{dst}:  {d[u]} + {w} = {nd}  <  {old_s}  →  aktualisiert ✓")
        else:
            lines.append(f"   v{dst}:  {d[u]} + {w} = {nd}  ≥  {old_s}  →  keine Änderung")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  GUI
# ──────────────────────────────────────────────────────────────────────────────
class DijkstraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dijkstra Algorithmus – Visualisierung")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(1200, 720)

        self.steps, self.G = dijkstra_steps(EDGES, start=0)
        self.nodes = sorted(self.G.nodes)
        self.step_idx = -1
        self._auto_id = None

        self._build_ui()
        self._draw_step()

        self.root.bind("<Right>",  lambda e: self._next())
        self.root.bind("<Left>",   lambda e: self._prev())
        self.root.bind("<space>",  lambda e: self._toggle_auto())
        self.root.bind("<Escape>", lambda e: self._stop_auto())

    # ──────────────────────────────────────────────────────────────────────────
    #  UI-Aufbau
    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        title_frame = tk.Frame(self.root, bg=TUM_BLUE)
        title_frame.pack(fill="x")
        tk.Label(title_frame,
                 text="Globale Planung  –  Dijkstra Algorithmus",
                 font=("Helvetica Neue", 16, "bold"),
                 fg="white", bg=TUM_BLUE, pady=10).pack()

        main = tk.Frame(self.root, bg=BG_COLOR)
        main.pack(fill="both", expand=True, padx=16, pady=12)

        left = tk.Frame(main, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6.5, 5.2))
        self.fig.patch.set_facecolor(BG_COLOR)
        self.canvas = FigureCanvasTkAgg(self.fig, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._build_legend(left)

        right = tk.Frame(main, bg=BG_COLOR, width=430)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        self._build_step_box(right)
        self._build_main_table(right)
        self._build_queue_table(right)

        self._build_controls()

    def _build_legend(self, parent):
        leg = tk.Frame(parent, bg=BG_COLOR)
        leg.pack(fill="x", padx=8, pady=(2, 4))
        items = [
            (TUM_BLUE,    "#fff",          "Aktueller Knoten"),
            ("#c45f00",   UPDATED_COLOR,   "Gerade aktualisiert"),
            ("#777777",   VISITED_COLOR,   "Bereits besucht"),
            ("#aaaaaa",   UNVISITED_COLOR, "Noch offen"),
        ]
        for border, fill, label in items:
            row = tk.Frame(leg, bg=BG_COLOR)
            row.pack(side="left", padx=10)
            c = tk.Canvas(row, width=18, height=18, bg=BG_COLOR, highlightthickness=0)
            c.pack(side="left")
            c.create_oval(2, 2, 16, 16, fill=fill, outline=border, width=2)
            tk.Label(row, text=label, font=("Helvetica Neue", 9),
                     fg="#555", bg=BG_COLOR).pack(side="left", padx=2)

    def _build_step_box(self, parent):
        frame = tk.Frame(parent, bg="#EAF2FB", bd=0, relief="flat")
        frame.pack(fill="x", pady=(0, 10))

        self.step_label = tk.Label(
            frame, text="Ausgangszustand",
            font=("Helvetica Neue", 12, "bold"),
            fg=TUM_BLUE, bg="#EAF2FB", anchor="w", padx=10, pady=6)
        self.step_label.pack(fill="x")

        self.desc_label = tk.Label(
            frame, text="",
            font=("Courier", 12),
            fg="#333", bg="#EAF2FB",
            anchor="w", justify="left",
            padx=10, pady=6, wraplength=405)
        self.desc_label.pack(fill="x")

    def _build_main_table(self, parent):
        tk.Label(parent, text="Distanz- & Vorgänger-Tabelle",
                 font=("Helvetica Neue", 11, "bold"),
                 fg=TUM_BLUE, bg=BG_COLOR, anchor="w").pack(fill="x")

        frame = tk.Frame(parent, bg="#cccccc")
        frame.pack(fill="x", pady=(4, 12))

        self.table_cells = {}
        cols = [""] + [f"v{n}" for n in self.nodes]

        for c, col in enumerate(cols):
            bg = TUM_BLUE if c == 0 else TUM_LIGHT
            lbl = tk.Label(frame, text=col,
                           font=("Helvetica Neue", 10, "bold italic" if c > 0 else "bold"),
                           bg=bg, fg="white",
                           width=5, padx=4, pady=5, relief="flat")
            lbl.grid(row=0, column=c, sticky="nsew", padx=1, pady=1)

        for r, rlabel in enumerate(["d[v]", "p[v]", "c[v]"]):
            tk.Label(frame, text=rlabel,
                     font=("Helvetica Neue", 10, "bold"),
                     bg=TUM_BLUE, fg="white",
                     width=5, padx=4, pady=5, relief="flat"
                     ).grid(row=r + 1, column=0, sticky="nsew", padx=1, pady=1)

            for c, node in enumerate(self.nodes):
                cell = tk.Label(frame, text="–",
                                font=("Helvetica Neue", 10),
                                bg="white", fg="#333",
                                width=5, padx=4, pady=5, relief="flat")
                cell.grid(row=r + 1, column=c + 1, sticky="nsew", padx=1, pady=1)
                self.table_cells[(rlabel, node)] = cell

    def _build_queue_table(self, parent):
        tk.Label(parent, text="Prioritätswarteschlange",
                 font=("Helvetica Neue", 11, "bold"),
                 fg=TUM_BLUE, bg=BG_COLOR, anchor="w").pack(fill="x")

        self.queue_frame = tk.Frame(parent, bg=BG_COLOR)
        self.queue_frame.pack(fill="x", pady=(4, 8))

    def _build_controls(self):
        ctrl = tk.Frame(self.root, bg="#E0E8F0", pady=8)
        ctrl.pack(fill="x", padx=16, pady=(0, 12))

        bs = dict(font=("Helvetica Neue", 11, "bold"),
                  bg=TUM_BLUE, fg="black", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  activebackground=TUM_LIGHT, activeforeground="black")

        self.btn_prev = tk.Button(ctrl, text="◀  Zurück", command=self._prev, **bs)
        self.btn_prev.pack(side="left", padx=6)

        self.btn_next = tk.Button(ctrl, text="Weiter  ▶", command=self._next, **bs)
        self.btn_next.pack(side="left", padx=6)

        self.btn_auto = tk.Button(ctrl, text="▶▶  Auto-Play",
                                  command=self._toggle_auto,
                                  font=("Helvetica Neue", 11, "bold"),
                                  bg="#059669", fg="black", relief="flat",
                                  padx=16, pady=6, cursor="hand2",
                                  activebackground="#047857", activeforeground="black")
        self.btn_auto.pack(side="left", padx=6)

        self.btn_reset = tk.Button(ctrl, text="↺  Neustart",
                                   command=self._reset,
                                   font=("Helvetica Neue", 11),
                                   bg="#888", fg="black", relief="flat",
                                   padx=16, pady=6, cursor="hand2",
                                   activebackground="#aaa", activeforeground="black")
        self.btn_reset.pack(side="left", padx=6)

        tk.Label(ctrl, text="Geschwindigkeit:",
                 font=("Helvetica Neue", 10), fg=TUM_BLUE, bg="#E0E8F0"
                 ).pack(side="left", padx=(20, 4))
        tk.Label(ctrl, text="schnell",
                 font=("Helvetica Neue", 9), fg="#888", bg="#E0E8F0"
                 ).pack(side="left")
        self.speed_var = tk.IntVar(value=1500)
        speed_scale = tk.Scale(ctrl, from_=400, to=3000,
                               orient="horizontal", resolution=100,
                               variable=self.speed_var, length=120,
                               bg="#E0E8F0", fg=TUM_BLUE,
                               troughcolor="#C8D8E8",
                               highlightthickness=0, showvalue=False)
        speed_scale.pack(side="left")
        tk.Label(ctrl, text="langsam",
                 font=("Helvetica Neue", 9), fg="#888", bg="#E0E8F0"
                 ).pack(side="left")

        self.progress_lbl = tk.Label(ctrl, text="",
                                     font=("Helvetica Neue", 10),
                                     fg=TUM_BLUE, bg="#E0E8F0")
        self.progress_lbl.pack(side="right", padx=12)

        tk.Label(ctrl, text="← →  Pfeiltasten  |  Leertaste: Auto",
                 font=("Helvetica Neue", 9), fg="#999", bg="#E0E8F0"
                 ).pack(side="right", padx=8)

    # ──────────────────────────────────────────────────────────────────────────
    #  Navigation
    # ──────────────────────────────────────────────────────────────────────────
    def _next(self):
        if self.step_idx < len(self.steps) - 1:
            self.step_idx += 1
            self._draw_step()

    def _prev(self):
        if self.step_idx > -1:
            self.step_idx -= 1
            self._draw_step()

    def _reset(self):
        self._stop_auto()
        self.step_idx = -1
        self._draw_step()

    def _toggle_auto(self):
        if self._auto_id is not None:
            self._stop_auto()
        else:
            self.btn_auto.config(text="⏹  Stop", bg="#dc2626", fg="black",
                                 activebackground="#b91c1c", activeforeground="black")
            self._auto_step()

    def _auto_step(self):
        if self.step_idx >= len(self.steps) - 1:
            self._stop_auto()
            return
        self._next()
        self._auto_id = self.root.after(self.speed_var.get(), self._auto_step)

    def _stop_auto(self):
        if self._auto_id is not None:
            self.root.after_cancel(self._auto_id)
            self._auto_id = None
        self.btn_auto.config(text="▶▶  Auto-Play", bg="#059669", fg="black",
                             activebackground="#047857", activeforeground="black")

    # ──────────────────────────────────────────────────────────────────────────
    #  Zeichnen
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_step(self):
        self.ax.clear()
        self.ax.set_facecolor(BG_COLOR)
        INF = float('inf')

        if self.step_idx == -1:
            d        = {v: INF for v in self.nodes}
            d[0]     = 0
            p        = {v: None for v in self.nodes}
            visited  = set()
            current  = None
            updated  = []
            active_e = []
            title    = "Ausgangszustand"
            desc     = ("Startknoten v0 = 0, alle anderen Knoten = ∞.\n"
                        "Drücke 'Weiter' oder → um zu beginnen.")
        else:
            step     = self.steps[self.step_idx]
            d        = step['d']
            p        = step['p']
            visited  = step['visited']
            current  = step['current']
            updated  = step['updated_nodes']
            active_e = [(u, v) for u, v, w in step['active_edges']]
            title    = f"Schritt {self.step_idx + 1}  |  Bearbeite v{current}"
            desc     = build_description(step)

        self.step_label.config(text=title)
        self.desc_label.config(text=desc)

        # ── Knotenfarben ──────────────────────────────────────────────────────
        node_fill   = []
        node_border = []
        node_lw     = []

        for n in self.G.nodes:
            if n == current:
                node_fill.append(CURRENT_COLOR)
                node_border.append(TUM_BLUE)
                node_lw.append(3.5)
            elif n in updated:
                node_fill.append(UPDATED_COLOR)
                node_border.append("#c45f00")
                node_lw.append(2.5)
            elif n in visited:
                node_fill.append(VISITED_COLOR)
                node_border.append("#777777")
                node_lw.append(1.5)
            else:
                node_fill.append(UNVISITED_COLOR)
                node_border.append("#AAAAAA")
                node_lw.append(1.5)

        # ── Kantenfarben ──────────────────────────────────────────────────────
        edge_colors = []
        edge_widths = []

        for (u, v) in self.G.edges():
            if (u, v) in active_e:
                if v in updated:
                    edge_colors.append(UPDATED_COLOR)
                else:
                    edge_colors.append(TUM_BLUE)
                edge_widths.append(2.5)
            elif u in visited and u != current:
                edge_colors.append("#A0C4E0")
                edge_widths.append(1.2)
            else:
                edge_colors.append(EDGE_INACTIVE)
                edge_widths.append(1.0)

        # ── Graph zeichnen ────────────────────────────────────────────────────
        nx.draw_networkx_nodes(
            self.G, POS, ax=self.ax,
            node_color=node_fill,
            edgecolors=node_border,
            linewidths=node_lw,
            node_size=900,
        )
        nx.draw_networkx_edges(
            self.G, POS, ax=self.ax,
            edge_color=edge_colors,
            width=edge_widths,
            arrows=True,
            arrowstyle='-|>',
            arrowsize=18,
            node_size=900,
            connectionstyle='arc3,rad=0.05',
        )
        edge_labels = {(u, v): str(w) for u, v, w in self.G.edges(data='weight')}
        nx.draw_networkx_edge_labels(
            self.G, POS, edge_labels=edge_labels, ax=self.ax,
            font_size=9, font_color="#333",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.85, ec="none"),
        )

        # ── Knotenbezeichnungen ───────────────────────────────────────────────
        for n, (x, y) in POS.items():
            if n == current:
                txt_color = TUM_BLUE
            elif n in updated or n in visited:
                txt_color = "white"
            else:
                txt_color = "#444"
            self.ax.text(x, y, f"v{n}",
                         ha='center', va='center',
                         fontsize=10, fontweight='bold',
                         color=txt_color, zorder=5)

        # ── Distanzlabels über Knoten ─────────────────────────────────────────
        for n, (x, y) in POS.items():
            val = d[n]
            dist_str = "∞" if val == INF else str(int(val))
            self.ax.text(x, y + 0.36, f"d={dist_str}",
                         ha='center', va='bottom',
                         fontsize=8, color="#555", style='italic')

        self.ax.set_title(title, fontsize=12, fontweight='bold',
                          color=TUM_BLUE, pad=10)
        self.ax.axis('off')
        self.fig.tight_layout()
        self.canvas.draw()

        self._update_table(d, p, visited, current, updated)
        self._update_queue(d, visited)
        self._update_buttons()

    # ──────────────────────────────────────────────────────────────────────────
    #  Tabelle aktualisieren
    # ──────────────────────────────────────────────────────────────────────────
    def _update_table(self, d, p, visited, current, updated):
        INF = float('inf')
        for node in self.nodes:
            val   = d[node]
            dtext = "0" if val == 0 else ("∞" if val == INF else str(int(val)))
            pval  = p[node]
            ptext = "–" if pval is None else f"v{pval}"

            cell_d = self.table_cells[("d[v]", node)]
            cell_p = self.table_cells[("p[v]", node)]
            cell_c = self.table_cells[("c[v]", node)]

            # d[v]-Zelle
            if node == current:
                bg_d, fg_d, fw = TUM_LIGHT, "white", "bold"
            elif node in updated:
                bg_d, fg_d, fw = "#FFD580", "#7a3c00", "bold"
            elif node in visited:
                bg_d, fg_d, fw = "#DFF0D8", "#2D6A2D", "normal"
            elif val != INF:
                bg_d, fg_d, fw = "#E8F4FD", TUM_BLUE, "normal"
            else:
                bg_d, fg_d, fw = "white", "#bbb", "normal"

            cell_d.config(text=dtext, bg=bg_d, fg=fg_d,
                          font=("Helvetica Neue", 10, fw))

            # p[v]-Zelle
            cell_p.config(
                text=ptext,
                bg="#EAF4FB" if pval is not None else "white",
                fg=TUM_BLUE if pval is not None else "#bbb",
                font=("Helvetica Neue", 10))

            # c[v]-Zelle
            if node in visited:
                cell_c.config(text="✓", bg="#DFF0D8", fg=GREEN_CHECK,
                              font=("Helvetica Neue", 13, "bold"))
            elif node == current:
                cell_c.config(text="→", bg=TUM_LIGHT, fg="white",
                              font=("Helvetica Neue", 11, "bold"))
            else:
                cell_c.config(text="–", bg="white", fg="#bbb",
                              font=("Helvetica Neue", 10))

    # ──────────────────────────────────────────────────────────────────────────
    #  Prioritätswarteschlange (horizontal wie im Bild)
    # ──────────────────────────────────────────────────────────────────────────
    def _update_queue(self, d, visited):
        for w in self.queue_frame.winfo_children():
            w.destroy()

        INF = float('inf')
        queue = sorted((d[v], v) for v in self.nodes
                       if v not in visited and d[v] != INF)

        if not queue:
            tk.Label(self.queue_frame,
                     text="(leer – Algorithmus abgeschlossen ✓)",
                     font=("Helvetica Neue", 10, "italic"),
                     fg=GREEN_CHECK, bg=BG_COLOR).pack(anchor="w")
            return

        head_row = tk.Frame(self.queue_frame, bg="#cccccc")
        head_row.pack(fill="x")
        val_row  = tk.Frame(self.queue_frame, bg="#cccccc")
        val_row.pack(fill="x", pady=(1, 0))

        lbl_kw = dict(width=5, padx=4, pady=4, relief="flat")

        tk.Label(head_row, text="v",
                 font=("Helvetica Neue", 10, "bold"),
                 bg=TUM_BLUE, fg="white", **lbl_kw
                 ).pack(side="left", padx=(0, 1))
        tk.Label(val_row, text="d[v]",
                 font=("Helvetica Neue", 10, "bold"),
                 bg=TUM_BLUE, fg="white", **lbl_kw
                 ).pack(side="left", padx=(0, 1))

        for dist, node in queue:
            is_min = (dist == queue[0][0])
            bg = TUM_LIGHT if is_min else "white"
            fg = "white"  if is_min else "#333"
            fw = "bold"   if is_min else "normal"
            tk.Label(head_row, text=f"v{node}",
                     font=("Helvetica Neue", 10, fw),
                     bg=bg, fg=fg, **lbl_kw
                     ).pack(side="left", padx=(0, 1))
            tk.Label(val_row, text=str(int(dist)),
                     font=("Helvetica Neue", 10, fw),
                     bg=bg, fg=fg, **lbl_kw
                     ).pack(side="left", padx=(0, 1))

    # ──────────────────────────────────────────────────────────────────────────
    #  Button-Zustand
    # ──────────────────────────────────────────────────────────────────────────
    def _update_buttons(self):
        total = len(self.steps)
        idx   = self.step_idx

        self.btn_prev.config(
            state="normal" if idx >= 0 else "disabled",
            bg=TUM_BLUE if idx >= 0 else "#AAAAAA")
        self.btn_next.config(
            state="normal" if idx < total - 1 else "disabled",
            bg=TUM_BLUE if idx < total - 1 else "#AAAAAA")

        if idx == -1:
            prog = f"Bereit  (0 / {total})"
        elif idx == total - 1:
            prog = f"Fertig ✓  ({total} / {total})"
        else:
            prog = f"Schritt  {idx + 1} / {total}"
        self.progress_lbl.config(text=prog)


# ──────────────────────────────────────────────────────────────────────────────
#  START
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = DijkstraApp(root)
    root.mainloop()
