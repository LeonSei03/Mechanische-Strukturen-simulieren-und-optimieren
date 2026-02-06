from knoten import Knoten
from feder import Feder

# Klasse die das Gerüst der mechanischen Struktur aufbaut auf den Knoten und den Federn
class Struktur:
    def __init__(self):
        # dictionary für alle Knoten und Feder, keine Listen, weil sich beim Löschen dann die Indices ändern würde
        self.knoten: dict[int, Knoten] = {}
        self.federn: dict[int, Feder] = {}
        self.knoten_id_zaehler = 0
        self.feder_id_zaehler = 0

        # Anzahl der Knoten in x- und in z-Richtung
        self.anzahl_x = None
        self.anzahl_z = None

    # Funktion um das Gitter zu erzeugen
    def gitter_erzeugen_knoten(self, anzahl_x: int, anzahl_z: int, dx: float, dz: float):
        self.anzahl_x = anzahl_x
        self.anzahl_z = anzahl_z

        # Gitter bauen im dictionary mit ganz vielen Knoten
        for i in range(anzahl_x):
            for j in range(anzahl_z):
                x = i * dx # dx als Abstand zwischen den Knoten, also die Federlänge dann
                z = j * dz

                k_id = self.knoten_id_zaehler
                self.knoten[k_id] = Knoten(id=k_id, x=x, z=z) # im dictionary jeden neuen Knoten abspeichern
                self.knoten_id_zaehler += 1

    def gitter_erzeugen_federn():
        # über alle knoten drüber iterieren und eine feder dazwischen abspeichern, x richutng, z richtung und diagonal
        pass

    def knoten_entfernen():
        pass

    def feder_entfernen():
        pass