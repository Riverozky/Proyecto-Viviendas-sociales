import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.path import Path
import matplotlib.patches as patches # Necesario para dibujar rectángulos
from pykml import parser
from lxml import etree
import math # Para floor
import sys # Para obtener límites numéricos

# --- Funciones de Procesamiento ---

def leer_kml_y_obtener_bbox(archivo):
    """
    Lee un archivo KML, busca el primer polígono y devuelve su bounding box.

    Args:
        archivo (str): Ruta al archivo KML.

    Returns:
        tuple: (min_x, min_y, max_x, max_y) del bounding box, o None si hay error.
    """
    try:
        with open(archivo, 'rb') as f: # Abrir en modo binario para pykml
            doc = parser.parse(f).getroot()
            # Buscar el primer polígono en cualquier nivel del KML
            # El namespace puede variar, buscamos por el nombre local 'Polygon'
            polygon = doc.find(".//*[local-name()='Polygon']")
            if polygon is not None:
                # Buscar las coordenadas dentro del polígono encontrado
                coordinates_tag = polygon.find(".//*[local-name()='coordinates']")
                if coordinates_tag is not None:
                    # Extraer y limpiar las coordenadas (longitud, latitud, altitud opcional)
                    coords_text = coordinates_tag.text.strip()
                    # Dividir por espacios o saltos de línea, manejar comas como separador decimal si es necesario
                    points_str = coords_text.split()
                    coordenadas = []
                    for point_str in points_str:
                        try:
                            # Tomar solo los dos primeros valores (lon, lat)
                            lon, lat = map(float, point_str.split(',')[:2])
                            coordenadas.append((lon, lat))
                        except ValueError:
                            # Ignorar puntos mal formateados
                            print(f"Advertencia: Ignorando punto mal formateado '{point_str}'")
                            continue

                    if not coordenadas:
                         messagebox.showerror("Error KML", "No se pudieron extraer coordenadas válidas del polígono.")
                         return None

                    # Calcular Bounding Box
                    min_x = sys.float_info.max
                    min_y = sys.float_info.max
                    max_x = sys.float_info.min
                    max_y = sys.float_info.min
                    for x, y in coordenadas:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)

                    if min_x == sys.float_info.max: # Si no se actualizó, no había puntos válidos
                        messagebox.showerror("Error KML", "No se encontraron coordenadas válidas para calcular el bounding box.")
                        return None

                    return (min_x, min_y, max_x, max_y)
                else:
                     messagebox.showerror("Error KML", "No se encontró la etiqueta 'coordinates' dentro del polígono.")
                     return None
            else:
                messagebox.showerror("Error KML", "No se encontró ningún polígono en el archivo KML.")
                return None
    except FileNotFoundError:
         messagebox.showerror("Error", f"Archivo no encontrado: {archivo}")
         return None
    except etree.XMLSyntaxError as e:
        messagebox.showerror("Error KML", f"Error al parsear el archivo KML (XML inválido): {e}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado al leer el archivo KML: {e}")
        return None


