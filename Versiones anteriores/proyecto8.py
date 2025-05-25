import tkinter as tk
from tkinter import filedialog, messagebox, ttk # ttk para widgets mejorados
import math
import json
import os

# Importaciones para KML y Geometría
from fastkml import kml
from shapely.geometry import Polygon, box

# Importaciones para Matplotlib en Tkinter
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.patches as patches

# --- Funciones de Cálculo y Lectura KML (Ligeramente adaptadas) ---
# (Las funciones 'leer_primer_poligono_kml' y 'calcular_unidades_terreno'
#  van aquí. Son casi idénticas a las versiones anteriores, solo
#  asegurándonos de que devuelvan diccionarios con 'error' en caso de fallo)

def leer_primer_poligono_kml(filepath):
    """
    Lee un archivo KML, busca el primer polígono encontrado en un Placemark
    (revisando hasta un nivel de profundidad en Document/Folder)
    y devuelve su bounding box {'min_x', 'min_y', 'max_x', 'max_y'}.
    """
    if not os.path.exists(filepath):
        return {"error": f"Archivo no encontrado: {filepath}"}

    try:
        # Leer el contenido del archivo KML
        with open(filepath, 'rt', encoding='utf-8') as f:
            kml_string = f.read()

        # Crear objeto KML y parsear
        k = kml.KML()
        k.from_string(kml_string.encode('utf-8'))

        feature_polygon = None

        # Iterar sobre las características principales del KML
        # (Pueden ser Placemarks, Documentos, Carpetas)
        for feature in k.features():
            # 1. Verificar si la característica principal es un Polígono
            if hasattr(feature, 'geometry') and isinstance(feature.geometry, Polygon):
                feature_polygon = feature.geometry
                # print("DEBUG: Polígono encontrado en nivel superior.") # Opcional
                break # Encontramos uno, salimos del bucle

            # 2. Si no, verificar si es un contenedor (Documento/Carpeta) y buscar dentro
            elif hasattr(feature, 'features'):
                # print(f"DEBUG: Buscando dentro de: {feature.name if hasattr(feature, 'name') else type(feature)}") # Opcional
                for subfeature in feature.features():
                     # Verificar si la sub-característica es un Polígono
                    if hasattr(subfeature, 'geometry') and isinstance(subfeature.geometry, Polygon):
                        feature_polygon = subfeature.geometry
                        # print("DEBUG: Polígono encontrado en nivel secundario.") # Opcional
                        break # Encontramos uno, salimos del bucle interno
                if feature_polygon:
                    break # Salimos también del bucle externo

        # Procesar si encontramos un polígono
        if feature_polygon:
            # Extraer coordenadas y calcular bounding box con Shapely
            shapely_poly = Polygon(feature_polygon.exterior.coords)
            minx, miny, maxx, maxy = shapely_poly.bounds
            # print(f"DEBUG: Bounding Box calculado: ({minx}, {miny}) a ({maxx}, {maxy})") # Opcional
            return {'min_x': minx, 'min_y': miny, 'max_x': maxx, 'max_y': maxy}
        else:
            # print("DEBUG: No se encontró ningún polígono en la estructura KML.") # Opcional
            return {"error": "No se encontró ningún polígono en la estructura KML procesada."}

    except Exception as e:
        # Capturar cualquier otra excepción durante lectura/parseo
        import traceback # Importar para obtener más detalles
        print("--- ERROR DETALLADO ---")
        traceback.print_exc() # Imprimir el traceback completo en consola
        print("-----------------------")
        return {"error": f"Error al leer o parsear KML: {e}"}

