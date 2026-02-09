# Klasse zum erstellen der Knotenpunkte der mechanischen Struktur
# Knotenpositionen erst Mal in 2D mit x und z Koordinaten

class Knoten:
    def __init__(self, id, x, z, knoten_aktiv=True, fix_x=True, fix_z=True, kraft_x=0.0, kraft_z=0.0):
        self.id = id
       
        # Position
        self.x = x
        self.z = z
        
        # ob Knoten noch da ist oder nicht (für Optimieren)
        self.knoten_aktiv = knoten_aktiv
        
        # Freiheitsgrade vom Knoten regulieren
        self.fix_x = fix_x
        self.fix_z = fix_z
        
        # Kraft von 0 bis 100N dann
        self.kraft_x = kraft_z
        self.kraft_z = kraft_x


    