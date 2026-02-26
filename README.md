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
    - git clone <REPO-URL>
    - cd <REPO-ORDNER>
- Virtuelle Umgebung erstellen:
    - python -m venv .venv 
    - .venv/Scripts/activate (Windows)
- Alle nötigen packages installieren: 
    - pip install -r requirements.txt
- Anwendung starten: 
    - streamlit run ui.py 

Für die zweite Möglichkeit um mit der Anwendung arbeiten zu können muss man lediglich diesem Link folgen: https://mechanische-strukturen-simulieren-und-optimieren.streamlit.app. Allerdings kann man hierbei keinen Code ändern/überarbeiten sondern nur mit dem bereits vorhandenem UI interagieren.  

# Implementierte Erweiterungen
## Heatmap-Visualisierung für Verschiebung, Federenergie und Federkraft 

## Verschiedene Optimierungsstrategien (energie-basiert und lastpfad-gestützt)

## Anzeige von Lastpfad 

## Strukturvergleich Nebeneineder 

## GIF-Export der Optimierung  

## Checkpoint-System (TinyDB + Pickle)
