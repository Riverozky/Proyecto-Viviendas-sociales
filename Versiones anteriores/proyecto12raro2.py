import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from pykml import parser
import math

# --- Clase KMLProcessor ---
class KMLProcessor:
    def __init__(self):
        self.bounding_box = None
        self.inner_area = None
        self.base_units = [] # Volvemos a una lista única
        self.stair_units = []
        self.central_area = None
        self.offset_value = 0
        self.base_width_value = 0
        self.base_length_value = 0

    # --- load_kml (sin cambios respecto a la versión anterior) ---
    def load_kml(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    doc = parser.parse(f).getroot().find('.//{http://www.opengis.net/kml/2.2}Document')
                    if doc is None:
                         f.seek(0)
                         doc = parser.parse(f).getroot().find('.//{http://earth.google.com/kml/2.2}Document')
                    if doc is None:
                        f.seek(0)
                        doc = parser.parse(f).getroot()
                except Exception as parse_err:
                     return False, f"Error al parsear KML: {str(parse_err)}"

                polygon = None
                for p in doc.iterfind('.//{http://www.opengis.net/kml/2.2}Polygon'):
                    polygon = p
                    break
                if polygon is None:
                     for p in doc.iterfind('.//{http://earth.google.com/kml/2.2}Polygon'):
                        polygon = p
                        break
                if polygon is None: return False, "No se encontró polígono en KML"

                coordinates = None
                coord_paths = [
                    './/{http://www.opengis.net/kml/2.2}outerBoundaryIs/{http://www.opengis.net/kml/2.2}LinearRing/{http://www.opengis.net/kml/2.2}coordinates',
                    './/{http://www.opengis.net/kml/2.2}coordinates',
                    './/{http://earth.google.com/kml/2.2}outerBoundaryIs/{http://earth.google.com/kml/2.2}LinearRing/{http://earth.google.com/kml/2.2}coordinates',
                    './/{http://earth.google.com/kml/2.2}coordinates'
                ]
                for path in coord_paths:
                    coordinates = polygon.find(path)
                    if coordinates is not None and coordinates.text:
                        break
                if coordinates is None or not coordinates.text:
                    return False, "No se encontraron coordenadas válidas en el polígono"

                coords_text = coordinates.text.strip()
                coords_pairs = coords_text.split()
                coords = []
                for pair in coords_pairs:
                    try:
                        parts = pair.split(',')
                        if len(parts) >= 2:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            coords.append((lon, lat))
                        else: print(f"Advertencia: Ignorando par coords incompleto '{pair}'")
                    except ValueError: print(f"Advertencia: Ignorando par coords inválido '{pair}'")
                if not coords or len(coords) < 3: return False, "Coords insuficientes."

                x_coords = [c[0] for c in coords]
                y_coords = [c[1] for c in coords]
                self.bounding_box = {'min_x': min(x_coords), 'max_x': max(x_coords),
                                     'min_y': min(y_coords), 'max_y': max(y_coords),
                                     'width': max(x_coords) - min(x_coords),
                                     'height': max(y_coords) - min(y_coords)}
                # Reset calculated areas
                self.inner_area = None
                self.base_units = []
                self.stair_units = []
                self.central_area = None
                return True, "KML cargado correctamente"
        except FileNotFoundError: return False, f"Error: Archivo no encontrado '{file_path}'"
        except Exception as e: return False, f"Error inesperado al leer KML: {str(e)}"

    # --- calculate_inner_area (sin cambios respecto a la versión anterior) ---
    def calculate_inner_area(self, offset):
        if not self.bounding_box: return False, "Cargue un KML primero"
        if offset < 0: return False, "Offset no puede ser negativo."
        self.offset_value = offset
        inner_width = self.bounding_box['width'] - 2 * offset
        inner_height = self.bounding_box['height'] - 2 * offset

        if inner_width <= 0 or inner_height <= 0:
            self.inner_area = None
            return False, "Offset demasiado grande, área interna inválida."

        self.inner_area = {'min_x': self.bounding_box['min_x'] + offset,
                           'max_x': self.bounding_box['max_x'] - offset,
                           'min_y': self.bounding_box['min_y'] + offset,
                           'max_y': self.bounding_box['max_y'] - offset,
                           'width': inner_width, 'height': inner_height}
        return True, "Área interna calculada"

    # --- calculate_units (NUEVA LÓGICA DE ORIENTACIÓN) ---
    def calculate_units(self, base_width, base_length):
        if not self.inner_area: return False, "Calcule el área interna primero"
        if base_width <= 0 or base_length <= 0: return False, "Dims base deben ser > 0."

        self.base_width_value = base_width
        self.base_length_value = base_length
        stair_size = max(base_width, base_length)

        # Ajustar stair_size si no cabe
        required_dim = 2 * stair_size
        if required_dim > self.inner_area['width'] or required_dim > self.inner_area['height']:
             available_space = min(self.inner_area['width'], self.inner_area['height'])
             if available_space < required_dim:
                  stair_size = available_space / 2
                  print(f"Advertencia: Tamaño unidad escalera reducido a {stair_size:.2f} para caber.")
                  if stair_size <= 0 :
                       return False, "Unidades escalera no caben en área interna."

        # --- Unidades Escalera ---
        self.stair_units = [
            {'x': self.inner_area['min_x'], 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size}, # inf-izq
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size}, # inf-der
            {'x': self.inner_area['min_x'], 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}, # sup-izq
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}  # sup-der
        ]

        # --- Área Central (opcional) ---
        center_avail_width = max(0, self.inner_area['width'] - 2 * stair_size)
        center_avail_height = max(0, self.inner_area['height'] - 2 * stair_size)
        central_size = min(center_avail_width, center_avail_height) * 0.4
        if central_size > 0:
            center_x = self.inner_area['min_x'] + stair_size + center_avail_width / 2
            center_y = self.inner_area['min_y'] + stair_size + center_avail_height / 2
            self.central_area = {'min_x': center_x - central_size / 2, 'max_x': center_x + central_size / 2,
                                 'min_y': center_y - central_size / 2, 'max_y': center_y + central_size / 2,
                                 'width': central_size, 'height': central_size}
        else: self.central_area = None

        # --- Unidades Base ---
        self.base_units = [] # Reiniciar lista única
        epsilon = 1e-9

        # --- Lado INFERIOR (Orientación VERTICAL) ---
        # Junto a lados horizontales de escaleras inf. -> Vertical
        x_start_bottom = self.stair_units[0]['x'] + stair_size
        x_end_bottom = self.stair_units[1]['x']
        y_bottom = self.inner_area['min_y']
        current_x = x_start_bottom
        unit_width_v = base_length # Ancho es Largo
        unit_height_v = base_width # Alto es Ancho
        while current_x + unit_width_v <= x_end_bottom + epsilon:
            self.base_units.append({'x': current_x, 'y': y_bottom, 'width': unit_width_v, 'height': unit_height_v})
            current_x += unit_width_v # Incrementar por el nuevo ancho (largo original)

        # --- Lado SUPERIOR (Orientación VERTICAL) ---
        # Junto a lados horizontales de escaleras sup. -> Vertical
        x_start_top = self.stair_units[2]['x'] + stair_size
        x_end_top = self.stair_units[3]['x']
        # Posición Y: Borde superior menos la nueva altura (ancho original)
        y_top = self.inner_area['max_y'] - unit_height_v
        current_x = x_start_top
        while current_x + unit_width_v <= x_end_top + epsilon:
            self.base_units.append({'x': current_x, 'y': y_top, 'width': unit_width_v, 'height': unit_height_v})
            current_x += unit_width_v # Incrementar por el nuevo ancho

        # --- Lado IZQUIERDO (Orientación HORIZONTAL) ---
        # Junto a lados verticales de escaleras izq. -> Horizontal
        x_left = self.inner_area['min_x']
        y_start_left = self.stair_units[0]['y'] + stair_size
        y_end_left = self.stair_units[2]['y']
        current_y = y_start_left
        unit_width_h = base_width # Ancho normal
        unit_height_h = base_length # Alto normal
        while current_y + unit_height_h <= y_end_left + epsilon:
            self.base_units.append({'x': x_left, 'y': current_y, 'width': unit_width_h, 'height': unit_height_h})
            current_y += unit_height_h # Incrementar por la altura

        # --- Lado DERECHO (Orientación HORIZONTAL) ---
        # Junto a lados verticales de escaleras der. -> Horizontal
        x_right = self.inner_area['max_x'] - unit_width_h # Posición X: Borde derecho menos el ancho normal
        y_start_right = self.stair_units[1]['y'] + stair_size
        y_end_right = self.stair_units[3]['y']
        current_y = y_start_right
        while current_y + unit_height_h <= y_end_right + epsilon:
            self.base_units.append({'x': x_right, 'y': current_y, 'width': unit_width_h, 'height': unit_height_h})
            current_y += unit_height_h # Incrementar por la altura

        # (Opcional) Podríamos re-introducir la eliminación de duplicados si sospechamos solapamientos
        # unique_units = []; seen = set()
        # for unit in self.base_units:
        #     key = (round(unit['x'], 6), round(unit['y'], 6))
        #     if key not in seen: seen.add(key); unique_units.append(unit)
        # self.base_units = unique_units

        return True, f"{len(self.base_units)} unidades base y {len(self.stair_units)} unidades escalera calculadas"


