# Imports necesarios (asumiendo que están al inicio del archivo)
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from pykml import parser
import math # Necesario para ceil

class KMLProcessor:
    def __init__(self):
        self.bounding_box = None
        self.inner_area = None
        self.base_units_horizontal = [] # Separar listas para claridad
        self.base_units_vertical = []
        self.stair_units = []
        self.central_area = None
        self.offset_value = 0 # Guardar el offset usado
        self.base_width_value = 0 # Guardar dimensiones usadas
        self.base_length_value = 0

    # --- load_kml --- (sin cambios respecto a la versión anterior)
    def load_kml(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: # Added encoding for broader compatibility
                # Try parsing with common namespaces first
                try:
                    # Standard KML namespace
                    doc = parser.parse(f).getroot().find('.//{http://www.opengis.net/kml/2.2}Document')
                    if doc is None:
                         # Google Earth KML namespace (sometimes used)
                         f.seek(0) # Reset file pointer
                         doc = parser.parse(f).getroot().find('.//{http://earth.google.com/kml/2.2}Document')
                    if doc is None:
                        # Fallback to root if no Document tag
                        f.seek(0)
                        doc = parser.parse(f).getroot()

                except Exception as parse_err:
                     return False, f"Error al parsear KML: {str(parse_err)}"


                # Find the first Polygon regardless of its parent structure
                polygon = None
                for p in doc.iterfind('.//{http://www.opengis.net/kml/2.2}Polygon'):
                    polygon = p
                    break
                # Try Google Earth namespace if not found
                if polygon is None:
                     for p in doc.iterfind('.//{http://earth.google.com/kml/2.2}Polygon'):
                        polygon = p
                        break

                if polygon is None:
                    return False, "No se encontró un polígono en el archivo KML"

                coordinates = None
                # Look for coordinates within the polygon structure
                coord_path = './/{http://www.opengis.net/kml/2.2}outerBoundaryIs/{http://www.opengis.net/kml/2.2}LinearRing/{http://www.opengis.net/kml/2.2}coordinates'
                coordinates = polygon.find(coord_path)
                if coordinates is None:
                    # Fallback for simpler structure or different namespace
                    coord_path_alt1 = './/{http://www.opengis.net/kml/2.2}coordinates'
                    coordinates = polygon.find(coord_path_alt1)
                if coordinates is None:
                    coord_path_google = './/{http://earth.google.com/kml/2.2}outerBoundaryIs/{http://earth.google.com/kml/2.2}LinearRing/{http://earth.google.com/kml/2.2}coordinates'
                    coordinates = polygon.find(coord_path_google)
                if coordinates is None:
                     coord_path_google_alt1 = './/{http://earth.google.com/kml/2.2}coordinates'
                     coordinates = polygon.find(coord_path_google_alt1)


                if coordinates is None or not coordinates.text:
                    return False, "No se encontraron coordenadas válidas en el polígono"

                # Clean up coordinates string (remove altitude, handle extra spaces)
                coords_text = coordinates.text.strip()
                coords_pairs = coords_text.split()
                coords = []
                for pair in coords_pairs:
                    try:
                        # Attempt to read lon, lat, potentially ignoring altitude if present
                        parts = pair.split(',')
                        if len(parts) >= 2:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            coords.append((lon, lat))
                        else:
                             print(f"Advertencia: Ignorando par de coordenadas incompleto '{pair}'")
                    except ValueError:
                        # Skip invalid coordinate pairs
                        print(f"Advertencia: Ignorando par de coordenadas inválido '{pair}'")
                        continue

                if not coords or len(coords) < 3:
                     return False, "No hay suficientes coordenadas válidas para formar un polígono."


                x_coords = [c[0] for c in coords]
                y_coords = [c[1] for c in coords]

                self.bounding_box = {
                    'min_x': min(x_coords),
                    'max_x': max(x_coords),
                    'min_y': min(y_coords),
                    'max_y': max(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords)
                }
                # Reset calculated areas when loading new KML
                self.inner_area = None
                self.base_units_horizontal = []
                self.base_units_vertical = []
                self.stair_units = []
                self.central_area = None
                return True, "KML cargado correctamente"
        except FileNotFoundError:
             return False, f"Error: Archivo no encontrado en la ruta '{file_path}'"
        except Exception as e:
            # Catch other potential errors during file reading/processing
            return False, f"Error inesperado al leer el archivo KML: {str(e)}"

    # --- calculate_inner_area --- (sin cambios respecto a la versión anterior)
    def calculate_inner_area(self, offset):
        if not self.bounding_box:
            return False, "Primero debe cargar un archivo KML"

        # Check if offset is too large for the bounding box
        # Allow zero offset
        if offset < 0:
             return False, "El offset (Distancia Corona) no puede ser negativo."
        if 2 * offset > self.bounding_box['width'] or 2 * offset > self.bounding_box['height']:
            # Warning instead of error if offset is large but non-negative
            print(f"Advertencia: El offset ({offset}) es grande para las dimensiones del terreno, puede resultar en área interna negativa o cero.")
            # return False, f"El offset ({offset}) es demasiado grande para las dimensiones del terreno."


        self.offset_value = offset # Guardar valor
        self.inner_area = {
            'min_x': self.bounding_box['min_x'] + offset,
            'max_x': self.bounding_box['max_x'] - offset,
            'min_y': self.bounding_box['min_y'] + offset,
            'max_y': self.bounding_box['max_y'] - offset,
            # Calculate width/height, ensuring they are not negative
            'width': max(0, (self.bounding_box['max_x'] - offset) - (self.bounding_box['min_x'] + offset)),
            'height': max(0, (self.bounding_box['max_y'] - offset) - (self.bounding_box['min_y'] + offset))
        }

        if self.inner_area['width'] <= 0 or self.inner_area['height'] <= 0:
             # Handle case where offset makes inner area invalid
             self.inner_area = None # Invalidate inner area
             return False, "El offset es demasiado grande, resultando en un área interna inválida (ancho o alto cero o negativo)."

        return True, "Área interna calculada"

    def calculate_units(self, base_width, base_length):
        if not self.inner_area:
            return False, "Primero debe calcular el área interna"
        if base_width <= 0 or base_length <= 0:
             return False, "El ancho y largo de la unidad base deben ser mayores que cero."

        self.base_width_value = base_width # Guardar valores
        self.base_length_value = base_length

        stair_size = max(base_width, base_length) # Mantener la unidad escalera cuadrada

        # Check if stair units fit within the inner area
        # Use math.ceil to ensure we don't place partial units if stair_size is large
        required_width = 2 * stair_size
        required_height = 2 * stair_size

        if required_width > self.inner_area['width'] or required_height > self.inner_area['height']:
             # Make stair units fit if possible by reducing size, otherwise error
             available_width = self.inner_area['width'] / 2
             available_height = self.inner_area['height'] / 2
             stair_size = min(stair_size, available_width, available_height)
             print(f"Advertencia: Tamaño de unidad escalera reducido a {stair_size:.2f} para caber en el área interna.")
             if stair_size <= 0:
                  return False, f"Las 'unidades escalera' (basadas en ancho/largo {base_width}/{base_length}) son demasiado grandes para caber en el área interna, incluso reducidas."


        # --- Definir las 4 unidades escalera en las esquinas del ÁREA INTERNA ---
        self.stair_units = [
            # Esquina inferior izquierda (min_x, min_y)
            {'x': self.inner_area['min_x'], 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size},
            # Esquina inferior derecha (max_x, min_y)
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size},
            # Esquina superior izquierda (min_x, max_y)
            {'x': self.inner_area['min_x'], 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size},
            # Esquina superior derecha (max_x, max_y)
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}
        ]

        # --- Calcular área central (opcional) ---
        # Calculate based on space *between* stair units
        center_avail_width = max(0, self.inner_area['width'] - 2 * stair_size)
        center_avail_height = max(0, self.inner_area['height'] - 2 * stair_size)
        central_size = min(center_avail_width, center_avail_height) * 0.4 # 40% of the smallest available dimension

        if central_size > 0:
            center_x = self.inner_area['min_x'] + stair_size + center_avail_width / 2
            center_y = self.inner_area['min_y'] + stair_size + center_avail_height / 2
            self.central_area = {
                'min_x': center_x - central_size / 2,
                'max_x': center_x + central_size / 2,
                'min_y': center_y - central_size / 2,
                'max_y': center_y + central_size / 2,
                'width': central_size,
                'height': central_size
            }
        else:
            self.central_area = None # No space for central area


        # --- Generar unidades base ---
        self.base_units_horizontal = []
        self.base_units_vertical = []
        epsilon = 1e-9 # Small value to handle floating point comparisons

        # --- Lado INFERIOR (Horizontal) ---
        x_start_bottom = self.stair_units[0]['x'] + stair_size
        x_end_bottom = self.stair_units[1]['x']
        y_bottom = self.inner_area['min_y']
        current_x = x_start_bottom
        while current_x + base_width <= x_end_bottom + epsilon:
            self.base_units_horizontal.append({'x': current_x, 'y': y_bottom, 'width': base_width, 'height': base_length})
            current_x += base_width

        # --- Lado SUPERIOR (Vertical - Dimensiones Invertidas) ---
        x_start_top = self.stair_units[2]['x'] + stair_size
        x_end_top = self.stair_units[3]['x']
        # La 'y' de inicio es el borde superior menos la NUEVA altura (que es base_width)
        y_top = self.inner_area['max_y'] - base_width
        current_x = x_start_top
        # El ancho ahora es base_length, la altura es base_width
        while current_x + base_length <= x_end_top + epsilon: # Usar base_length para el ancho
            self.base_units_vertical.append({'x': current_x, 'y': y_top, 'width': base_length, 'height': base_width}) # Dimensiones invertidas
            current_x += base_length # Incrementar por el nuevo ancho (base_length)


        # --- Lado IZQUIERDO (Horizontal) ---
        x_left = self.inner_area['min_x']
        y_start_left = self.stair_units[0]['y'] + stair_size
        y_end_left = self.stair_units[2]['y']
        current_y = y_start_left
        while current_y + base_length <= y_end_left + epsilon:
            self.base_units_horizontal.append({'x': x_left, 'y': current_y, 'width': base_width, 'height': base_length})
            current_y += base_length

        # --- Lado DERECHO (Horizontal) ---
        x_right = self.inner_area['max_x'] - base_width
        y_start_right = self.stair_units[1]['y'] + stair_size
        y_end_right = self.stair_units[3]['y']
        current_y = y_start_right
        while current_y + base_length <= y_end_right + epsilon:
            self.base_units_horizontal.append({'x': x_right, 'y': current_y, 'width': base_width, 'height': base_length})
            current_y += base_length

        # No se necesita eliminar duplicados si las listas están separadas y la lógica es correcta

        total_base_units = len(self.base_units_horizontal) + len(self.base_units_vertical)
        return True, f"{total_base_units} unidades base ({len(self.base_units_vertical)} verticales arriba, {len(self.base_units_horizontal)} horizontales en otros lados) y {len(self.stair_units)} unidades escalera calculadas"


