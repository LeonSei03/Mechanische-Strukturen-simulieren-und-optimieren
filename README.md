# Projektbeschreibung 
Im Rahmen der Lehrveranstaltung Softwaredesign wurde dieses Projekt entwickelt, welches eine interaktive Web-Anwendung zur Modellierung, Simulation und Topologieoptimierung mechanischer 2D-Strukturen enthält.

Die Struktur wird anhand der Anleitung als Feder-Knoten-Modell aufgebaut, bestehend aus: 
- Knoten (2 Freiheitsgrade in x- und z-Richtung)
- Federn zwischen den Knoten (horizontal, vertikal und diagonal)
- Randbedingungen (Festlager / Loslager)
- Extern eingeleiteten Kräften 

Die Anwendung erlaubt Grundsätzlich: 
- Aufbauen und Visualisieren einer Gitterstruktur
- Setzen von Kräften und Lagern 
- Lösen des Gleichungssystems `K * u = F`
- Visualisierung der Verformung
- Visualisierung des Lastpfads 
- Visualisierung unterschiedlicher Heatmaps
- Iterative Topologieoptimierung mit adaptivem Rollback 
- Topologieoptimierung mittels Dijkstra-Algorithmus (Kraftbasiert)
- Topologieoptimierung Energiebasiert
- Speichern, Laden und weiterarbeiten von optimierten Strukturen (TinyDB + Pickle)
- Optionaler GIF-Export eines Optimierungsverlaufs 
- Downloads der Strukturen als .png
- Vergleich einer Referenz- und einer Aktuellen-Struktur 

Die ganze Anwendung wir vollständig mit Streamlit umgesetzt. 

# Messerschmitt-Bölkow-Blohm Balken

# Installation 
Um mit dem Anwenung arbeiten zu können gibt es zwei verschiedene möglichkeiten. 

Die erste Möglichkeit ist hierbei das ganze Repo zu Klonen, man kann selbst am Code weiter arbeiten und weiter optimieren. Dies Funktioniert so:
- Repository Klonen: 
    - git clone https://github.com/LeonSei03/Mechanische-Strukturen-simulieren-und-optimieren.git
    - cd Mechanische-Strukturen-simulieren-und-optimieren
- Virtuelle Umgebung erstellen:
    - python -m venv .venv 
    - .venv/Scripts/activate (Windows)
- Alle nötigen packages installieren: 
    - pip install -r requirements.txt
- Anwendung starten: 
    - streamlit run ui.py 

Für die zweite Möglichkeit um mit der Anwendung arbeiten zu können muss man lediglich diesem Link folgen: https://mechanische-strukturen-simulieren-und-optimieren.streamlit.app. Allerdings kann man hierbei keinen Code ändern/überarbeiten sondern nur mit dem bereits vorhandenem UI interagieren.  
# Grobe Anleitung UI 
### Sidebar
Die Sidebar links enthält Einstellungen, welche tabübergreifend wirken. 
#### Geometrie / Lager 
- nx / nz: Anzahl der Knoten in x- und z-Richtung
- dx / dz Knotenabstand (Geometrie)
- Lager (Start)
    - Knoten einzeln: setzt Default-Lager auf zwei Knoten (links unten Festlager, rechts unten Loslager)
    - Knotenspalte: setzt die ganze linke Spalte als Feslager
- Neue Struktur erzeugen: erstellt eine neue Default-Struktur und setzt UI-Entwürfe/Erbenisse zurück 

#### Darstellung
- Skalierung Deformation: verstärkt/verkleinert die sichtbare deformierte Form (nur sichtbar nach Solve)
- Federn anzeigen: zeichnet die Federn 
- Knoten-IDs anzeigen: blendet die Knoten IDs im Plot ein 
- Legende anzeigen: blendet die Marker-Legende ein und aus (Lager/Kraftknoten)
- Lastpfad anzeigen: zeigt (falls vorhanden) den Lastpfad im Plot 

#### Heatmap 
- Keine: normale Darstellung 
- Verschiebung (Knoten): färbt nach Betrag der Verschiebung (nur nach Solve sichtbar)
- Federenergie / Federkraft: färbt Federn/Knoten nach Energie bzw. Kraft (nur nach Solve sichtbar)
- Hinweis: Bei Federenergie/Federkraft werden die Federn automatisch eingeblendet, auch wenn die Checkbox aus ist.

### Tab Ansicht 
Bei Start der Anwendung wird automatisch eine Default-Struktur erzeugt mit der man sofort arbeiten kann: 
- Default-Kraft wirkt mittig oben nach unten (bei geradem nx auf zwei Knoten verteilt)
- Default-Lager: je nach "Lager (Start)" in der Sidebar 

