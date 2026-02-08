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

    # Funktion um Knotenobjekte zum Dict hinzuzufügen
    def knoten_hinzufuegen(self, x: float, z: float) -> int:
        k_id = self.knoten_id_zaehler

        self.knoten[k_id] = Knoten(id=k_id, x=x, z=z) # im dictionary jeden neuen Knoten abspeichern
        self.knoten_id_zaehler += 1
        return k_id


    # Funktion um das Gitter aus Knoten zu erzeugen
    def gitter_erzeugen_knoten(self, anzahl_x: int, anzahl_z: int, dx: float, dz: float):
        self.anzahl_x = anzahl_x
        self.anzahl_z = anzahl_z

        # Gitter bauen im dictionary mit ganz vielen Knoten
        for j in range(anzahl_z):
            for i in range(anzahl_x):
                x = i * dx # dx als Abstand zwischen den Knoten, also die Federlänge dann
                z = j * dz

                self.knoten_hinzufuegen(x, z)

    
    # Funktion um Federobjekte ins Dict zu schreiben
    def feder_hinzufuegen(self, knoten_i: int, knoten_j: int, steifigkeit: float) -> int:
        f_id = self.feder_id_zaehler

        self.federn[f_id] = Feder(id=f_id, knoten_i=knoten_i, knoten_j=knoten_j, steifigkeit=steifigkeit)
        self.feder_id_zaehler += 1
        return f_id


    # Funktion um aus einer Gitterposition die passende Knoten id zurückzugeben
    def knoten_id(self, i: int, j: int) -> int:
        return j * self.anzahl_x + i


    # Funktion um das Gitter aus den Federn zu erzeugen, Feder kommt immer zwischen zwei benachbarte Knoten
    def gitter_erzeugen_federn(self, k_h: float, k_v: float, k_d: float): # WICHTIG: ich weiß nicht ob die steifigkeiten der federn unterschiedlich sind je nachdem ob sie hori, verti, dia sind. also mal drei verschiedene Steifigkeiten die übergeben werden müssen
        # über alle knoten drüber iterieren und eine feder dazwischen abspeichern, x richutng, z richtung und diagonal
        for j in range(self.anzahl_z):
            for i in range(self.anzahl_x):

                a = self.knoten_id(i, j) # aktuelle Knoten ID abspeichern

                # Feder zwischen aktuellem Knoten (a) und Knoten rechts davon
                if i + 1 < self.anzahl_x:
                    b = self.knoten_id(i+1, j)
                    self.feder_hinzufuegen(a, b, k_h)

                # Feder zwischen a und drunter liegendem Knoten
                if j + 1 < self.anzahl_z:
                    c = self.knoten_id(i, j+1)
                    self.feder_hinzufuegen(a, c, k_v)

                # Feder zwischen a und diagonal liegendem Knoten, rechts oben und unten rechts
                if i + 1 < self.anzahl_x and j + 1 < self.anzahl_z:
                    d = self.knoten_id(i + 1, j + 1) # Feder diagonal negative Steigung (zweiter Knoten rechts unterhalb von a)
                    self.feder_hinzufuegen(a, d, k_d)

                    # Feder diagonal positive Steigung (gehen mit ausgangsknoten eins rechts und zweiten Knoten eins nach unten)
                    e = self.knoten_id(i + 1, j)
                    f = self.knoten_id(i, j + 1)
                    self.feder_hinzufuegen(e, f, k_d)


    # Funktion zum entfernen von Knoten, für die Optimierung
    def knoten_entfernen(self, k_id: int):
        if k_id in self.knoten:
            self.knoten[k_id].knoten_aktiv = False # knoten_aktiv Variable am Key k_id auf False setzen

        # alle Federn die am Knoten dran sind deaktivieren
        for feder in self.federn.values():
            if not feder.feder_aktiv:
                continue
            if self.knoten_geschuetzt(k_id):
                return
            if feder.knoten_i == k_id or feder.knoten_j == k_id:
                feder.feder_aktiv = False
    

    # Funktion zum deaktivieren von Federn, für die Optimierung
    def feder_entfernen(self, f_id: int):
        if f_id in self.federn:
            self.federn[f_id].feder_aktiv = False


    # Funktion um Knoten zu schützen, dass sie nicht entfernt werden können
    def knoten_geschuetzt(self, k_id: int) -> bool:
        k = self.knoten[k_id]
        return (k.fix_x or k.fix_z)