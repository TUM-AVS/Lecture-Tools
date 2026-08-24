# Dijkstra Algorithmus – Interaktive Visualisierung

Interaktives Lerntool zum **Dijkstra-Algorithmus** aus *Grundlagen Autonomer Fahrzeuge (GAV)*,
TUM (Globale Planung).

Statt den Algorithmus nur auf dem Papier durchzurechnen, klickst du dich hier Schritt für
Schritt selbst durch: bei jedem Klick auf Weiter wird genau ein Knoten abgearbeitet, und du
siehst live, wie sich Distanz- und Vorgängertabelle sowie die Prioritätswarteschlange ändern.

---

## Voraussetzungen

- Python 3.9 oder neuer
- NetworkX
- Matplotlib

Installieren (falls noch nicht vorhanden):

```bash
pip install networkx matplotlib
```

> Wichtig: Das Tool nutzt Tkinter für die Oberfläche. Das ist bei den meisten
> Python-Installationen bereits vorinstalliert. Falls `tkinter` fehlt (z. B. bei manchen
> Linux-Minimalinstallationen), muss es zusätzlich über den Paketmanager installiert werden
> (unter Ubuntu z. B. `sudo apt install python3-tk`).

---

## Starten

```bash
python dijkstra_visualisierung.py
```

Es öffnet sich das Hauptfenster im Ausgangszustand: Startknoten `v0` hat Distanz 0, alle
anderen Knoten stehen auf unendlich. Über den Button Weiter (oder die Pfeiltaste rechts)
gehst du Schritt für Schritt durch den Algorithmus.

---

## Der Algorithmus in Kürze

Dijkstra findet die kürzesten Wege von einem Startknoten zu allen anderen Knoten in einem
gewichteten Graphen mit nichtnegativen Kantengewichten. Zu jedem Zeitpunkt verwaltet der
Algorithmus drei Größen pro Knoten `v`:

```
d[v]   Distanz          – aktuell kürzester bekannter Abstand vom Start
p[v]   Vorgänger        – über welchen Knoten dieser Abstand erreicht wird
c[v]   Status           – noch offen, aktuell in Bearbeitung, oder abgeschlossen
```

In jedem Schritt wird der noch nicht abgeschlossene Knoten mit der kleinsten Distanz aus der
Prioritätswarteschlange entnommen (das ist der aktuelle Knoten), und für jede seiner
ausgehenden Kanten wird geprüft, ob sich über ihn ein kürzerer Weg zum Nachbarn ergibt:

```
wenn  d[u] + w(u, v)  <  d[v]:
    d[v] = d[u] + w(u, v)
    p[v] = u
```

Das nennt man **Relaxation**. Wird dabei ein Wert verkleinert, gilt der Knoten als
aktualisiert und wandert mit seiner neuen Distanz in die Warteschlange.

---

## Aufbau des Fensters

| Bereich      | Inhalt                                                              |
|--------------|-----------------------------------------------------------------------|
| Links        | Graph-Ansicht mit Legende                                            |
| Rechts oben  | Schritt-Box mit Titel und Textbeschreibung der aktuell laufenden Relaxation |
| Rechts Mitte | Distanz- und Vorgängertabelle (`d[v]`, `p[v]`, `c[v]`) für alle Knoten |
| Rechts unten | Prioritätswarteschlange, sortiert nach aktueller Distanz              |
| Unten        | Steuerleiste: Zurück, Weiter, Auto-Play, Neustart, Geschwindigkeit    |

In der **Graph-Ansicht** sind Knoten und Kanten farblich codiert:

| Farbe                | Bedeutung                                  |
|-----------------------|--------------------------------------------|
| weiß mit blauem Rand  | aktueller Knoten (wird gerade bearbeitet)  |
| orange                | Knoten, dessen Distanz gerade aktualisiert wurde |
| grau                  | bereits abgeschlossener Knoten             |
| weiß mit grauem Rand  | noch offener, unbesuchter Knoten           |
| blaue Kante           | gerade betrachtete Kante ohne Aktualisierung |
| orange Kante          | gerade betrachtete Kante, die zu einer Aktualisierung geführt hat |
| hellblaue Kante       | Kante von einem bereits abgeschlossenen Knoten |
| graue Kante           | noch nicht betrachtete Kante                |

Über jedem Knoten steht außerdem laufend seine aktuelle Distanz `d = ...`.

---

## Bedienung

**Steuerung:**

| Aktion              | Taste / Button      |
|---------------------|-----------------------|
| Einen Schritt vor   | Weiter-Button oder Pfeiltaste rechts |
| Einen Schritt zurück| Zurück-Button oder Pfeiltaste links  |
| Auto-Play starten/stoppen | Auto-Play-Button oder Leertaste |
| Zurück zum Anfang   | Neustart-Button       |

Der Regler Geschwindigkeit steuert das Zeitintervall im Auto-Play-Modus zwischen schnell
und langsam. Unten rechts zeigt die Fortschrittsanzeige, beim wievielten von insgesamt
wie vielen Schritten du gerade bist.

---

## Der verwendete Graph

Der Graph ist im Code fest hinterlegt (gerichtet, mit Kantengewichten):

| Kante   | Gewicht | Kante   | Gewicht | Kante   | Gewicht |
|---------|---------|---------|---------|---------|---------|
| v0 → v1 | 3       | v2 → v3 | 2       | v5 → v4 | 3       |
| v0 → v2 | 4       | v2 → v4 | 3       | v5 → v6 | 6       |
| v1 → v2 | 3       | v3 → v5 | 4       |         |         |
| v1 → v3 | 3       | v4 → v6 | 4       |         |         |

Startknoten ist immer `v0`.

---

## Datei

`dijkstra_visualisierung.py` – alles in einer Datei, keine weiteren Projektdateien nötig.