#### Workflow: Struktur definieren -> Anwenden -> Lösen
1. Struktur erstellen (Sidebar -> **Neue Struktur erzeugen**)
2. Kräfte & Lager entwerfen (Editor-Bereich)
    - Man wählt eine Knoten-ID und setzt Werte
    - Mit **IN Entwurf speichern** landen diese erst in einer Entwurftabelle (noch nicht in der Struktur)
3. Entwürfe auf Struktur anwenden
    - Erst jetzt werden alle Entwürfe wirklich in die Struktur übernommen 
4. Solve 
    - Löst das System und zeigt die deformierte Struktur (abhängig von **Skalierung Deformation**)

#### Kräfte-Editor 
- In Entwurf speichern: merkt sich Kraftwerte für den gewählten Knoten (Entwurfsliste wird darunter angezeigt)
- Aus Entwurf löschen: entfernt Entwurf und löscht die Kraft auch aus der Struktur 
- Alle Kräfte entfernen: setzt alle vorhandenen Kräfte auf 0 

#### Lager-Editor 
- Setzmodus 
    - Knoten einzeln: nur ausgewählte Knoten setzen 
    - Knotenspalte: setzt/entfernt Lager für die gesamte Spalte des ausgewählten Knotens
- Lagertyp welchen man will auswählen

### Tab Optimierung 
Hier wird eine Topologieoptimierung durchgeführt, mit dem Ziel die aktive Masse (1 Knoten = 1 kg) zu reduzieren

1. Optimierung initialisieren 
- Strategie 
    - Energiebasiert (lokal) 
    - Dijkstra-Lastpfad (global geschützt), mit "Pfad-Schutz(Nachbarschaft)
- Ziel-Massenanteil z.B 0,50 wählen -> Hälfte der Startmasse behalten 
- Max. Iterationen, max_entfernen_pro_iter, u_faktor (Rollback/Limit-Parameter)
- Button **Optimierung initialisieren** übernimmt alle eingestellten Parameter 

2. Optimierung laufen lassen 
- Weiter (1 Schritt): genau eine Iteration 
- Auto-Weiter / Stop: iteriert automatisch pro UI-Rerun, Stop hält nach dem aktuellen Schritt an 
- Optimierung komplett durchlafuen (schnell): läuft ohne Stop-Möglichkeiten bis zum Ende 

#### Checkpoints (Speichern / Laden)
- Speichern: speichert den Optimierten-Zustand als Checkpoint inklusive Paramter/Info 
- Laden / Fortsetzen: lädt einen ausgewählten Checkpoint und man kann die Optimierung fortsetzen 
- Checkpoint löschen: löscht den ausgewählten Checkpoint 
#### GIF Recording 
- GIF Recording aktiv: zeichnet während der Optimierung Frames auf 
- Danach: FPS wählen -> GIF erstellen -> Download 

### Tab Varlaufplots 
Zeift Verlauf über Iteration: 
- Gesamtenergie
- Materialanteil 
- Aktive Knoten 
- maximale Verschiebung vs. Grenze 

### Tab Vergleich 
Vergleich von Referenz-Struktur vs. Aktuell: 
- Button **Aktuelle Struktur als Referenz speichern** speichert eine Kopie der aktuellen Struktur 
- Checkbox **Deformierte Struktur anzeigen** blendet (falls Solve vorhanden) die deformierte Struktur ein

Wechselt man oben zum Tab Optimierung kann man zwei verschiedene Optimierungsstrategien auswählen. Weiters kann man den gewünschten Masseanteil welcher erreicht werden soll mit einem Slider einstellen. Zudem kann man noch eine Checkbox *GIF Recording aktiv* anhaken, dabei kann nach der Optimierung das geschehen visuell nachvollzogen werden. Wird nun der Button *Optimierung initialisieren* geklickt werden die eingestellten Parameter übernommen und man kann die Optimierung anhand verschiedener Optionen durchführen. Weiters kann die Optimierte Struktur gespeichert werden, oder eine bereits optimierte Struktur aus der Datenbank geladen werden um weiter daran zu arbeiten. 

### Tab Verlaufplots 
In diesem Tab werden die verläufe pro Iteration der Optimierung dargestellt.

### Tab Vergleich 
In diesem Tab kann man eine Referenzstruktur speichern, um diese anschnließend mit zum Beispiel einer Optimierten Struktur zu vergleichen 
# Implementierte Erweiterungen
#### Heatmap-Visualisierung für Verschiebung, Federenergie und Federkraft 

#### Verschiedene Optimierungsstrategien (energie-basiert und lastpfad-gestützt)

#### Anzeige von Lastpfad 

#### Verlaufplots

#### Strukturvergleich Nebeneineder 

#### GIF-Export der Optimierung  

#### Checkpoint-System (TinyDB + Pickle)
