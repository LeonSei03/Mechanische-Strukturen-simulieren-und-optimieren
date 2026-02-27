import networkx as nx

def dijkstra_lastpfad(struktur, energien, eps=1e-12, weight_mode="inv_energy"):
    """
    Bestimmt uns einen gewichteten Lastpfad zwischen einem Lastknoten und einem Lagerknoten mithilfe des Dijkstra Algorithmus
    
    Idee:
    Hohe Energie / hohe Kraft -> hat kleine Kosten
    Disjkstra bevorzugt den Weg dann und das wird zum Hauptlastpfad der Struktur

    Argumente:
        struktur -> Instanz der Struktur Klasse mit Knoten und Feder Infos
        energien -> Dict
        eps -> gegen division durch 0, Falls Kraft 0 ist
        weightmode
    
    return:
    list[int]:
        Gibt eine Liste an Knoten-IDs des besten Lastpfades zurück.
    """

    # aktuell Last- und Lagerknoten bestimmen
    last_ids = struktur.last_knoten_id()
    lager_ids = struktur.lager_knoten_id()

    # wenn wir keine Randbedingungen haben ist auch kein Pfad möglich
    if not last_ids or not lager_ids:
        return []

    start = last_ids[0]

    # Netzwerk Graph erzeugen
    G = nx.Graph()

    # aktive Knoten hinzufügen
    for k_id in struktur.aktive_knoten_ids():
        G.add_node(k_id)

    # Aktive Federn als gewichtete Kanten hinzufügen
    for f_id in struktur.aktive_federn_ids():
        feder = struktur.federn[f_id]
        i = feder.knoten_i
        j = feder.knoten_j

        # zur Sicherheit nur Kanten zwischen aktiven Knoten
        if i not in G or j not in G:
            continue

        # aus Energie oder Kraft Dict
        val = float(energien.get(f_id, 0.0))

        # Gewicht berechnen
        # hohes val -> kleines Gewicht
        # kleines val -> hohes Gewicht
        if weight_mode in ("inv_energy", "inv_force"):
            weight = 1.0 / (val + eps)
        else:
            weight = val + eps

        G.add_edge(i, j, weight=weight)

    # kürzesten Pfad bestimmen
    best_path = []
    best_cost = float("inf")

    for ziel in lager_ids:
        # falls start- oder Zielknoten nicht merh aktiv sind
        if ziel not in G or start not in G:
            continue

        try:
            path = nx.shortest_path(G, source=start, target=ziel, weight="weight")
            cost = nx.path_weight(G, path, weight="weight")
        except Exception:
            continue

        if cost < best_cost:
            best_cost = cost
            best_path = path

    return best_path

def knoten_in_ring_nachbarschaft(struktur, start_nodes, ring=1):
    """
    Erweitert eine Knotenmenge um Nachbarschaftsringe im aktiven Graphen.

    Idee:
    Der Dijkstra Pfad gibt uns eine einzelne Linie an Knoten, also der Hauptlastpfad. 
    Aber damit der nicht nur eine Reihe an Knoten ist und ultra dünn ist, wird der Pfad um dessen
    Nachbarn und wiederrum dessen Nachbarn erweitert.
    
    ring=0 -> nur start_nodes
    ring=1 -> start_nodes + direkte Nachbarn
    ring=2 -> start_nodes + Nachbarn der Nachbarn
    """
    start_nodes = set(start_nodes)

    # falls kein Ring oder keine Startknoten
    if ring <= 0 or not start_nodes:
        return start_nodes

    adj = struktur.nachbarschaft()

    besucht = set(start_nodes)
    frontier = set(start_nodes)

    for _ in range(ring):
        next_frontier = set()

        for node in frontier:
            for nb in adj.get(node, []):
                if nb not in besucht:
                    besucht.add(nb)
                    next_frontier.add(nb)

        frontier = next_frontier
        # wenn keine Nachbarn merh vorhanden sind
        if not frontier:
            break

    return besucht