def calcular_y_visualizar_unidades(bbox, dist_corona, largo_base_y, ancho_base_x):
    """
    Calcula la disposición de unidades base y escalera y genera la visualización.

    Args:
        bbox (tuple): (min_x, min_y, max_x, max_y) del bounding box exterior.
        dist_corona (float): Distancia del offset hacia adentro.
        largo_base_y (float): Dimensión Y de la unidad base y lado de la unidad escalera.
        ancho_base_x (float): Dimensión X de la unidad base.

    Returns:
        matplotlib.figure.Figure: La figura de Matplotlib con el gráfico, o None si hay error.
    """
    if not all(isinstance(n, (int, float)) and n >= 0 for n in [dist_corona, largo_base_y, ancho_base_x]):
        messagebox.showerror("Error de Parámetros", "Las dimensiones y la corona deben ser números no negativos.")
        return None
    if largo_base_y <= 0 or ancho_base_x <= 0:
         messagebox.showerror("Error de Parámetros", "Las dimensiones de la unidad base deben ser mayores que cero.")
         return None

    min_x_bb, min_y_bb, max_x_bb, max_y_bb = bbox
    bb_width = max_x_bb - min_x_bb
    bb_height = max_y_bb - min_y_bb

    # 1. Calcular Área Interna
    inner_min_x = min_x_bb + dist_corona
    inner_min_y = min_y_bb + dist_corona
    inner_max_x = max_x_bb - dist_corona
    inner_max_y = max_y_bb - dist_corona
    inner_width = inner_max_x - inner_min_x
    inner_height = inner_max_y - inner_min_y

    if inner_width <= 0 or inner_height <= 0:
        messagebox.showerror("Error de Cálculo", "La distancia de la 'corona' es demasiado grande para el bounding box.")
        return None

    # 2. Definir Unidad Escalera
    lado_escalera = largo_base_y # Lado de la unidad escalera es el LARGO (Y) de la unidad base

    # 3. Calcular espacio para Unidades Base (entre las 4 esquinas de escaleras)
    espacio_central_x = inner_width - 2 * lado_escalera
    espacio_central_y = inner_height - 2 * lado_escalera

    if espacio_central_x < 0 or espacio_central_y < 0:
        messagebox.showwarning("Advertencia de Cálculo", "El área interna no es suficientemente grande para colocar ni siquiera las 4 unidades escalera. Se dibujarán solo las áreas.")
        num_base_x = 0
        num_base_y = 0
        # Aún así calculamos el espacio total para centrar lo que se pueda dibujar (escaleras)
        total_structure_width = 2 * lado_escalera
        total_structure_height = 2 * lado_escalera
    else:
        # Calcular cuántas unidades base COMPLETAS caben
        num_base_x = math.floor(espacio_central_x / ancho_base_x) if ancho_base_x > 0 else 0
        num_base_y = math.floor(espacio_central_y / largo_base_y) if largo_base_y > 0 else 0

         # 4. Calcular tamaño total de la estructura (bases + escaleras)
        ancho_total_bases = num_base_x * ancho_base_x
        largo_total_bases = num_base_y * largo_base_y
        total_structure_width = ancho_total_bases + 2 * lado_escalera
        total_structure_height = largo_total_bases + 2 * lado_escalera


    # 5. Calcular offset para centrar la estructura dentro del Área Interna
    offset_x = (inner_width - total_structure_width) / 2
    offset_y = (inner_height - total_structure_height) / 2

    # 6. Calcular posiciones finales

    # Coordenadas de inicio (bottom-left) de las 4 Unidades Escalera
    escalera_coords = []
    # BL (Bottom-Left)
    esc_bl = (inner_min_x + offset_x, inner_min_y + offset_y)
    escalera_coords.append(esc_bl)
    # BR (Bottom-Right)
    esc_br = (inner_min_x + offset_x + lado_escalera + num_base_x * ancho_base_x, inner_min_y + offset_y)
    escalera_coords.append(esc_br)
    # TL (Top-Left)
    esc_tl = (inner_min_x + offset_x, inner_min_y + offset_y + lado_escalera + num_base_y * largo_base_y)
    escalera_coords.append(esc_tl)
    # TR (Top-Right)
    esc_tr = (inner_min_x + offset_x + lado_escalera + num_base_x * ancho_base_x, inner_min_y + offset_y + lado_escalera + num_base_y * largo_base_y)
    escalera_coords.append(esc_tr)

    # Coordenadas de inicio (bottom-left) de las Unidades Base
    base_coords = []
    start_base_x = inner_min_x + offset_x + lado_escalera
    start_base_y = inner_min_y + offset_y + lado_escalera
    for j in range(num_base_y): # Filas (Y)
        for i in range(num_base_x): # Columnas (X)
            coord = (start_base_x + i * ancho_base_x, start_base_y + j * largo_base_y)
            base_coords.append(coord)

    # --- Visualización ---
    fig, ax = plt.subplots()
    ax.set_aspect('equal') # Mantener proporción x/y

    # Dibujar Bounding Box (Negro)
    rect_bb = patches.Rectangle(
        (min_x_bb, min_y_bb), bb_width, bb_height,
        linewidth=1, edgecolor='black', facecolor='none', label='Bounding Box KML'
    )
    ax.add_patch(rect_bb)

    # Dibujar Área Interna (Azul Punteado)
    rect_inner = patches.Rectangle(
        (inner_min_x, inner_min_y), inner_width, inner_height,
        linewidth=1, edgecolor='blue', facecolor='none', linestyle='--', label='Área Interna (con corona)'
    )
    ax.add_patch(rect_inner)

    # Dibujar Unidades Escalera (Rojo/Salmón)
    for i, (x, y) in enumerate(escalera_coords):
        rect_esc = patches.Rectangle(
            (x, y), lado_escalera, lado_escalera,
            linewidth=1, edgecolor='darkred', facecolor='salmon', alpha=0.7, label='Unidad Escalera' if i == 0 else "" # Solo una etiqueta
        )
        ax.add_patch(rect_esc)

    # Dibujar Unidades Base (Verde)
    for i, (x, y) in enumerate(base_coords):
        rect_base = patches.Rectangle(
            (x, y), ancho_base_x, largo_base_y,
            linewidth=1, edgecolor='darkgreen', facecolor='lightgreen', alpha=0.7, label='Unidad Base' if i == 0 else "" # Solo una etiqueta
        )
        ax.add_patch(rect_base)

    # Ajustar límites del gráfico con un pequeño margen
    margin_x = bb_width * 0.05
    margin_y = bb_height * 0.05
    ax.set_xlim(min_x_bb - margin_x, max_x_bb + margin_x)
    ax.set_ylim(min_y_bb - margin_y, max_y_bb + margin_y)

    ax.set_xlabel("Longitud / Coordenada X")
    ax.set_ylabel("Latitud / Coordenada Y")
    ax.set_title("Visualización de Unidades Base y Escalera")
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    return fig

