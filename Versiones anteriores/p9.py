# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import math
import json
import os
import traceback # Para imprimir errores detallados

# --- Importaciones críticas ---
# Intentar importar y mostrar error si faltan
try:
    from fastkml import kml
    from shapely.geometry import Polygon, box
except ImportError as e:
    root_check = tk.Tk()
    root_check.withdraw() # Ocultar ventana tk extra
    messagebox.showerror("Error de Importación Crítica",
                         f"Falta una librería esencial ({e}).\n"
                         "El programa no puede continuar.\n"
                         "Por favor, instálalas en tu terminal:\n"
                         "pip install fastkml shapely")
    exit()

try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import matplotlib.patches as patches
except ImportError as e:
     root_check = tk.Tk()
     root_check.withdraw()
     messagebox.showerror("Error de Importación Crítica",
                         f"Falta la librería matplotlib ({e}).\n"
                         "El programa no puede continuar.\n"
                         "Por favor, instálala en tu terminal:\n"
                         "pip install matplotlib")
     exit()


# --- Funciones de Cálculo y Lectura KML ---

# <<< VERSIÓN 3: Intenta iterar k.features directamente >>>
def leer_primer_poligono_kml(filepath):
    """
    Lee KML y devuelve BBox. Intenta iterar k.features directamente
    para solucionar el error 'list object is not callable'.
    """
    print("\n--- Iniciando leer_primer_poligono_kml (v3) ---")
    if not os.path.exists(filepath):
        print(f"DEBUG: Archivo no existe: {filepath}")
        return {"error": f"Archivo no encontrado: {filepath}"}
    print(f"DEBUG: Archivo encontrado: {filepath}")

    try:
        with open(filepath, 'rt', encoding='utf-8') as f: kml_string = f.read()
        print("DEBUG: Archivo KML leído.")

        k = kml.KML()
        print(f"DEBUG: Objeto KML inicializado: {type(k)}")
        k.from_string(kml_string.encode('utf-8'))
        print("DEBUG: k.from_string ejecutado.")

        feature_polygon = None

        # --- INTENTO DE CORRECCIÓN (v3) ---
        if not hasattr(k, 'features'):
             print("ERROR DEBUG: Objeto KML parseado no tiene atributo 'features'.")
             return {"error": "Objeto KML parseado no tiene atributo 'features'."}

        print(f"DEBUG: Intentando acceder a k.features (tipo: {type(k.features)})...")
        try:
            top_level_features = k.features
            if callable(top_level_features):
                 print("DEBUG: k.features SÍ era llamable, obteniendo lista...")
                 top_level_features = list(top_level_features())
            elif not hasattr(top_level_features, '__iter__'):
                 print(f"ERROR DEBUG: k.features (tipo {type(top_level_features)}) no es llamable NI iterable.")
                 return {"error": "Error interno: k.features no es llamable ni iterable."}
            else:
                 print("DEBUG: k.features NO es llamable, se usará directamente como iterable.")

            print(f"DEBUG: Iterando sobre top_level_features (tipo: {type(top_level_features)})")
            for i, feature in enumerate(top_level_features):
                print(f"\nDEBUG: Procesando feature nivel superior #{i}: {type(feature)}")
                if hasattr(feature, 'geometry') and isinstance(feature.geometry, Polygon):
                    print("DEBUG:   ¡Es un polígono!")
                    feature_polygon = feature.geometry
                    break
                elif hasattr(feature, 'features'):
                    print(f"DEBUG:   Es un contenedor, buscando dentro...")
                    if not hasattr(feature, 'features'):
                         print("DEBUG:   feature no tiene atributo 'features'.")
                         continue
                    sub_level_features = feature.features
                    print(f"DEBUG:   Intentando acceder a feature.features (tipo: {type(sub_level_features)})...")
                    if callable(sub_level_features):
                        print("DEBUG:     feature.features SÍ era llamable, obteniendo lista...")
                        sub_level_features = list(sub_level_features())
                    elif not hasattr(sub_level_features, '__iter__'):
                         print(f"ERROR DEBUG:   sub_level_features (tipo {type(sub_level_features)}) no es llamable NI iterable.")
                         continue
                    else:
                         print("DEBUG:     feature.features NO es llamable, se usará directamente.")

                    print(f"DEBUG:   Iterando sobre sub_level_features (tipo: {type(sub_level_features)})")
                    for j, subfeature in enumerate(sub_level_features):
                        print(f"DEBUG:     Procesando subfeature #{j}: {type(subfeature)}")
                        if hasattr(subfeature, 'geometry') and isinstance(subfeature.geometry, Polygon):
                            print("DEBUG:       ¡Es un polígono!")
                            feature_polygon = subfeature.geometry
                            break
                    if feature_polygon:
                        print("DEBUG:   Polígono encontrado en subfeature, saliendo.")
                        break
                else:
                    print("DEBUG:   No es polígono ni contenedor.")
        except TypeError as te:
            print(f"\nERROR DEBUG: TypeError incluso al intentar iterar directamente: {te}")
            print("--- TRACEBACK DETALLADO (TypeError en iteración directa v3) ---")
            traceback.print_exc()
            print("--------------------------------------------------------------")
            return {"error": f"TypeError persistente al acceder a features: {te}"}
        # --- FIN INTENTO DE CORRECCIÓN (v3) ---

        # Procesar si encontramos un polígono
        if feature_polygon:
            print(f"DEBUG: Polígono encontrado: {type(feature_polygon)}")
            if not hasattr(feature_polygon, 'exterior') or not hasattr(feature_polygon.exterior, 'coords'):
                 return {"error": "Geometría de polígono inválida (sin exterior.coords)."}
            coords_obj = feature_polygon.exterior.coords
            print(f"DEBUG: Tipo de coords_obj: {type(coords_obj)}")
            print(f"DEBUG: Primeras 5 coords (si existen): {coords_obj[:5]}")
            if not callable(Polygon):
                 print("FATAL DEBUG: ¡Shapely Polygon no es llamable!")
                 return {"error": "Error interno: Shapely Polygon no es llamable."}
            print(f"DEBUG: Intentando crear Shapely Polygon con coords de tipo {type(coords_obj)}...")
            shapely_poly = Polygon(coords_obj)
            print(f"DEBUG: Shapely Polygon creado: {type(shapely_poly)}")
            if not hasattr(shapely_poly, 'bounds'):
                 print("ERROR DEBUG: shapely_poly no tiene atributo 'bounds'")
                 return {"error": "No se pudo obtener el bounding box del polígono."}
            bounds_obj = shapely_poly.bounds
            print(f"DEBUG: Tipo de shapely_poly.bounds: {type(bounds_obj)}")
            minx, miny, maxx, maxy = bounds_obj
            print(f"DEBUG: Bounding Box: ({minx}, {miny}) a ({maxx}, {maxy})")
            return {'min_x': minx, 'min_y': miny, 'max_x': maxx, 'max_y': maxy}
        else:
            print("DEBUG: No se encontró polígono en la estructura KML.")
            return {"error": "No se encontró ningún polígono en la estructura KML procesada."}

    except Exception as e:
        print("\n--- ERROR DETALLADO en leer_primer_poligono_kml (Bloque General v3) ---")
        traceback.print_exc()
        print("-----------------------------------------------------------------")
        return {"error": f"Error al leer o parsear KML: {e}"}