# --- Clase Application ---
# Asegúrate de que el método visualize use las nuevas listas:
# self.kml_processor.base_units_horizontal y self.kml_processor.base_units_vertical

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno")
        self.geometry("950x750") # Slightly larger window

        self.kml_processor = KMLProcessor()
        self.current_figure = None
        self.canvas = None
        self.toolbar = None

        # Frame for plot
        self.plot_frame = tk.Frame(self)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)


        self.create_widgets()

    def create_widgets(self):
        control_frame = tk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # --- Botón Cargar ---
        self.load_button = tk.Button(control_frame, text="Cargar KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=5)

        # --- Frame para Parámetros ---
        param_frame = tk.Frame(control_frame)
        param_frame.pack(side=tk.LEFT, padx=10)

        # Distancia Corona
        tk.Label(param_frame, text="Dist. Corona (m):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.offset_entry = tk.Entry(param_frame, width=8)
        self.offset_entry.grid(row=0, column=1, padx=(0, 10)) # Pad right
        self.offset_entry.insert(0, "5")

        # Ancho Base
        tk.Label(param_frame, text="Ancho Base (m):").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.base_width_entry = tk.Entry(param_frame, width=8)
        self.base_width_entry.grid(row=0, column=3, padx=(0, 10)) # Pad right
        self.base_width_entry.insert(0, "3")

        # Largo Base
        tk.Label(param_frame, text="Largo Base (m):").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.base_length_entry = tk.Entry(param_frame, width=8)
        self.base_length_entry.grid(row=0, column=5, padx=(0, 5))
        self.base_length_entry.insert(0, "2")


        # --- Botón Calcular ---
        self.calculate_button = tk.Button(control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED) # Start disabled
        self.calculate_button.pack(side=tk.LEFT, padx=5)

        # --- Barra de Estado ---
        self.status_var = tk.StringVar()
        self.status_var.set("Listo. Cargue un archivo KML.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        # Pack status label at the very bottom of the main window
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)


    def load_kml(self):
         self._clear_plot()
         # No reiniciar el procesador aquí, permite re-calcular con mismos params
         # self.kml_processor = KMLProcessor() # Reset processor state if needed

         file_path = filedialog.askopenfilename(
             title="Seleccionar archivo KML",
             filetypes=[("KML files", "*.kml"), ("All files", "*.*")]
             )
         if file_path:
             self.status_var.set(f"Cargando {file_path}...")
             self.update_idletasks()

             # Load KML data into the *existing* processor instance
             success, message = self.kml_processor.load_kml(file_path)
             if success:
                 bb = self.kml_processor.bounding_box
                 self.status_var.set(f"KML cargado ({file_path.split('/')[-1]}). BB: W={bb['width']:.2f}, H={bb['height']:.2f}. Ingrese parámetros y calcule.")
                 self.calculate_button['state'] = tk.NORMAL # Enable calculate button
                 # Optional: Visualize bounding box only
                 # self._visualize_bounding_box()
             else:
                 messagebox.showerror("Error al cargar KML", message)
                 self.status_var.set("Error al cargar KML. Intente con otro archivo.")
                 self.calculate_button['state'] = tk.DISABLED # Disable if load fails

    def calculate_and_visualize(self):
        if not self.kml_processor.bounding_box:
             messagebox.showwarning("Operación Inválida", "Primero debe cargar un archivo KML válido.")
             return
        try:
            offset_str = self.offset_entry.get()
            base_width_str = self.base_width_entry.get()
            base_length_str = self.base_length_entry.get()

            if not offset_str or not base_width_str or not base_length_str:
                 messagebox.showerror("Error de Entrada", "Todos los campos (Distancia, Ancho, Largo) son requeridos.")
                 return

            offset = float(offset_str)
            base_width = float(base_width_str)
            base_length = float(base_length_str)

            # Basic validation
            if offset < 0:
                 messagebox.showerror("Error de Entrada", "La Distancia Corona no puede ser negativa.")
                 return
            if base_width <= 0 or base_length <= 0:
                 messagebox.showerror("Error de Entrada", "El Ancho y Largo Base deben ser positivos.")
                 return

        except ValueError:
            messagebox.showerror("Error de Entrada", "Por favor ingrese valores numéricos válidos para distancia, ancho y largo.")
            return

        # --- Calculation Steps ---
        self.status_var.set("Calculando área interna...")
        self.update_idletasks()
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success:
            messagebox.showerror("Error de Cálculo (Área Interna)", message)
            self.status_var.set(f"Error: {message}")
            self._clear_plot() # Clear plot on error
            return

        self.status_var.set("Calculando unidades...")
        self.update_idletasks()
        success, message = self.kml_processor.calculate_units(base_width, base_length)
        if not success:
            messagebox.showerror("Error de Cálculo (Unidades)", message)
            self.status_var.set(f"Error: {message}")
            self._clear_plot() # Clear plot on error
            return

        # --- Visualization ---
        self.status_var.set("Generando visualización...")
        self.update_idletasks()
        self._visualize_results()
        self.status_var.set(f"Visualización completa. {message}") # Display result message

    def _clear_plot(self):
         if self.canvas:
             self.canvas.get_tk_widget().destroy()
             self.canvas = None
         if self.toolbar:
             # Check if toolbar still exists before destroying
             if self.toolbar.winfo_exists():
                 self.toolbar.destroy()
             self.toolbar = None
         # Clear plot frame content
         for widget in self.plot_frame.winfo_children():
              widget.destroy()

    def _visualize_results(self):
        """Visualizes bounding box, inner area, and ALL calculated units."""
        self._clear_plot()

        if not self.kml_processor.bounding_box:
             self.status_var.set("No hay Bounding Box para visualizar.")
             return

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal', adjustable='box')

        bb = self.kml_processor.bounding_box

        # --- Draw Elements ---
        # 1. Bounding Box
        ax.add_patch(Rectangle(
            (bb['min_x'], bb['min_y']), bb['width'], bb['height'],
            edgecolor='black', facecolor='whitesmoke', alpha=0.5, linewidth=1.5, label='Bounding Box KML'
        ))

        # Check if inner area and units were calculated before drawing them
        if self.kml_processor.inner_area:
            ia = self.kml_processor.inner_area
            offset_val = self.kml_processor.offset_value

            # 2. Inner Area
            ax.add_patch(Rectangle(
                (ia['min_x'], ia['min_y']), ia['width'], ia['height'],
                edgecolor='blue', facecolor='none', linestyle='--', linewidth=1.5, label=f'Área Interna (Offset: {offset_val} m)'
            ))

            # 3. Central Area
            if self.kml_processor.central_area:
                ca = self.kml_processor.central_area
                ax.add_patch(Rectangle(
                    (ca['min_x'], ca['min_y']), ca['width'], ca['height'],
                    edgecolor='purple', facecolor='lavender', alpha=0.7, label='Área Central'
                ))

            # 4. Stair Units
            stair_unit_plotted = False
            for unit in self.kml_processor.stair_units:
                label = 'Unidades Escalera' if not stair_unit_plotted else ""
                ax.add_patch(Rectangle(
                    (unit['x'], unit['y']), unit['width'], unit['height'],
                    edgecolor='darkred', facecolor='salmon', alpha=0.85, label=label
                ))
                stair_unit_plotted = True

            # 5. Base Units (Horizontal)
            base_h_plotted = False
            for unit in self.kml_processor.base_units_horizontal:
                label = 'Unidades Base (Horiz.)' if not base_h_plotted else ""
                ax.add_patch(Rectangle(
                    (unit['x'], unit['y']), unit['width'], unit['height'],
                    edgecolor='darkgreen', facecolor='lightgreen', alpha=0.8, label=label
                ))
                base_h_plotted = True

            # 6. Base Units (Vertical - Top)
            base_v_plotted = False
            for unit in self.kml_processor.base_units_vertical:
                label = 'Unidades Base (Vert. Sup.)' if not base_v_plotted else ""
                ax.add_patch(Rectangle(
                    (unit['x'], unit['y']), unit['width'], unit['height'],
                    edgecolor='darkblue', facecolor='lightblue', alpha=0.8, label=label # Different color
                ))
                base_v_plotted = True


        # --- Plot Setup ---
        # Determine plot limits based on bounding box
        padding_x = bb['width'] * 0.07 # Increased padding slightly
        padding_y = bb['height'] * 0.07
        padding_x = max(padding_x, 1) # Ensure minimum padding
        padding_y = max(padding_y, 1)

        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x)
        ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)

        ax.set_xlabel("Coordenada X / Longitud")
        ax.set_ylabel("Coordenada Y / Latitud")
        title = "Distribución de Unidades en Terreno"
        if self.kml_processor.base_width_value > 0: # Add dims to title if calculated
             title += f" (Base: {self.kml_processor.base_width_value}x{self.kml_processor.base_length_value}m)"
        ax.set_title(title)
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(fontsize='small', loc='best') # 'best' location for legend

        # --- Embed in Tkinter ---
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

# --- Main execution block --- (sin cambios)
if __name__ == "__main__":
    app = Application()
    app.mainloop()