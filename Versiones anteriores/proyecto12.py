import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from pykml import parser

class KMLProcessor:
    def __init__(self):
        self.bounding_box = None
        self.inner_area = None
        self.base_units = []
        self.stair_units = []
        self.central_area = None

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
                        lon, lat, *alt = map(float, pair.split(','))
                        coords.append((lon, lat))
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
                return True, "KML cargado correctamente"
        except FileNotFoundError:
             return False, f"Error: Archivo no encontrado en la ruta '{file_path}'"
        except Exception as e:
            # Catch other potential errors during file reading/processing
            return False, f"Error inesperado al leer el archivo KML: {str(e)}"


    def calculate_inner_area(self, offset):
        if not self.bounding_box:
            return False, "Primero debe cargar un archivo KML"

        # Check if offset is too large for the bounding box
        if 2 * offset >= self.bounding_box['width'] or 2 * offset >= self.bounding_box['height']:
            return False, f"El offset ({offset}) es demasiado grande para las dimensiones del terreno."

        self.inner_area = {
            'min_x': self.bounding_box['min_x'] + offset,
            'max_x': self.bounding_box['max_x'] - offset,
            'min_y': self.bounding_box['min_y'] + offset,
            'max_y': self.bounding_box['max_y'] - offset,
            'width': (self.bounding_box['max_x'] - offset) - (self.bounding_box['min_x'] + offset),
            'height': (self.bounding_box['max_y'] - offset) - (self.bounding_box['min_y'] + offset)
        }
        return True, "Área interna calculada"

    def calculate_units(self, base_width, base_length):
        if not self.inner_area:
            return False, "Primero debe calcular el área interna"
        if base_width <= 0 or base_length <= 0:
             return False, "El ancho y largo de la unidad base deben ser mayores que cero."

        stair_size = max(base_width, base_length) # Mantener la unidad escalera cuadrada

        # Check if stair units fit within the inner area
        if 2 * stair_size > self.inner_area['width'] or 2 * stair_size > self.inner_area['height']:
             return False, f"Las 'unidades escalera' (tamaño {stair_size}) son demasiado grandes para caber en el área interna."


        # Definir las 4 unidades escalera en las esquinas del ÁREA INTERNA
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

        # Calcular área central cuadrada (opcional, podrías quitarla si no es necesaria)
        central_size = min(self.inner_area['width'], self.inner_area['height']) * 0.4
        center_x = (self.inner_area['min_x'] + self.inner_area['max_x']) / 2
        center_y = (self.inner_area['min_y'] + self.inner_area['max_y']) / 2

        self.central_area = {
            'min_x': center_x - central_size / 2,
            'max_x': center_x + central_size / 2,
            'min_y': center_y - central_size / 2,
            'max_y': center_y + central_size / 2,
            'width': central_size,
            'height': central_size
        }

        # Generar unidades base HORIZONTALES ("acostadas")
        self.base_units = []
        epsilon = 1e-9 # Small value to handle floating point comparisons

        # --- Lado INFERIOR (Horizontal) ---
        # Empieza justo después de la unidad escalera inf-izq
        # Termina justo antes de la unidad escalera inf-der
        # Se pega al borde inferior del inner_area
        x = self.stair_units[0]['x'] + stair_size
        y = self.inner_area['min_y'] # Pegado al borde inferior
        while x + base_width <= self.stair_units[1]['x'] + epsilon: # <= para incluir la última si cabe exacta
            self.base_units.append({'x': x, 'y': y, 'width': base_width, 'height': base_length})
            x += base_width

        # --- Lado SUPERIOR (Horizontal) ---
        # Empieza justo después de la unidad escalera sup-izq
        # Termina justo antes de la unidad escalera sup-der
        # Se pega al borde superior del inner_area
        x = self.stair_units[2]['x'] + stair_size
        y = self.inner_area['max_y'] - base_length # Pegado al borde superior
        while x + base_width <= self.stair_units[3]['x'] + epsilon:
            self.base_units.append({'x': x, 'y': y, 'width': base_width, 'height': base_length})
            x += base_width

        # --- Lado IZQUIERDO (Orientación Horizontal) ---
        # Empieza justo encima de la unidad escalera inf-izq
        # Termina justo debajo de la unidad escalera sup-izq
        # Se pega al borde izquierdo del inner_area
        x = self.inner_area['min_x'] # Pegado al borde izquierdo
        y = self.stair_units[0]['y'] + stair_size
        while y + base_length <= self.stair_units[2]['y'] + epsilon:
            self.base_units.append({'x': x, 'y': y, 'width': base_width, 'height': base_length})
            y += base_length # Incrementa en Y porque se apilan verticalmente

        # --- Lado DERECHO (Orientación Horizontal) ---
        # Empieza justo encima de la unidad escalera inf-der
        # Termina justo debajo de la unidad escalera sup-der
        # Se pega al borde derecho del inner_area
        x = self.inner_area['max_x'] - base_width # Pegado al borde derecho
        y = self.stair_units[1]['y'] + stair_size
        while y + base_length <= self.stair_units[3]['y'] + epsilon:
            self.base_units.append({'x': x, 'y': y, 'width': base_width, 'height': base_length})
            y += base_length # Incrementa en Y

        # Eliminar unidades duplicadas (aunque con la lógica actual no deberían generarse)
        unique_units = []
        seen = set()
        for unit in self.base_units:
            # Usar tupla redondeada para evitar problemas de precisión flotante
            key = (round(unit['x'], 6), round(unit['y'], 6))
            if key not in seen:
                seen.add(key)
                unique_units.append(unit)
        self.base_units = unique_units

        return True, f"{len(self.base_units)} unidades base (horizontales) y 4 unidades escalera calculadas"


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno")
        self.geometry("900x700") # Slightly larger window

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

        self.load_button = tk.Button(control_frame, text="Cargar Archivo KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=5)

        param_frame = tk.Frame(control_frame)
        param_frame.pack(side=tk.LEFT, padx=10)

        tk.Label(param_frame, text="Distancia Corona (m):").grid(row=0, column=0, sticky=tk.W)
        self.offset_entry = tk.Entry(param_frame, width=10)
        self.offset_entry.grid(row=0, column=1, padx=5)
        self.offset_entry.insert(0, "5")

        tk.Label(param_frame, text="Ancho Unidad Base (m):").grid(row=1, column=0, sticky=tk.W)
        self.base_width_entry = tk.Entry(param_frame, width=10)
        self.base_width_entry.grid(row=1, column=1, padx=5)
        self.base_width_entry.insert(0, "3") # Adjusted default

        tk.Label(param_frame, text="Largo Unidad Base (m):").grid(row=2, column=0, sticky=tk.W)
        self.base_length_entry = tk.Entry(param_frame, width=10)
        self.base_length_entry.grid(row=2, column=1, padx=5)
        self.base_length_entry.insert(0, "2") # Adjusted default

        self.calculate_button = tk.Button(control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize)
        self.calculate_button.pack(side=tk.LEFT, padx=5)

        # Status bar at the bottom of the control frame
        self.status_var = tk.StringVar()
        self.status_var.set("Listo. Cargue un archivo KML.")
        self.status_label = tk.Label(control_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        # Make status label expand to fill remaining space
        self.status_label.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)


    def load_kml(self):
         # Clear previous plot when loading a new file
        self._clear_plot()
        self.kml_processor = KMLProcessor() # Reset processor state

        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo KML",
            filetypes=[("KML files", "*.kml"), ("All files", "*.*")]
            )
        if file_path:
            self.status_var.set(f"Cargando {file_path}...")
            self.update_idletasks() # Ensure status update is visible

            success, message = self.kml_processor.load_kml(file_path)
            if success:
                bb = self.kml_processor.bounding_box
                self.status_var.set(f"KML cargado. BB:({bb['min_x']:.2f},{bb['min_y']:.2f})->({bb['max_x']:.2f},{bb['max_y']:.2f}). Ingrese parámetros y calcule.")
                # Optionally, visualize just the bounding box immediately
                # self.visualize_initial()
            else:
                messagebox.showerror("Error al cargar KML", message)
                self.status_var.set("Error al cargar KML. Intente con otro archivo.")

    def calculate_and_visualize(self):
        if not self.kml_processor.bounding_box:
             messagebox.showwarning("Advertencia", "Primero debe cargar un archivo KML válido.")
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

            if offset < 0 or base_width <= 0 or base_length <= 0:
                 messagebox.showerror("Error de Entrada", "La distancia corona no puede ser negativa. El ancho y largo deben ser positivos.")
                 return

        except ValueError:
            messagebox.showerror("Error de Entrada", "Por favor ingrese valores numéricos válidos para distancia, ancho y largo.")
            return

        self.status_var.set("Calculando área interna...")
        self.update_idletasks()

        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success:
            messagebox.showerror("Error de Cálculo", message)
            self.status_var.set(f"Error: {message}")
            return

        self.status_var.set("Calculando unidades...")
        self.update_idletasks()

        success, message = self.kml_processor.calculate_units(base_width, base_length)
        if not success:
            messagebox.showerror("Error de Cálculo", message)
            self.status_var.set(f"Error: {message}")
            return

        self.status_var.set("Generando visualización...")
        self.update_idletasks()

        self._visualize_results() # Call the renamed visualization method
        self.status_var.set(f"Visualización completa. {message}")

    def _clear_plot(self):
         """Clears the Matplotlib canvas and toolbar."""
         if self.canvas:
             self.canvas.get_tk_widget().destroy()
             self.canvas = None
         if self.toolbar:
             self.toolbar.destroy()
             self.toolbar = None
         # Clear plot frame content just in case
         for widget in self.plot_frame.winfo_children():
              widget.destroy()


    def _visualize_results(self):
        """Visualizes the bounding box, inner area, and calculated units."""
        self._clear_plot() # Clear previous plot first

        if not self.kml_processor.bounding_box or not self.kml_processor.inner_area:
            self.status_var.set("No hay datos suficientes para visualizar.")
            return

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal', adjustable='box') # Ensure aspect ratio is equal

        bb = self.kml_processor.bounding_box
        ia = self.kml_processor.inner_area

        # 1. Draw Bounding Box
        ax.add_patch(Rectangle(
            (bb['min_x'], bb['min_y']), bb['width'], bb['height'],
            edgecolor='black', facecolor='none', linewidth=2, label='Bounding Box KML'
        ))

        # 2. Draw Inner Area
        ax.add_patch(Rectangle(
            (ia['min_x'], ia['min_y']), ia['width'], ia['height'],
            edgecolor='blue', facecolor='none', linestyle='--', linewidth=2, label=f'Área Interna (Offset: {self.offset_entry.get()} m)'
        ))

        # 3. Draw Central Area (if calculated)
        if self.kml_processor.central_area:
            ca = self.kml_processor.central_area
            ax.add_patch(Rectangle(
                (ca['min_x'], ca['min_y']), ca['width'], ca['height'],
                edgecolor='purple', facecolor='lavender', alpha=0.6, label='Área Central'
            ))

        # 4. Draw Base Units
        base_unit_plotted = False
        for unit in self.kml_processor.base_units:
            label = 'Unidades Base' if not base_unit_plotted else ""
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='darkgreen', facecolor='lightgreen', alpha=0.8, label=label
            ))
            base_unit_plotted = True # Add label only once

        # 5. Draw Stair Units
        stair_unit_plotted = False
        for unit in self.kml_processor.stair_units:
            label = 'Unidades Escalera' if not stair_unit_plotted else ""
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='darkred', facecolor='salmon', alpha=0.8, label=label
            ))
            stair_unit_plotted = True # Add label only once


        # Set plot limits slightly padded around the bounding box
        padding_x = bb['width'] * 0.05
        padding_y = bb['height'] * 0.05
        # Handle cases where padding might be zero
        padding_x = max(padding_x, 1)
        padding_y = max(padding_y, 1)

        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x)
        ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)

        ax.set_xlabel("Coordenada X / Longitud (grados decimales)")
        ax.set_ylabel("Coordenada Y / Latitud (grados decimales)")
        ax.set_title("Distribución de Unidades en Terreno")
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(fontsize='small') # Add legend to identify elements

        # Embed plot in Tkinter window
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame) # Embed in plot_frame
        self.canvas.draw()
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add navigation toolbar below the plot
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame) # Embed in plot_frame
        self.toolbar.update()
        # Pack toolbar *below* the canvas
        # canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True) # This was packing it twice
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)


if __name__ == "__main__":
    app = Application()
    app.mainloop()