def calcular_unidades_terreno(
    minX_outer, minY_outer, maxX_outer, maxY_outer,
    distancia_corona, largo_base, ancho_base):
    """
    Calcula la posición de unidades 'escalera' y 'base'.
    Devuelve dict con 'escaleras', 'bases', 'inner_coords' o 'error'.
    """
    escaleras = []
    bases = []
    resultado = {}
    if largo_base <= 0 or ancho_base <= 0 or distancia_corona < 0: return {"error": "Dimensiones deben ser > 0, Corona >= 0."}
    if maxX_outer <= minX_outer or maxY_outer <= minY_outer: return {"error": "Coords. terreno exterior inválidas."}
    try:
        lado_escalera = largo_base
        minX_inner = minX_outer + distancia_corona; minY_inner = minY_outer + distancia_corona
        maxX_inner = maxX_outer - distancia_corona; maxY_inner = maxY_outer - distancia_corona
        if minX_inner >= maxX_inner or minY_inner >= maxY_inner: return {"error": f"La distancia de la corona ({distancia_corona}) es demasiado grande."}
        resultado['inner_coords'] = {'min_x': minX_inner, 'min_y': minY_inner, 'max_x': maxX_inner, 'max_y': maxY_inner}
        W_inner = maxX_inner - minX_inner; H_inner = maxY_inner - minY_inner
        W_base_available = W_inner - 2 * lado_escalera; H_base_available = H_inner - 2 * lado_escalera
        num_base_X = 0; num_base_Y = 0
        if W_base_available >= 0 and H_base_available >= 0 and ancho_base > 0 and largo_base > 0 :
            num_base_X = math.floor(W_base_available / ancho_base)
            num_base_Y = math.floor(H_base_available / largo_base)
        W_bloque_base = num_base_X * ancho_base; H_bloque_base = num_base_Y * largo_base
        W_total_estructura = W_bloque_base + 2 * lado_escalera; H_total_estructura = H_bloque_base + 2 * lado_escalera
        W_hueco_total = W_inner - W_total_estructura; H_hueco_total = H_inner - H_total_estructura
        if W_hueco_total < -1e-9 or H_hueco_total < -1e-9: return {"error": f"Área interna no cabe ni las 4 escaleras (lado {lado_escalera})."}
        W_margen = W_hueco_total / 2; H_margen = H_hueco_total / 2
        coords_escalera = {
            "BL": ((minX_inner + W_margen, minY_inner + H_margen), (minX_inner + W_margen + lado_escalera, minY_inner + H_margen + lado_escalera)),
            "BR": ((maxX_inner - W_margen - lado_escalera, minY_inner + H_margen), (maxX_inner - W_margen, minY_inner + H_margen + lado_escalera)),
            "TL": ((minX_inner + W_margen, maxY_inner - H_margen - lado_escalera), (minX_inner + W_margen + lado_escalera, maxY_inner - H_margen)),
            "TR": ((maxX_inner - W_margen - lado_escalera, maxY_inner - H_margen - lado_escalera), (maxX_inner - W_margen, maxY_inner - H_margen))
        }
        for key, (bl, tr) in coords_escalera.items(): escaleras.append({"type": f"escalera_{key}", "bl": bl, "tr": tr})
        if num_base_X > 0 and num_base_Y > 0:
            base_start_x = minX_inner + W_margen + lado_escalera; base_start_y = minY_inner + H_margen + lado_escalera
            for j in range(num_base_Y):
                for i in range(num_base_X):
                     unit_bl_x = base_start_x + i * ancho_base; unit_bl_y = base_start_y + j * largo_base
                     unit_tr_x = unit_bl_x + ancho_base; unit_tr_y = unit_bl_y + largo_base
                     bases.append({"type": "base", "row": j, "col": i, "bl": (unit_bl_x, unit_bl_y), "tr": (unit_tr_x, unit_tr_y)})
        resultado['escaleras'] = escaleras; resultado['bases'] = bases
        return resultado
    except Exception as e:
        print("--- ERROR DETALLADO en calcular_unidades_terreno ---")
        traceback.print_exc()
        print("--------------------------------------------------")
        return {"error": f"Error inesperado durante el cálculo: {e}"}


