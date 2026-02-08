# Klasse für die Federn

class Feder:
    def __init__(self, id, knoten_i, knoten_j, steifigkeit, feder_aktiv=True):
        self.id = id

        # Knoten zwischen welche die Feder liegt
        self.knoten_i = knoten_i
        self.knoten_j = knoten_j

        # steifigkeit der Feder
        self.steifigkeit = steifigkeit
        
        # ob Feder aktiv ist
        self.feder_aktiv = feder_aktiv