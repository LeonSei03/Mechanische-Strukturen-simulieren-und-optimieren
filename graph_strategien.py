import networkx as nx

def dijkstra_lastpfad(struktur, energien, eps=1e-12, weight_mode="inv_energy"):
    """Liefert uns einen gewichteten Lastpfad, in Form einer Liste der Knoten-IDs mithilfe des Dijkstra Algorithmus"""

    last_ids = struktur.last_knoten_id()
    lager_ids = struktur.lager_knoten_id()

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

        val = float(energien.get(f_id, 0.0))  # Energie oder Kraft

        # inv_energy / inv_force: bevorzugt hohe val (weil cost = 1/(val+eps) klein wird)
        if weight_mode in ("inv_energy", "inv_force"):
            weight = 1.0 / (val + eps)
        else:
            weight = val + eps

        G.add_edge(i, j, weight=weight)

    # bestes Lager wählen
    best_path = []
    best_cost = float("inf")

    for ziel in lager_ids:
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
    """Erweitert eine Knotenmenge um Nachbarschaftsringe im aktiven Graphen.

    ring=0 -> nur start_nodes
    ring=1 -> start_nodes + direkte Nachbarn
    ring=2 -> start_nodes + Nachbarn der Nachbarn
    """
    start_nodes = set(start_nodes)

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
        if not frontier:
            break

    return besucht