def visualizar_en_canvas(ax, outer_coords, inner_coords, escaleras, bases, params):
    """Dibuja en un objeto Axes de Matplotlib proporcionado."""
    try:
        ax.clear()
        outer_width = outer_coords['max_x'] - outer_coords['min_x']
        outer_height = outer_coords['max_y'] - outer_coords['min_y']
        inner_width = inner_coords['max_x'] - inner_coords['min_x']
        inner_height = inner_coords['max_y'] - inner_coords['min_y']
        lado_escalera = params['largo_base']
        ancho_base = params['ancho_base']
        largo_base = params['largo_base']
        rect_outer = patches.Rectangle((outer_coords['min_x'], outer_coords['min_y']), outer_width, outer_height, linewidth=1.5, edgecolor='black', facecolor='none', label='Bounding Box KML')
        ax.add_patch(rect_outer)
        rect_inner = patches.Rectangle((inner_coords['min_x'], inner_coords['min_y']), inner_width, inner_height, linewidth=1, edgecolor='blue', linestyle='--', facecolor='none', label='Área Interna')
        ax.add_patch(rect_inner)
        for i, esc in enumerate(escaleras):
            bl_coord = esc['bl']
            rect_esc = patches.Rectangle(bl_coord, lado_escalera, lado_escalera, linewidth=1, edgecolor='red', facecolor='salmon', label='Unidad Escalera' if i == 0 else "")
            ax.add_patch(rect_esc)
        for i, base in enumerate(bases):
            bl_coord = base['bl']
            rect_base = patches.Rectangle(bl_coord, ancho_base, largo_base, linewidth=0.5, edgecolor='green', facecolor='lightgreen', label='Unidad Base' if i == 0 else "")
            ax.add_patch(rect_base)
        margin_x = outer_width * 0.05; margin_y = outer_height * 0.05
        ax.set_xlim(outer_coords['min_x'] - margin_x, outer_coords['max_x'] + margin_x)
        ax.set_ylim(outer_coords['min_y'] - margin_y, outer_coords['max_y'] + margin_y)
        ax.set_aspect('equal', adjustable='box')
        ax.set_title('Visualización del Terreno y Unidades')
        ax.set_xlabel('Coordenada X / Longitud (Simplificado)')
        ax.set_ylabel('Coordenada Y / Latitud (Simplificado)')
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), fontsize='small')
        ax.grid(True, linestyle=':', alpha=0.6)
    except Exception as e:
        print("--- ERROR DETALLADO en visualizar_en_canvas ---")
        traceback.print_exc()
        print("---------------------------------------------")
        ax.clear()
        ax.text(0.5, 0.5, f"Error al dibujar:\n{e}", ha='center', va='center', color='red', wrap=True)
        ax.set_title("Error de Visualización")