# --- Clase Application (GUI estilo anterior) ---
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno")
        self.geometry("850x650") # Ajustar tamaño si es necesario

        self.kml_processor = KMLProcessor()
        self.current_figure = None
        self.canvas = None
        self.toolbar = None

        # Frame para controles arriba, plot abajo
        self.control_frame = tk.Frame(self)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.plot_frame = tk.Frame(self)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.create_widgets() # Llama al método para crear los widgets

    # --- create_widgets (Estilo anterior) ---
    def create_widgets(self):
        # Botón Cargar
        self.load_button = tk.Button(self.control_frame, text="Cargar Archivo KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=(5, 10)) # Añadir padding derecho

        # Frame para parámetros en línea
        param_frame = tk.Frame(self.control_frame)
        param_frame.pack(side=tk.LEFT, padx=0)

        # Distancia Corona
        tk.Label(param_frame, text="Dist. Corona (m):").pack(side=tk.LEFT, padx=(0,2))
        self.offset_entry = tk.Entry(param_frame, width=7)
        self.offset_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.offset_entry.insert(0, "5")

        # Ancho Base
        tk.Label(param_frame, text="Ancho Base (m):").pack(side=tk.LEFT, padx=(0,2))
        self.base_width_entry = tk.Entry(param_frame, width=7)
        self.base_width_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.base_width_entry.insert(0, "3") # Ejemplo

        # Largo Base
        tk.Label(param_frame, text="Largo Base (m):").pack(side=tk.LEFT, padx=(0,2))
        self.base_length_entry = tk.Entry(param_frame, width=7)
        self.base_length_entry.pack(side=tk.LEFT, padx=(0, 15)) # Más padding derecho
        self.base_length_entry.insert(0, "2") # Ejemplo

        # Botón Calcular
        self.calculate_button = tk.Button(self.control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED)
        self.calculate_button.pack(side=tk.LEFT, padx=5)

        # Barra de Estado (abajo de la ventana principal)
        self.status_var = tk.StringVar()
        self.status_var.set("Listo. Cargue un archivo KML.")
        # Empaquetar la etiqueta de estado en la ventana principal 'self', no en 'control_frame'
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X) # Abajo del todo

    # --- load_kml (sin cambios funcionales mayores) ---
    def load_kml(self):
        self._clear_plot()
        file_path = filedialog.askopenfilename(title="Seleccionar archivo KML", filetypes=[("KML files", "*.kml"), ("All files", "*.*")])
        if file_path:
            self.status_var.set(f"Cargando {file_path}...")
            self.update_idletasks()
            success, message = self.kml_processor.load_kml(file_path)
            if success:
                bb = self.kml_processor.bounding_box
                fname = file_path.split('/')[-1]
                self.status_var.set(f"KML '{fname}' cargado. W={bb['width']:.2f}, H={bb['height']:.2f}. Calcule.")
                self.calculate_button['state'] = tk.NORMAL
            else:
                messagebox.showerror("Error al cargar KML", message)
                self.status_var.set("Error al cargar KML.")
                self.calculate_button['state'] = tk.DISABLED

    # --- calculate_and_visualize (sin cambios funcionales mayores) ---
    def calculate_and_visualize(self):
        if not self.kml_processor.bounding_box:
             messagebox.showwarning("Operación Inválida", "Cargue un KML primero.")
             return
        try:
            offset = float(self.offset_entry.get())
            base_width = float(self.base_width_entry.get())
            base_length = float(self.base_length_entry.get())
            if offset < 0 or base_width <= 0 or base_length <= 0:
                 messagebox.showerror("Error de Entrada", "Offset >= 0. Ancho y Largo > 0.")
                 return
        except ValueError:
            messagebox.showerror("Error de Entrada", "Valores numéricos inválidos.")
            return

        self.status_var.set("Calculando área interna...")
        self.update_idletasks()
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success:
            messagebox.showerror("Error Cálculo (Área Interna)", message)
            self.status_var.set(f"Error: {message}")
            self._clear_plot(); return

        self.status_var.set("Calculando unidades...")
        self.update_idletasks()
        success, message = self.kml_processor.calculate_units(base_width, base_length)
        if not success:
            messagebox.showerror("Error Cálculo (Unidades)", message)
            self.status_var.set(f"Error: {message}")
            self._clear_plot(); return

        self.status_var.set("Generando visualización...")
        self.update_idletasks()
        self._visualize_results()
        self.status_var.set(f"Visualización completa. {message}")

    # --- _clear_plot (sin cambios) ---
    def _clear_plot(self):
         if self.canvas: self.canvas.get_tk_widget().destroy(); self.canvas = None
         if self.toolbar and self.toolbar.winfo_exists(): self.toolbar.destroy(); self.toolbar = None
         for widget in self.plot_frame.winfo_children(): widget.destroy()

    # --- _visualize_results (adaptado a lista única 'base_units') ---
    def _visualize_results(self):
        self._clear_plot()
        if not self.kml_processor.bounding_box: return
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal', adjustable='box')
        bb = self.kml_processor.bounding_box

        # 1. Bounding Box
        ax.add_patch(Rectangle((bb['min_x'], bb['min_y']), bb['width'], bb['height'],
                               edgecolor='black', facecolor='whitesmoke', alpha=0.5, lw=1.5, label='Bounding Box'))

        if self.kml_processor.inner_area:
            ia = self.kml_processor.inner_area
            offset = self.kml_processor.offset_value
            # 2. Inner Area
            ax.add_patch(Rectangle((ia['min_x'], ia['min_y']), ia['width'], ia['height'],
                                   edgecolor='blue', facecolor='none', ls='--', lw=1.5, label=f'Área Interna (Off:{offset})'))
            # 3. Central Area
            if self.kml_processor.central_area:
                ca = self.kml_processor.central_area
                ax.add_patch(Rectangle((ca['min_x'], ca['min_y']), ca['width'], ca['height'],
                                       edgecolor='purple', facecolor='lavender', alpha=0.7, label='Área Central'))
            # 4. Stair Units
            stair_plotted = False
            for unit in self.kml_processor.stair_units:
                label = 'Unidades Escalera' if not stair_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='darkred', facecolor='salmon', alpha=0.85, label=label))
                stair_plotted = True

            # 5. Base Units (Single List)
            base_plotted = False
            for unit in self.kml_processor.base_units:
                label = 'Unidades Base' if not base_plotted else ""
                # Usar un solo color por simplicidad, la orientación será visible
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='darkgreen', facecolor='lightgreen', alpha=0.8, label=label))
                base_plotted = True

        # --- Plot Setup ---
        padding_x = bb['width'] * 0.07; padding_y = bb['height'] * 0.07
        padding_x = max(padding_x, 1); padding_y = max(padding_y, 1)
        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x)
        ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)
        ax.set_xlabel("Coordenada X / Longitud"); ax.set_ylabel("Coordenada Y / Latitud")
        title = "Distribución de Unidades"
        if self.kml_processor.base_width_value > 0:
             title += f" (Base:{self.kml_processor.base_width_value}x{self.kml_processor.base_length_value}m)"
        ax.set_title(title); ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(fontsize='small', loc='best')

        # --- Embed in Tkinter ---
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw(); canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update(); self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

# --- Main execution block ---
if __name__ == "__main__":
    app = Application()
    app.mainloop()