def calcular_unidades_terreno(
    minX_outer, minY_outer, maxX_outer, maxY_outer,
    distancia_corona, largo_base, ancho_base):
    """
    Calcula la posición de unidades 'escalera' y 'base'.
    Devuelve dict con 'escaleras', 'bases', 'inner_coords' o 'error'.
    """
    # ... (Mismo código de cálculo que en la respuesta anterior) ...
    # Asegúrate de que todas las rutas de retorno de error devuelvan
    # un diccionario como {'error': 'mensaje...'}
    # Y la ruta de éxito devuelva el diccionario con las listas y coords internas.

    # --- Ejemplo resumido de la estructura interna ---
    escaleras = []
    bases = []
    resultado = {}
    # --- Validaciones Iniciales ---
    if largo_base <= 0 or ancho_base <= 0 or distancia_corona < 0: return {"error": "Dimensiones/Corona deben ser > 0."}
    if maxX_outer <= minX_outer or maxY_outer <= minY_outer: return {"error": "Coords. terreno exterior inválidas."}
    # --- Cálculos (Pasos 1-8) ---
    lado_escalera = largo_base
    minX_inner = minX_outer + distancia_corona; minY_inner = minY_outer + distancia_corona
    maxX_inner = maxX_outer - distancia_corona; maxY_inner = maxY_outer - distancia_corona
    if minX_inner >= maxX_inner or minY_inner >= maxY_inner: return {"error": "Corona demasiado grande."}
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
    if W_hueco_total < -1e-9 or H_hueco_total < -1e-9: return {"error": f"Área interna no cabe ni las escaleras (lado {lado_escalera})."}
    W_margen = W_hueco_total / 2; H_margen = H_hueco_total / 2
    # --- Paso 9: Coords Escaleras ---
    coords_escalera = { # ... (definir como antes) ...
        "BL": ((minX_inner + W_margen, minY_inner + H_margen), (minX_inner + W_margen + lado_escalera, minY_inner + H_margen + lado_escalera)),
        "BR": ((maxX_inner - W_margen - lado_escalera, minY_inner + H_margen), (maxX_inner - W_margen, minY_inner + H_margen + lado_escalera)),
        "TL": ((minX_inner + W_margen, maxY_inner - H_margen - lado_escalera), (minX_inner + W_margen + lado_escalera, maxY_inner - H_margen)),
        "TR": ((maxX_inner - W_margen - lado_escalera, maxY_inner - H_margen - lado_escalera), (maxX_inner - W_margen, maxY_inner - H_margen))
    }
    for key, (bl, tr) in coords_escalera.items(): escaleras.append({"type": f"escalera_{key}", "bl": bl, "tr": tr})
    # --- Paso 10: Coords Bases ---
    if num_base_X > 0 and num_base_Y > 0:
        base_start_x = minX_inner + W_margen + lado_escalera; base_start_y = minY_inner + H_margen + lado_escalera
        for j in range(num_base_Y):
            for i in range(num_base_X):
                # ... (calcular coords base y añadir a la lista 'bases') ...
                 unit_bl_x = base_start_x + i * ancho_base; unit_bl_y = base_start_y + j * largo_base
                 unit_tr_x = unit_bl_x + ancho_base; unit_tr_y = unit_bl_y + largo_base
                 bases.append({"type": "base", "row": j, "col": i, "bl": (unit_bl_x, unit_bl_y), "tr": (unit_tr_x, unit_tr_y)})
    # --- Retorno ---
    resultado['escaleras'] = escaleras; resultado['bases'] = bases
    return resultado