class KMLApp:
    def __init__(self, master):
        self.master = master
        master.title("Calculadora de Unidades en Terreno KML (v3 - Fix Iterator)")
        master.geometry("850x650")
        self.kml_filepath = None
        self.outer_coords = None
        control_frame = ttk.Frame(master, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        self.plot_frame = ttk.Frame(master)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        ttk.Label(control_frame, text="Archivo KML:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.kml_label = ttk.Label(control_frame, text="Ninguno seleccionado", width=40, relief=tk.SUNKEN, anchor=tk.W)
        self.kml_label.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(control_frame, text="Seleccionar KML", command=self.select_kml).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(control_frame, text="Distancia Corona:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.corona_entry = ttk.Entry(control_frame, width=12); self.corona_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W); self.corona_entry.insert(0, "10.0")
        ttk.Label(control_frame, text="Largo U. Base (Y):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.largo_entry = ttk.Entry(control_frame, width=12); self.largo_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W); self.largo_entry.insert(0, "8.0")
        ttk.Label(control_frame, text="Ancho U. Base (X):").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.ancho_entry = ttk.Entry(control_frame, width=12); self.ancho_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W); self.ancho_entry.insert(0, "5.0")
        ttk.Button(control_frame, text="Calcular y Visualizar", command=self.run_calculation).grid(row=1, column=3, rowspan=3, padx=15, pady=5, sticky=tk.NSEW)
        self.status_label = ttk.Label(control_frame, text="Listo.", relief=tk.SUNKEN, anchor=tk.W); self.status_label.grid(row=4, column=0, columnspan=4, padx=5, pady=10, sticky=tk.EW)
        control_frame.columnconfigure(1, weight=0); control_frame.columnconfigure(2, weight=1); control_frame.columnconfigure(3, weight=0)
        self.fig = Figure(figsize=(7, 5.5), dpi=100); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame); self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame); toolbar.update(); toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.ax.set_title("Esperando datos para visualizar..."); self.ax.grid(True); self.canvas.draw()

    def select_kml(self):
        filepath = filedialog.askopenfilename(title="Seleccionar archivo KML", filetypes=(("KML files", "*.kml"), ("All files", "*.*")))
        if filepath:
            self.kml_filepath = filepath; filename = os.path.basename(filepath)
            self.kml_label.config(text=filename); self.status_label.config(text=f"Archivo: {filename}. Leyendo BBox...")
            self.master.update_idletasks()
            self.outer_coords = leer_primer_poligono_kml(self.kml_filepath)
            if "error" in self.outer_coords:
                 messagebox.showerror("Error KML", f"No se pudo leer polígono del KML:\n{self.outer_coords['error']}")
                 self.outer_coords = None; self.kml_label.config(text="Error al leer KML"); self.status_label.config(text="Error al leer KML.")
            else: self.status_label.config(text=f"BBox KML leído. Listo.")
        else:
            self.kml_filepath = None; self.outer_coords = None; self.kml_label.config(text="Ninguno seleccionado"); self.status_label.config(text="Selección cancelada.")

    def run_calculation(self):
        self.status_label.config(text="Procesando..."); self.master.update_idletasks()
        if not self.kml_filepath: messagebox.showerror("Error", "Selecciona un archivo KML."); self.status_label.config(text="Error: Falta KML."); return
        if not self.outer_coords or "error" in self.outer_coords:
             if not self.outer_coords: self.outer_coords = leer_primer_poligono_kml(self.kml_filepath) # Re-intentar si no se leyó antes
             if not self.outer_coords or "error" in self.outer_coords:
                  error_msg = self.outer_coords.get('error', 'No se pudieron leer coords.') if self.outer_coords else 'No se pudieron leer coords.'
                  messagebox.showerror("Error KML", f"Error al obtener coords:\n{error_msg}"); self.status_label.config(text="Error: KML inválido."); return
        try:
            dist_corona = float(self.corona_entry.get()); largo_base = float(self.largo_entry.get()); ancho_base = float(self.ancho_entry.get())
            if dist_corona < 0 or largo_base <= 0 or ancho_base <= 0: raise ValueError("Valores deben ser positivos (largo/ancho > 0).")
            params = {'distancia_corona': dist_corona, 'largo_base': largo_base, 'ancho_base': ancho_base}
        except ValueError as e: messagebox.showerror("Error de Entrada", f"Valor numérico inválido: {e}"); self.status_label.config(text="Error: Parámetros."); return

        resultado_calculo = calcular_unidades_terreno(self.outer_coords['min_x'], self.outer_coords['min_y'], self.outer_coords['max_x'], self.outer_coords['max_y'], params['distancia_corona'], params['largo_base'], params['ancho_base'])

        if "error" in resultado_calculo:
            messagebox.showerror("Error de Cálculo", resultado_calculo['error']); self.status_label.config(text=f"Error cálculo: {resultado_calculo['error']}")
            self.ax.clear(); self.ax.set_title("Error en el cálculo"); self.ax.text(0.5, 0.5, f"Error:\n{resultado_calculo['error']}", ha='center', va='center', color='red', wrap=True); self.ax.grid(True); self.canvas.draw()
        else:
            try:
                visualizar_en_canvas(self.ax, self.outer_coords, resultado_calculo['inner_coords'], resultado_calculo['escaleras'], resultado_calculo['bases'], params)
                self.canvas.draw(); self.status_label.config(text="¡Éxito!")
            except Exception as e: messagebox.showerror("Error de Visualización", f"Error al dibujar:\n{e}"); self.status_label.config(text="Error al visualizar.")

if __name__ == "__main__":
    try: import fastkml; import shapely; import matplotlib
    except ImportError as e: messagebox.showerror("Error Dependencia", f"Falta librería esencial: {e}\nInstala: pip install matplotlib fastkml shapely"); exit()
    root = tk.Tk(); app = KMLApp(root); root.mainloop()