import numpy as np
import matplotlib.pyplot as plt 
import matplotlib.cm as cm 
import matplotlib.colors as mcolors 

from struktur import Struktur

class UIPlots: 

    def __init__(self, figsize=(11, 4.5), dpi=120, cmap_name="plasma", farbe_knoten_undeformiert="slategray", farbe_knoten_deformiert="dimgray", grid_linewidth=0.2, margin=0.12, pfeil_skalierung=0.5, knoten_fontsize=5):

        self.figsize = figsize
        self.dpi = dpi 
        self.cmap_name = cmap_name 
        self.farbe_knoten_undeformiert = farbe_knoten_undeformiert
        self.farbe_knoten_deformiert = farbe_knoten_deformiert
        self.grid_linewidth = grid_linewidth
        self.margin = margin 
        self.pfeil_skalierung = pfeil_skalierung
        self.knoten_fontsize = knoten_fontsize

        #einmal die Colormap erzeugen statt wie davor in jeder plot_struktur funktion 
        self.cmap = cm.get_cmap(self.cmap_name)

    #Interne Mehoden hier, alle mit _ gekennzeichnet 
    def _knoten_pos(self, struktur:Struktur, knoten_id: int, u=None, mapping=None, skalierung: float = 1.0):
        '''
        Funktion gibt die Plot-Position eines Knoten zurück 
        - Ohne u/mapping die undeformierte Position (x, z) 
        - Mit u/mapping die defomierte Position (x + u_x * skalierung und z + u_z * skalierung)
        '''
        k = struktur.knoten[knoten_id]
        x, z = k.x, k.z

        if u is None or mapping is None:
            return x, z

        idx = mapping.get(knoten_id, None)

        if idx is None:
            return x, z
        
        ix, iz = idx
        x += float(skalierung) * float(u[ix])
        z += float(skalierung) * float(u[iz])
        return x, z 

    
    def _sammle_plot_marker(self, struktur:Struktur): 
        '''
        Sammelt Knoten-IDs um Marker richtig zu setzen
        - Festlager (x und z sind fix)
        - Loslager (nur eine Richtung fix)
        - Kraftknoten (fx oder fz ungleich 0)
        '''

        festlager_ids = []
        loslager_ids = []
        kraft_ids = []

        for k_id in struktur.aktive_knoten_ids():
            k = struktur.knoten[k_id]

            #Lager 
            if k.fix_x or k.fix_z: 
                if k.fix_x and k.fix_z:
                    festlager_ids.append(k_id) #Festlager
                else: 
                    loslager_ids.append(k_id) #Loslager

            #Kraft 
            if k.kraft_x != 0 or k.kraft_z != 0:
                kraft_ids.append(k_id)

        return festlager_ids, loslager_ids, kraft_ids
    
    def _norm_min_max(self, werte: list[float]):
        '''
        Erzeugt eine Normalize-Objekt mit Min/Max-Werten für die Colormap
        - Wert wird auf 0...1 Skaliert damit cmap() eine passende Farbe liefert
        '''

        if not werte: 
            return None 
        #um ausreiser zu filtern dass nicht alles andere die gleiche farbe hat
        vmin = float(np.percentile(werte, 5))
        vmax = float(np.percentile(werte, 95))

        #Wenn alle Werte gleich sind die Skala minimal aufteilen damit Matplotlib nicht zickt (division durch 0)
        if np.isclose(vmin, vmax):
            vmax = vmin + 1e-9

        #Werte mit mcolors auf einen Farbbereich übersetzen
        return mcolors.Normalize(vmin=vmin, vmax=vmax)
    

    def plot_struktur(self, struktur:Struktur, u = None, mapping = None, skalierung = 1.0, titel = "Struktur", federn_anzeigen = False, knoten_ids_anzeigen = False, lastpfad_knoten=None, heatmap_modus = "Keine", colorbar_anzeigen = True, legende_anzeigen = True):
        '''
        Zeichnet die Struktur

        Geplottet wird: 
        - Undeformierte Knoten (immer)
        - Deformierte Knote/Federn wenn u und mapping vorhanden sind
        - Lager-marker und Kraftpfeile 
        - einfärbung für Heatmap (optional und erst nach Solve)
        - Lastpfade bei deformierter Struktur 
        - Knoten IDs (optional)
        - Federn(optional)
        '''
        #Transparent schalten (paramter alpha) nachdem gesolved wird, um was zu erkennen 
        geloest = (u is not None) and (mapping is not None)
        transparenz = 0.35 if geloest else 1.0

        knoten_vals = None 
        federn_vals = None 
        norm = None 
        colorbar_label = None 

        heatmap_aktiv = (heatmap_modus != "Keine") and geloest

        if heatmap_aktiv: 
            if heatmap_modus == "Verschiebung (Knoten)":
            #Knotenwerte hier |u|
                knoten_vals = {}
                for k_id in struktur.aktive_knoten_ids():
                    if k_id not in mapping: 
                        continue
                    ix,iz = mapping[k_id]
                    ux = float(u[ix])
                    uz = float(u[iz])
                    knoten_vals[k_id] = (ux*ux + uz*uz) ** 0.5 

                #Federwerte (mittelwert der Endknoten somit werden Federn und knoten gemeinsam eingefärbt)
                federn_vals = {}
                for f_id in struktur.aktive_federn_ids():
                    f = struktur.federn[f_id]
                    vi = knoten_vals.get(f.knoten_i)
                    vj = knoten_vals.get(f.knoten_j)

                    if vi is None or vj is None: 
                        continue
                    federn_vals[f_id] = 0.5 * (vi + vj)

                werte = list(knoten_vals.values()) + list(federn_vals.values())
                norm = self._norm_min_max(werte)
                colorbar_label = "Betrag Verschiebung |u|"

            elif heatmap_modus == "Federenergie": 
                federn_vals = struktur.feder_energien_aus_u(u, mapping)
                knoten_vals = struktur.knoten_scores_aus_federenergien(federn_vals, mapping, modus="halb")

                werte = list(knoten_vals.values()) + list(federn_vals.values())
                norm = self._norm_min_max(werte)
                colorbar_label = "Federenergie"

            elif heatmap_modus == "Federkraft":
                federn_vals = struktur.feder_kraefte_aus_u(u, mapping, betrag=True)

                #Knotenwerte aus Federkräften verwendung von max(|N|) aller anliegenden Federn 
                angrenzende_kraefte = {k_id: [] for k_id in mapping.keys()}
                for f_id, N in federn_vals.items():
                    f = struktur.federn[f_id]
                    if f.knoten_i in angrenzende_kraefte: 
                        angrenzende_kraefte[f.knoten_i].append(N)
                    if f.knoten_j in angrenzende_kraefte: 
                        angrenzende_kraefte[f.knoten_j].append(N)

                knoten_vals = {}
                for k_id, lst in angrenzende_kraefte.items():
                    if lst: 
                        knoten_vals[k_id] = float(max(lst))

                werte = list(knoten_vals.values()) + list(federn_vals.values())
                norm = self._norm_min_max(werte)
                colorbar_label = "|N_feder|"

        #Hier noch ein hinweis im plot, falls Heatmap gewählt ist aber noch nicht Solve gedrückt wurde
        if heatmap_modus != "Keine" and not heatmap_aktiv:
            titel = f"{titel} (Heatmap erst nach Solve sichtbar!!)"

        
        #Knoten zeichen und feder (optional)
        fig, ax = plt.subplots(figsize=(11, 4.5), dpi = 120)
        ax.grid(True, linewidth = 0.2)
        ax.margins(0.12)
            
        #Hier federn undeformiert
        if federn_anzeigen:
            for f_id in struktur.aktive_federn_ids():
                f = struktur.federn[f_id]
                k_i = struktur.knoten[f.knoten_i]
                k_j = struktur.knoten[f.knoten_j]

                #Standardfabre für die Federn undeformiert
                col = self.farbe_knoten_undeformiert

                #Falls Heatmap für die Federn aktiv ist Farbe aus federn_vals 
                if federn_vals is not None and norm is not None: 
                    v = federn_vals.get(f_id)
                    if v is not None: 
                        col = self.cmap(norm(v))

                ax.plot([k_i.x, k_j.x], [k_i.z, k_j.z], linewidth=0.8, color=col, alpha=transparenz, zorder = 0)

        #undeformierte Knotenstruktur
        xs, zs, cols = [], [], []

        for k_id in struktur.aktive_knoten_ids():
            k = struktur.knoten[k_id]
            xs.append(k.x)
            zs.append(k.z)

            #Standardfabre bei keiner Heatmap 
            col = self.farbe_knoten_undeformiert

            #Falls Heatmap aktiv: Farbe aus knoten_vals
            if knoten_vals is not None and norm is not None: 
                v = knoten_vals.get(k_id)
                if v is not None: 
                    col = self.cmap(norm(v))

            cols.append(col)

        ax.scatter(xs, zs, s=18, c=cols, alpha=transparenz, label="Knoten undeformiert", zorder = 1)

        #Marker ids
        festlager_ids, loslager_ids, kraft_ids = self._sammle_plot_marker(struktur)

        if festlager_ids:
            x = [self._knoten_pos(struktur, i, u, mapping, skalierung)[0] for i in festlager_ids]
            z = [self._knoten_pos(struktur, i, u, mapping, skalierung)[1] for i in festlager_ids]
            ax.scatter(x, z, s=18, marker="s", color="green", label="Festlager", zorder = 3)

        if loslager_ids:
            x = [self._knoten_pos(struktur, i, u, mapping, skalierung)[0] for i in loslager_ids]
            z = [self._knoten_pos(struktur, i, u, mapping, skalierung)[1] for i in loslager_ids]
            ax.scatter(x, z, s=18, marker="s", color="black", label="Loslager", zorder = 3)

        #Kraft als Pfeil dazu zeichnen 
        pfeil_skalierung = 3.0
        for k_id in kraft_ids:
            k = struktur.knoten[k_id]
            x0, z0 = self._knoten_pos(struktur, k_id, u, mapping, skalierung)
            dx = pfeil_skalierung * k.kraft_x
            dz = pfeil_skalierung * k.kraft_z
            ax.arrow(x0, z0, dx, dz, head_width=0.1, head_length=0.2, length_includes_head=True, color="red", zorder = 5)


        #Knoten ID-Texte 
        if knoten_ids_anzeigen:
            for k_id in struktur.aktive_knoten_ids():
                k = struktur.knoten[k_id]
                x_txt, z_txt = self._knoten_pos(struktur, k_id, u, mapping, skalierung)
                ax.text(x_txt, z_txt, str(k_id), fontsize = 5)

        #Alle Lastknoten rot markieren
        if kraft_ids:
            xs_k = [self._knoten_pos(struktur, k_id, u, mapping, skalierung)[0] for k_id in kraft_ids]
            zs_k = [self._knoten_pos(struktur, k_id, u, mapping, skalierung)[1] for k_id in kraft_ids]
            ax.scatter(xs_k, zs_k, s=18, color="red", marker="o", label="Kraftknoten", zorder=7)


        if u is not None and mapping is not None: 
            #deformierte Knoten und Federn 
            xs_d, zs_d, cols_d = [], [], []

            #deform_knoten_ids = list(mapping.keys())

            deform_knoten_ids = list(struktur.aktive_knoten_ids())

            for k_id in deform_knoten_ids:
                x, z = self._knoten_pos(struktur, k_id, u, mapping, skalierung)
                xs_d.append(x); zs_d.append(z)

                #Standardfarbe 
                col = self.farbe_knoten_deformiert

                #Falls Heatmap aktiv 
                if knoten_vals is not None and norm is not None: 
                    v = knoten_vals.get(k_id)
                    if v is not None: 
                        col = self.cmap(norm(v))

                cols_d.append(col)

            ax.scatter(xs_d, zs_d, s = 18, c=cols_d, edgecolors="black", linewidths=0.4, label = f"Knoten (deformiert x{skalierung})", zorder = 2)

            if federn_anzeigen: 
                for f_id in struktur.aktive_federn_ids():
                    feder = struktur.federn[f_id]

                    if feder.knoten_i not in mapping or feder.knoten_j not in mapping:
                        continue

                    xi, zi = self._knoten_pos(struktur, feder.knoten_i, u, mapping, skalierung)
                    xj, zj = self._knoten_pos(struktur, feder.knoten_j, u, mapping, skalierung)
                    
                    #Standardfarbe Federn deformiert gleich wie knoten 
                    col = self.farbe_knoten_deformiert

                    #Heatmapfarbe für Feder wenn aktiv 
                    if federn_vals is not None and norm is not None: 
                        v = federn_vals.get(f_id)
                        if v is not None:
                            col = self.cmap(norm(v))

                    ax.plot([xi, xj], [zi, zj], linewidth = 0.8, color=col, zorder = 1)

        # Lastpfade anzeigen lassen
        if lastpfad_knoten is not None:
            # pfade kann entweder [pfad] oder [pfad1, pfad2, ...] sein
            pfade = lastpfad_knoten
            if pfade and isinstance(pfade[0], int):
                pfade = [pfade]

            adj = struktur.nachbarschaft()  # sollte nur aktive Federn/Knoten berücksichtigen

            def pos(k_id):
                # entweder komplett deformiert oder komplett undeformiert (kein Mischmodus)
                if (u is not None) and (mapping is not None) and (k_id in mapping):
                    ix, iz = mapping[k_id]
                    k = struktur.knoten[k_id]
                    return (k.x + skalierung * float(u[ix]), k.z + skalierung * float(u[iz]))
                else:
                    k = struktur.knoten[k_id]
                    return (k.x, k.z)

            for pfad in pfade:
                if not pfad or len(pfad) < 2:
                    continue

                # nur Segmente zeichnen, wenn k_i und k_{i+1} wirklich Nachbarn sind
                seg_x = []
                seg_z = []

                for a, b in zip(pfad[:-1], pfad[1:]):
                    if b in adj.get(a, []):
                        xa, za = pos(a)
                        xb, zb = pos(b)

                        # neuen Segment-Start?
                        if not seg_x:
                            seg_x = [xa, xb]
                            seg_z = [za, zb]
                        else:
                            seg_x.append(xb)
                            seg_z.append(zb)
                    else:
                        # Segment abschließen, Sprung wird nicht gezeichnet
                        if len(seg_x) >= 2:
                            ax.plot(seg_x, seg_z, linewidth=2, color="red", zorder=10)
                        seg_x, seg_z = [], []

                # letztes Segment zeichnen
                if len(seg_x) >= 2:
                    ax.plot(seg_x, seg_z, linewidth=2, color="red", zorder=10)

        # Colorbar also die Farblegende
        if colorbar_anzeigen and heatmap_aktiv and norm is not None:
            mappable = cm.ScalarMappable(norm=norm, cmap=self.cmap)
            mappable.set_array([])  
            fig.colorbar(mappable, ax=ax, fraction=0.03, pad=0.02, label=colorbar_label)

        ax.set_aspect("equal", adjustable="box")
        ax.set_title(titel)
        ax.set_xlabel("x")
        ax.set_ylabel("z")

        if legende_anzeigen:
            handles, labels = ax.get_legend_handles_labels()
            #nur Anzeigen wenn labels wirklich existiern 
            if labels:
                ax.legend(loc = "upper right")
        return fig