# --- Función de Visualización Adaptada para Tkinter ---
def visualizar_en_canvas(ax, outer_coords, inner_coords, escaleras, bases, params):
    """Dibuja en un objeto Axes de Matplotlib proporcionado."""
    ax.clear() # Limpiar gráfico anterior

    # Dimensiones para dibujar rectángulos
    outer_width = outer_coords['max_x'] - outer_coords['min_x']
    outer_height = outer_coords['max_y'] - outer_coords['min_y']
    inner_width = inner_coords['max_x'] - inner_coords['min_x']
    inner_height = inner_coords['max_y'] - inner_coords['min_y']
    lado_escalera = params['largo_base']
    ancho_base = params['ancho_base']
    largo_base = params['largo_base']

    # 1. Dibujar Terreno Exterior (Bounding Box del KML)
    rect_outer = patches.Rectangle(
        (outer_coords['min_x'], outer_coords['min_y']), outer_width, outer_height,
        linewidth=1.5, edgecolor='black', facecolor='none', label='Bounding Box KML'
    )
    ax.add_patch(rect_outer)

    # 2. Dibujar Área Interna
    rect_inner = patches.Rectangle(
        (inner_coords['min_x'], inner_coords['min_y']), inner_width, inner_height,
        linewidth=1, edgecolor='blue', linestyle='--', facecolor='none', label='Área Interna'
    )
    ax.add_patch(rect_inner)

    # 3. Dibujar Unidades Escalera
    for i, esc in enumerate(escaleras):
        bl_coord = esc['bl']
        rect_esc = patches.Rectangle(bl_coord, lado_escalera, lado_escalera, linewidth=1, edgecolor='red', facecolor='salmon', label='Unidad Escalera' if i == 0 else "")
        ax.add_patch(rect_esc)

    # 4. Dibujar Unidades Base
    for i, base in enumerate(bases):
        bl_coord = base['bl']
        rect_base = patches.Rectangle(bl_coord, ancho_base, largo_base, linewidth=0.5, edgecolor='green', facecolor='lightgreen', label='Unidad Base' if i == 0 else "")
        ax.add_patch(rect_base)

    # Ajustar límites y apariencia
    margin_x = outer_width * 0.05
    margin_y = outer_height * 0.05
    ax.set_xlim(outer_coords['min_x'] - margin_x, outer_coords['max_x'] + margin_x)
    ax.set_ylim(outer_coords['min_y'] - margin_y, outer_coords['max_y'] + margin_y)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title('Visualización del Terreno y Unidades')
    ax.set_xlabel('Coordenada X / Longitud (Simplificado)')
    ax.set_ylabel('Coordenada Y / Latitud (Simplificado)')
    ax.legend(fontsize='small')
    ax.grid(True, linestyle=':', alpha=0.6)


