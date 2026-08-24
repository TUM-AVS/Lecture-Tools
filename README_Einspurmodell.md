# Lineares Einspurmodell – Live-Simulation

Echtzeit-Simulation der Querdynamik eines Fahrzeugs auf Basis des **linearen
Einspurmodells** aus *Grundlagen Autonomer Fahrzeuge (GAV)*

Du gibst Lenkwinkel und Geschwindigkeit vor, das Auto fährt live los, und daneben siehst du
gleichzeitig alle fahrdynamischen Größen: Schwimmwinkel, Gierrate, Schräglaufwinkel,
Seitenkräfte, die Bewegungsgleichungen, die Reifenkennlinie und sogar die Eigenwerte des
Systems. Das Ziel ist, ein Gefühl dafür zu bekommen, *wie* Lenkeingabe und Reifeneigenschaften
das Fahrverhalten bestimmen und wo das lineare Modell an seine Grenzen kommt.

---

## Voraussetzungen

- Python 3.9 oder neuer
- PyQt6
- Matplotlib
- NumPy

Installieren (falls noch nicht vorhanden):

```bash
pip install PyQt6 matplotlib numpy
```

> Wichtig: Das Tool braucht ein **interaktives** Matplotlib-Backend (ein echtes Fenster).
> In einem normalen Terminal oder in VS Code funktioniert das direkt. In Jupyter/Colab
> funktioniert es nicht.

---

## Starten

```bash
python lineares_einspurmodell.py
```

Es öffnet sich das Hauptfenster. Stell links Lenkwinkel `δ` und Geschwindigkeit `v` ein und
drück **Start**.

---

## Das Modell in Kürze