# --- Interfaz Gráfica ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora de Unidades en Terreno (v2)")
        self.root.geometry("800x700") # Tamaño inicial ventana

        self.archivo_kml = None
        self.bounding_box = None # Almacenará (min_x, min_y, max_x, max_y)

        self.dist_corona = tk.DoubleVar(value=1.0) # Usar DoubleVar para floats
        self.largo_unidad_base = tk.DoubleVar(value=10.0)
        self.ancho_unidad_base = tk.DoubleVar(value=5.0)

        self.fig = None
        self.canvas = None
        self.toolbar = None

        self.crear_interfaz()
        self.actualizar_estado("Listo. Cargue un archivo KML.")

    def crear_interfaz(self):
        # Frame principal para organizar mejor
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Frame de Controles (Izquierda o Arriba) ---
        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        # Carga de Archivo
        load_frame = tk.Frame(control_frame)
        load_frame.pack(fill=tk.X)
        self.boton_cargar = tk.Button(load_frame, text="1. Cargar Archivo KML", command=self.cargar_archivo)
        self.boton_cargar.pack(side=tk.LEFT, padx=5)
        self.label_archivo = tk.Label(load_frame, text="Ningún archivo cargado.", fg="grey")
        self.label_archivo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Parámetros
        params_frame = tk.LabelFrame(control_frame, text="2. Parámetros Numéricos")
        params_frame.pack(fill=tk.X, pady=10)

        tk.Label(params_frame, text="Distancia 'Corona' (offset):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.entrada_corona = tk.Entry(params_frame, textvariable=self.dist_corona, width=10)
        self.entrada_corona.grid(row=0, column=1, padx=5, pady=2)

        tk.Label(params_frame, text="Largo Unidad Base (Y):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.entrada_largo_base = tk.Entry(params_frame, textvariable=self.largo_unidad_base, width=10)
        self.entrada_largo_base.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(params_frame, text="(Define lado Unidad Escalera)").grid(row=1, column=2, padx=5, pady=2, sticky="w", fg="blue")


        tk.Label(params_frame, text="Ancho Unidad Base (X):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.entrada_ancho_base = tk.Entry(params_frame, textvariable=self.ancho_unidad_base, width=10)
        self.entrada_ancho_base.grid(row=2, column=1, padx=5, pady=2)

        # Botón de Acción
        self.boton_visualizar = tk.Button(control_frame, text="3. Calcular y Visualizar", command=self.visualizar, state=tk.DISABLED)
        self.boton_visualizar.pack(pady=10)

        # --- Frame de Visualización (Centro/Abajo) ---
        self.plot_frame = tk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        # --- Barra de Estado (Abajo) ---
        self.status_bar = tk.Label(self.root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def actualizar_estado(self, mensaje, color="black"):
        """Actualiza el texto y color de la barra de estado."""
        self.status_bar.config(text=mensaje, fg=color)
        self.root.update_idletasks() # Forzar actualización inmediata

    def cargar_archivo(self):
        """Abre el diálogo para seleccionar KML y procesa el archivo."""
        self.actualizar_estado("Seleccionando archivo...", "blue")
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo KML",
            filetypes=[("KML files", "*.kml"), ("All files", "*.*")]
        )
        if not filepath:
            self.actualizar_estado("Carga cancelada.", "orange")
            return

        self.archivo_kml = filepath
        self.label_archivo.config(text=f"...{filepath[-40:]}") # Mostrar parte del nombre
        self.actualizar_estado(f"Procesando {filepath}...", "blue")

        self.bounding_box = leer_kml_y_obtener_bbox(self.archivo_kml)

        if self.bounding_box:
            self.actualizar_estado("Archivo KML cargado y BBox calculado. Ingrese parámetros.", "green")
            self.boton_visualizar.config(state=tk.NORMAL) # Habilitar botón
             # Limpiar gráfico anterior si existe
            self._limpiar_grafico()
        else:
            # El mensaje de error ya fue mostrado por leer_kml_y_obtener_bbox
            self.actualizar_estado("Error al procesar KML. Verifique el archivo.", "red")
            self.archivo_kml = None
            self.bounding_box = None
            self.label_archivo.config(text="Error en archivo.")
            self.boton_visualizar.config(state=tk.DISABLED) # Deshabilitar botón


    def _limpiar_grafico(self):
         """Elimina el canvas y la toolbar existentes."""
         if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
         if self.toolbar:
            self.toolbar.destroy()
            self.toolbar = None
         if self.fig:
             plt.close(self.fig) # Cerrar figura de matplotlib para liberar memoria
             self.fig = None


    def visualizar(self):
        """Obtiene parámetros, llama al cálculo/visualización y muestra el gráfico."""
        if not self.bounding_box:
            messagebox.showerror("Error", "Primero debe cargar un archivo KML válido.")
            return

        self.actualizar_estado("Calculando y visualizando...", "blue")

        try:
            # Obtener valores de las variables Tkinter (ya son floats)
            dist_corona_val = self.dist_corona.get()
            largo_base_val = self.largo_unidad_base.get()
            ancho_base_val = self.ancho_unidad_base.get()

            # Validar que no sean negativos (aunque DoubleVar ayuda, una verificación extra)
            if dist_corona_val < 0 or largo_base_val <= 0 or ancho_base_val <= 0:
                 raise ValueError("Dimensiones y corona deben ser positivas (dimensiones > 0).")

        except (tk.TclError, ValueError) as e:
            messagebox.showerror("Error de Entrada", f"Valores numéricos inválidos: {e}")
            self.actualizar_estado("Error en parámetros.", "red")
            return

        # Limpiar gráfico anterior antes de crear uno nuevo
        self._limpiar_grafico()

        # Llamar a la función principal de cálculo y dibujo
        self.fig = calcular_y_visualizar_unidades(
            self.bounding_box,
            dist_corona_val,
            largo_base_val,
            ancho_base_val
        )

        if self.fig:
            try:
                 # Crear el canvas de Tkinter para Matplotlib
                self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
                canvas_widget = self.canvas.get_tk_widget()
                canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                # Añadir la barra de herramientas de navegación de Matplotlib
                self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
                self.toolbar.update()
                canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True) # Re-pack para que la toolbar quede arriba

                self.canvas.draw()
                self.actualizar_estado("Visualización generada.", "green")
            except Exception as e:
                 messagebox.showerror("Error de Visualización", f"Ocurrió un error al mostrar el gráfico: {e}")
                 self.actualizar_estado("Error al mostrar gráfico.", "red")
                 self._limpiar_grafico() # Limpiar si falla la incrustación
        else:
            # El error específico ya fue mostrado por calcular_y_visualizar_unidades
            self.actualizar_estado("Error durante el cálculo. Verifique parámetros/corona.", "red")
            self._limpiar_grafico() # Asegurar limpieza


# --- Ejecutar la aplicación ---
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()