# --- Clase Principal de la Aplicación GUI ---
class KMLApp:
    def __init__(self, master):
        self.master = master
        master.title("Calculadora de Unidades en Terreno KML")
        master.geometry("800x600") # Tamaño inicial ventana

        self.kml_filepath = None
        self.outer_coords = None

        # --- Layout ---
        # Frame para Controles (arriba)
        control_frame = ttk.Frame(master, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Frame para el Gráfico (abajo)
        self.plot_frame = ttk.Frame(master)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # --- Widgets de Control ---
        # Selección KML
        ttk.Label(control_frame, text="Archivo KML:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.kml_label = ttk.Label(control_frame, text="Ninguno seleccionado", width=40, relief=tk.SUNKEN)
        self.kml_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(control_frame, text="Seleccionar KML", command=self.select_kml).grid(row=0, column=2, padx=5, pady=5)

        # Entradas de Parámetros
        ttk.Label(control_frame, text="Distancia Corona:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.corona_entry = ttk.Entry(control_frame, width=10)
        self.corona_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.corona_entry.insert(0, "10") # Valor por defecto

        ttk.Label(control_frame, text="Largo U. Base (Y):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.largo_entry = ttk.Entry(control_frame, width=10)
        self.largo_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.largo_entry.insert(0, "8") # Valor por defecto

        ttk.Label(control_frame, text="Ancho U. Base (X):").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.ancho_entry = ttk.Entry(control_frame, width=10)
        self.ancho_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        self.ancho_entry.insert(0, "5") # Valor por defecto

        # Botón de Acción
        ttk.Button(control_frame, text="Calcular y Visualizar", command=self.run_calculation).grid(row=1, column=2, rowspan=3, padx=5, pady=5, sticky=tk.NS)

        # Etiqueta de Estado
        self.status_label = ttk.Label(control_frame, text="Listo.", relief=tk.SUNKEN)
        self.status_label.grid(row=4, column=0, columnspan=3, padx=5, pady=10, sticky=tk.EW)

        # Configurar expansión de columnas en control_frame
        control_frame.columnconfigure(1, weight=1)

        # --- Configuración del Canvas de Matplotlib ---
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111) # Ejes para dibujar

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Añadir barra de herramientas de Matplotlib
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Dibujar un gráfico inicial vacío o con ejes
        self.ax.set_title("Esperando datos para visualizar...")
        self.ax.grid(True)
        self.canvas.draw()

    def select_kml(self):
        """Abre diálogo para seleccionar archivo KML."""
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo KML",
            filetypes=(("KML files", "*.kml"), ("All files", "*.*"))
        )
        if filepath:
            self.kml_filepath = filepath
            # Mostrar solo el nombre del archivo, no la ruta completa
            filename = os.path.basename(filepath)
            self.kml_label.config(text=filename)
            self.status_label.config(text=f"Archivo KML seleccionado: {filename}")
            # Intentar leer las coordenadas al seleccionar
            self.outer_coords = leer_primer_poligono_kml(self.kml_filepath)
            if "error" in self.outer_coords:
                 messagebox.showerror("Error KML", f"No se pudo leer el polígono del KML:\n{self.outer_coords['error']}")
                 self.outer_coords = None # Resetear si hay error
            else:
                 print(f"Coordenadas (Bounding Box) leídas: {self.outer_coords}")
        else:
            self.kml_filepath = None
            self.outer_coords = None
            self.kml_label.config(text="Ninguno seleccionado")

    def run_calculation(self):
        """Ejecuta la lectura, cálculo y visualización."""
        self.status_label.config(text="Procesando...")
        self.master.update_idletasks() # Forzar actualización de la etiqueta

        # 1. Validar selección de KML y coordenadas leídas
        if not self.kml_filepath:
            messagebox.showerror("Error", "Por favor, selecciona un archivo KML primero.")
            self.status_label.config(text="Error: Falta archivo KML.")
            return
        if not self.outer_coords or "error" in self.outer_coords:
             # Intentar leer de nuevo por si acaso
             self.outer_coords = leer_primer_poligono_kml(self.kml_filepath)
             if not self.outer_coords or "error" in self.outer_coords:
                  error_msg = self.outer_coords.get('error', 'No se pudieron leer las coordenadas del KML.') if self.outer_coords else 'No se pudieron leer las coordenadas del KML.'
                  messagebox.showerror("Error KML", f"Error al obtener coordenadas del KML:\n{error_msg}")
                  self.status_label.config(text="Error: KML inválido o sin polígono.")
                  return

        # 2. Validar y obtener parámetros numéricos
        try:
            dist_corona = float(self.corona_entry.get())
            largo_base = float(self.largo_entry.get())
            ancho_base = float(self.ancho_entry.get())
            if dist_corona < 0 or largo_base <= 0 or ancho_base <= 0:
                raise ValueError("Valores deben ser positivos (largo/ancho > 0).")
            params = {
                'distancia_corona': dist_corona,
                'largo_base': largo_base,
                'ancho_base': ancho_base
            }
        except ValueError as e:
            messagebox.showerror("Error de Entrada", f"Valor numérico inválido: {e}")
            self.status_label.config(text="Error: Parámetros inválidos.")
            return

        # 3. Ejecutar el cálculo principal
        resultado_calculo = calcular_unidades_terreno(
            self.outer_coords['min_x'], self.outer_coords['min_y'],
            self.outer_coords['max_x'], self.outer_coords['max_y'],
            params['distancia_corona'], params['largo_base'], params['ancho_base']
        )

        # 4. Mostrar resultado o error
        if "error" in resultado_calculo:
            messagebox.showerror("Error de Cálculo", resultado_calculo['error'])
            self.status_label.config(text=f"Error en cálculo: {resultado_calculo['error']}")
            # Limpiar el gráfico si hubo error
            self.ax.clear()
            self.ax.set_title("Error en el cálculo - Revise parámetros o KML")
            self.ax.grid(True)
            self.canvas.draw()
        else:
            # 5. Visualizar el resultado exitoso
            try:
                visualizar_en_canvas(
                    self.ax, # Pasar los ejes del canvas
                    self.outer_coords,
                    resultado_calculo['inner_coords'],
                    resultado_calculo['escaleras'],
                    resultado_calculo['bases'],
                    params
                )
                self.canvas.draw() # Actualizar el canvas de Tkinter
                self.status_label.config(text="¡Cálculo y visualización completados!")
                print("\n--- Resultados Detallados ---")
                print(json.dumps({k: v for k, v in resultado_calculo.items() if k != 'inner_coords'}, indent=2)) # Imprimir escaleras/bases en consola
            except Exception as e:
                 messagebox.showerror("Error de Visualización", f"Ocurrió un error al dibujar:\n{e}")
                 self.status_label.config(text="Error al visualizar.")


# --- Iniciar la aplicación ---
if __name__ == "__main__":
    root = tk.Tk()
    app = KMLApp(root)
    root.mainloop()