Das Einspurmodell fasst die beiden Räder jeder Achse zu einem gedachten mittigen Rad zusammen
(daher „Einspur"). Es beschreibt die **Querdynamik** über zwei gekoppelte Zustände:

- **β** – Schwimmwinkel im Schwerpunkt (Winkel zwischen Fahrzeuglängsachse und
  tatsächlicher Fahrtrichtung)
- **θ̇** – Gierrate (wie schnell sich das Fahrzeug um die Hochachse dreht)

Zustands- und Eingangsvektor:

```
x = [x, y, θ, θ̇, β]        u = [δ, v]
```

Die eigentliche Dynamik steckt in den gekoppelten Gleichungen für `β̇` und `θ̈` – die stehen
komplett im Tab **Bewegungsgleichungen** und werden live ausgewertet. Daraus folgen die
Schräglaufwinkel und (über die lineare Reifenkennlinie) die Seitenkräfte:

```
αV = δ − β − (lV/v)·θ̇        FYV = cαV · αV
αH =   − β + (lH/v)·θ̇        FYH = cαH · αH
```

---

## Aufbau des Fensters

| Bereich           | Inhalt                                                        |
|-------------------|---------------------------------------------------------------|
| Links (scrollbar) | Eingaben, Reifenparameter, Live-Zustände, Legende, Buttons    |
| Oben rechts       | Draufsicht – das fahrende Auto mit allen Vektoren             |
| Unten rechts      | Tab-Bereich mit sechs Ansichten (siehe unten)                |

In der **Draufsicht** kannst du das ganze Modell direkt „ablesen":

| Farbe / Symbol         | Bedeutung                                    |
|------------------------|----------------------------------------------|
| grüner Pfeil           | Heading θ (Fahrzeuglängsachse)               |
| oranger Pfeil (gestr.) | tatsächliche Fahrtrichtung `v`, inklusive β  |
| hellblauer Pfeil       | Lenkrichtung δ an der Vorderachse            |
| rote Bögen             | Schräglaufwinkel αV / αH                      |
| magenta / cyan Pfeile  | Seitenkräfte FYV / FYH                        |
| gepunkteter Kreis      | stationärer Kurvenradius R = v / θ̇          |

---

## Experimente zum Ausprobieren

Das ist der eigentliche Lernkern. Nimm dir für jedes Szenario ein paar Minuten.

### 1. Stationäre Kreisfahrt

Stell einen festen Lenkwinkel und eine feste Geschwindigkeit ein und lass laufen. Nach kurzer
Zeit pendelt sich das Fahrzeug in eine gleichmäßige Kreisfahrt ein, der gepunktete Kreis in
der Draufsicht zeigt dir den Radius `R = v/θ̇`. Beobachte, wie β und θ̇ konstant werden: das
ist der **stationäre Zustand**.

### 2. Lenksprung (Sprungantwort)

Der Klassiker aus der Vorlesung. Der Button **Lenksprung** setzt das Fahrzeug zurück und gibt
den aktuellen Lenkwinkel schlagartig als Sprung auf. Im Tab **Zeitverläufe** siehst du, wie β
und θ̇ auf ihren stationären Endwert einschwingen, die gepunkteten Linien markieren genau
diese Sollwerte. Achte darauf, ob das System sauber einläuft oder überschwingt.

### 3. Über- / Untersteuern

Verschieb das Verhältnis der **Schräglaufsteifigkeiten** `cαV` (vorne) und `cαH` (hinten) und
beobachte das Badge unter den Reglern (▲ Übersteuern / ▽ Untersteuern / ● Neutral) sowie die
Linie, die das Auto fährt. Damit erlebst du direkt, wie die Reifenbalance zwischen Vorder- und
Hinterachse das Eigenlenkverhalten bestimmt.

### 4. Stabilität über die Eigenwerte

Im Tab **Eigenwerte** stehen die beiden Eigenwerte λ₁, λ₂ der Systemmatrix:

- `Re(λ) < 0` → Störungen klingen ab (stabil)
- `Re(λ) > 0` → Störungen wachsen (instabil)
- `Im(λ) ≠ 0` → gedämpfte Schwingung (Überschwingen möglich)
- `τ = −1/Re(λ)` → Zeitkonstante; `4τ` ≈ Einschwingzeit

Spiel mit hoher Geschwindigkeit und einer weichen Hinterachse und schau, ab wann das System
kippt. Das verbindet die Fahrdynamik mit der Regelungstheorie.

---

## Die sechs Tabs

| Tab                  | Inhalt                                                                  |
|----------------------|-------------------------------------------------------------------------|
| Zeitverläufe         | β & θ̇, αV & αH, FYV & FYH über der Zeit                                 |
| Reifenkennlinie      | lineare Kennlinie `FY = cα·α` mit aktuellem Arbeitspunkt und ±5°-Grenze  |
| Kausalität           | die Wirkkette δ → αV → FYV → MV → θ̈ → θ̇ → θ als Diagramm               |
| Bewegungsgleichungen | die vollständigen Gleichungen des Modells                               |
| Modellannahmen       | Gültigkeitsgrenzen und Annahmen (siehe unten)                           |
| Eigenwerte           | Stabilitätsanalyse und Zeitkonstante                                    |

---

## Bedienung

**Regler (links):**

| Regler | Bedeutung                          | Bereich         |
|--------|------------------------------------|-----------------|
| `δ`    | Lenkwinkel                         | −15° … 15°      |
| `v`    | Geschwindigkeit                    | 5 … 40 m/s      |
| `cαV`  | Schräglaufsteifigkeit Vorderachse  | 20 … 120 kN/rad |
| `cαH`  | Schräglaufsteifigkeit Hinterachse  | 20 … 120 kN/rad |

**Buttons:**

- **▶ Start / Pause** – Simulation starten bzw. anhalten.
- **↺ Reset** – Zustände, Fahrspur und Zeitreihen auf null zurücksetzen.
- **⚡ Lenksprung** – Reset + sofortiger Start mit dem aktuellen δ als Sprungeingang
  (setzt zusätzlich die stationären Sollwerte für die Zeitplots).

Links unten laufen alle **Live-Zustände** mit (x, y, θ, θ̇, β, αV, αH, FYV, FYH, ay, t).

---

## Modellannahmen & Gültigkeit

- **Kleine Winkel:** `|α| < 5°`, `|β| < 12°` – nur dann ist die Linearisierung gültig.
- **Lineare Reifenkennlinie:** `FY = cα·α`, kein Sättigungsbereich, keine Haftgrenze.
- **Konstante Längsgeschwindigkeit:** `v = const`, keine Längsdynamik (kein Bremsen/
  Beschleunigen).
- **Gültigkeitsbereich:** etwa bis zu einer Querbeschleunigung `ay ≲ 0,4·g`.

> Das Modell ist zur Sicherheit so gebaut, dass es β auf ±12° und θ̇ auf ±60°/s begrenzt und
> bei numerischer Instabilität stoppt. Wenn du es also hart an die Grenze fährst, „sättigt" es
> künstlich, das ist genau der Bereich, in dem das **echte** nichtlineare Reifenverhalten
> anfangen würde zu dominieren. Integriert wird übrigens mit RK4 bei 25 Hz.

---

## Fahrzeugparameter (fest)

| Größe | Wert       | Bedeutung                 |
|-------|------------|---------------------------|
| m     | 1500 kg    | Fahrzeugmasse             |
| Jz    | 2500 kg·m² | Gierträgheitsmoment       |
| lV    | 1,3 m      | Schwerpunkt → Vorderachse |
| lH    | 1,4 m      | Schwerpunkt → Hinterachse |

---

## Datei

`lineares_einspurmodell.py` – alles in einer Datei, keine weiteren Projektdateien nötig.
