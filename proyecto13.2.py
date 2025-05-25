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
        self.outer_base_units = []
        self.inner_base_units = []
        self.corridor_units = []
        self.stair_units = []
        self.central_area = None
        self.offset_value = 0
        self.base_width_value = 0
        self.base_length_value = 0
        self.corridor_width_value = 0

    def load_kml(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    doc = parser.parse(f).getroot().find('.//{http://www.opengis.net/kml/2.2}Document')
                    if doc is None:
                         f.seek(0); doc = parser.parse(f).getroot().find('.//{http://earth.google.com/kml/2.2}Document')
                    if doc is None:
                        f.seek(0); doc = parser.parse(f).getroot()
                except Exception as parse_err: return False, f"Error KML Parse: {str(parse_err)}"
                polygon = None
                for p in doc.iterfind('.//{http://www.opengis.net/kml/2.2}Polygon'): polygon = p; break
                if polygon is None:
                     for p in doc.iterfind('.//{http://earth.google.com/kml/2.2}Polygon'): polygon = p; break
                if polygon is None: return False, "No se encontró polígono"
                coordinates = None; coord_paths = [ './/{http://www.opengis.net/kml/2.2}outerBoundaryIs/{http://www.opengis.net/kml/2.2}LinearRing/{http://www.opengis.net/kml/2.2}coordinates', './/{http://www.opengis.net/kml/2.2}coordinates', './/{http://earth.google.com/kml/2.2}outerBoundaryIs/{http://earth.google.com/kml/2.2}LinearRing/{http://earth.google.com/kml/2.2}coordinates', './/{http://earth.google.com/kml/2.2}coordinates']
                for path in coord_paths:
                    coordinates = polygon.find(path)
                    if coordinates is not None and coordinates.text: break
                if coordinates is None or not coordinates.text: return False, "No se encontraron coordenadas"
                coords_text = coordinates.text.strip(); coords_pairs = coords_text.split(); coords = []
                for pair in coords_pairs:
                    try:
                        parts = pair.split(',')
                        if len(parts) >= 2: coords.append((float(parts[0]), float(parts[1])))
                    except ValueError: pass
                if not coords or len(coords) < 3: return False, "Coords insuficientes."
                x_coords = [c[0] for c in coords]; y_coords = [c[1] for c in coords]
                self.bounding_box = {'min_x': min(x_coords), 'max_x': max(x_coords), 'min_y': min(y_coords), 'max_y': max(y_coords), 'width': max(x_coords) - min(x_coords), 'height': max(y_coords) - min(y_coords)}
                self.inner_area = None; self.outer_base_units = []; self.inner_base_units = []; self.corridor_units = []; self.stair_units = []; self.central_area = None
                return True, "KML cargado"
        except FileNotFoundError: return False, f"Error: Archivo no encontrado '{file_path}'"
        except Exception as e: return False, f"Error inesperado KML: {str(e)}"

    def calculate_inner_area(self, offset):
        if not self.bounding_box: return False, "Cargue KML"
        if offset < 0: return False, "Offset >= 0"
        self.offset_value = offset
        inner_width = self.bounding_box['width'] - 2 * offset; inner_height = self.bounding_box['height'] - 2 * offset
        if inner_width <= 0 or inner_height <= 0: self.inner_area = None; return False, "Offset grande, área interna inválida."
        self.inner_area = {'min_x': self.bounding_box['min_x'] + offset, 'max_x': self.bounding_box['max_x'] - offset, 'min_y': self.bounding_box['min_y'] + offset, 'max_y': self.bounding_box['max_y'] - offset, 'width': inner_width, 'height': inner_height}
        return True, "Área interna calculada"

    # --- calculate_units (CON AJUSTE DE POSICIÓN DE ESCALERAS) ---
    def calculate_units(self, base_width, base_length, corridor_width):
        if not self.inner_area: return False, "Calcule área interna"
        if base_width <= 0 or base_length <= 0 or corridor_width <= 0: return False, "Dims base y pasillo deben ser > 0."

        self.base_width_value = base_width
        self.base_length_value = base_length
        self.corridor_width_value = corridor_width
        epsilon = 1e-9

        # Tamaño intrínseco de la unidad escalera
        nominal_stair_size = (2 * base_width) + corridor_width

        if nominal_stair_size <= 0:
            # print("Advertencia: Tamaño nominal de escalera es <= 0. No se generarán unidades escalera.")
            self.stair_units = []
            # Considerar si es un error fatal o si se puede continuar sin escaleras
            # Por ahora, si no hay escaleras, el resto de la lógica se adaptará.
        
        # Verificar si caben dos escaleras (una a cada lado/extremo)
        if self.inner_area['width'] < 2 * nominal_stair_size or \
           self.inner_area['height'] < 2 * nominal_stair_size:
            # print(f"Advertencia: No caben 2 U.Escalera (tamaño {nominal_stair_size:.2f}) en InnerArea. Intentando reducir U.Escalera.")
            # Intentar reducir el tamaño de la escalera para que quepan al menos dos
            reducible_stair_size_w = self.inner_area['width'] / 2
            reducible_stair_size_h = self.inner_area['height'] / 2
            adjusted_stair_size = min(nominal_stair_size, reducible_stair_size_w, reducible_stair_size_h)
            
            if adjusted_stair_size < nominal_stair_size and adjusted_stair_size > 0:
                print(f"Info: Tamaño U.Escalera reducido de {nominal_stair_size:.2f} a {adjusted_stair_size:.2f} para caber.")
                nominal_stair_size = adjusted_stair_size
            elif adjusted_stair_size <=0 : # Incluso reducido no cabe o es inválido
                # print("Advertencia: U.Escalera no caben ni reducidas. No se generarán U.Escalera.")
                self.stair_units = []
                nominal_stair_size = 0 # Asegurar que es cero para lógica posterior
        
        # Si después de todo, nominal_stair_size es 0 o negativo, no hay escaleras.
        if nominal_stair_size <= 0:
            self.stair_units = []
            # print("Info: No se generarán Unidades Escalera (tamaño <=0).")
            # Las unidades base/pasillo ocuparán todo el inner_area
        
        # Dimensiones de las unidades base según su orientación
        unit_w_for_top_bottom_rows = base_length # Ancho de unidad vertical
        unit_h_for_left_right_rows = base_length # Alto de unidad horizontal

        # --- Calcular posiciones X finales de las escaleras ---
        stair_x0 = self.inner_area['min_x']
        stair_x2 = self.inner_area['min_x']
        
        available_width_for_units = self.inner_area['width'] - (2 * nominal_stair_size if nominal_stair_size > 0 else 0)
        num_fitted_horizontally = 0
        if nominal_stair_size > 0 and available_width_for_units >= unit_w_for_top_bottom_rows - epsilon : # Cabe al menos una
            num_fitted_horizontally = math.floor(available_width_for_units / unit_w_for_top_bottom_rows + epsilon)
        elif nominal_stair_size == 0 and self.inner_area['width'] >= unit_w_for_top_bottom_rows - epsilon: # No hay escaleras, usar todo el ancho
            num_fitted_horizontally = math.floor(self.inner_area['width'] / unit_w_for_top_bottom_rows + epsilon)

        occupied_by_horizontal_units = num_fitted_horizontally * unit_w_for_top_bottom_rows
        
        # La escalera derecha (x1, x3) se posiciona después de las unidades horizontales completas
        # y la escalera izquierda.
        stair_x1 = stair_x0 + (nominal_stair_size if nominal_stair_size > 0 else 0) + occupied_by_horizontal_units
        stair_x3 = stair_x1

        # --- Calcular posiciones Y finales de las escaleras ---
        stair_y0 = self.inner_area['min_y']
        stair_y1 = self.inner_area['min_y']

        available_height_for_units = self.inner_area['height'] - (2 * nominal_stair_size if nominal_stair_size > 0 else 0)
        num_fitted_vertically = 0
        if nominal_stair_size > 0 and available_height_for_units >= unit_h_for_left_right_rows - epsilon : # Cabe al menos una
            num_fitted_vertically = math.floor(available_height_for_units / unit_h_for_left_right_rows + epsilon)
        elif nominal_stair_size == 0 and self.inner_area['height'] >= unit_h_for_left_right_rows - epsilon: # No hay escaleras, usar toda la altura
            num_fitted_vertically = math.floor(self.inner_area['height'] / unit_h_for_left_right_rows + epsilon)

        occupied_by_vertical_units = num_fitted_vertically * unit_h_for_left_right_rows
        
        # La escalera superior (y2, y3) se posiciona después de las unidades verticales completas
        # y la escalera inferior.
        stair_y2 = stair_y0 + (nominal_stair_size if nominal_stair_size > 0 else 0) + occupied_by_vertical_units
        stair_y3 = stair_y2
        
        # --- Definir Unidades Escalera con posiciones ajustadas ---
        self.stair_units = [] # Limpiar por si acaso
        if nominal_stair_size > 0:
            self.stair_units.append({'x': stair_x0, 'y': stair_y0, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU0'})
            self.stair_units.append({'x': stair_x1, 'y': stair_y1, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU1'})
            self.stair_units.append({'x': stair_x2, 'y': stair_y2, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU2'})
            self.stair_units.append({'x': stair_x3, 'y': stair_y3, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU3'})
        
        # --- Calcular Área Central (basada en escaleras finales) ---
        self.central_area = None
        if self.stair_units and len(self.stair_units) == 4: # Solo si se generaron 4 escaleras
            # El espacio disponible para el centro es el rectángulo interior formado por las escaleras
            center_min_x = self.stair_units[0]['x'] + self.stair_units[0]['width'] # Borde derecho de SU0
            center_max_x = self.stair_units[1]['x'] # Borde izquierdo de SU1
            center_min_y = self.stair_units[0]['y'] + self.stair_units[0]['height'] # Borde superior de SU0
            center_max_y = self.stair_units[2]['y'] # Borde inferior de SU2

            center_avail_width = max(0, center_max_x - center_min_x)
            center_avail_height = max(0, center_max_y - center_min_y)
            central_size_dim = min(center_avail_width, center_avail_height) * 0.4
            
            if central_size_dim > epsilon:
                center_x_coord = center_min_x + center_avail_width / 2
                center_y_coord = center_min_y + center_avail_height / 2
                self.central_area = {
                    'min_x': center_x_coord - central_size_dim / 2, 'max_x': center_x_coord + central_size_dim / 2,
                    'min_y': center_y_coord - central_size_dim / 2, 'max_y': center_y_coord + central_size_dim / 2,
                    'width': central_size_dim, 'height': central_size_dim }

        # --- Generar Unidades Base Exteriores, Pasillos y Unidades Base Interiores ---
        self.outer_base_units = []; self.inner_base_units = []; self.corridor_units = []
        
        unit_w_v = base_length; unit_h_v = base_width
        unit_w_h = base_width; unit_h_h = base_length

        # Lado INFERIOR
        if self.stair_units and len(self.stair_units) >=2 : # Si hay escaleras para definir límites
            start_x_base_bottom = self.stair_units[0]['x'] + self.stair_units[0]['width']
            limit_x_base_bottom = self.stair_units[1]['x']
        else: # No hay escaleras, usar bordes del inner_area
            start_x_base_bottom = self.inner_area['min_x']
            limit_x_base_bottom = self.inner_area['max_x']
        
        y_outer_bottom = self.inner_area['min_y']
        current_x = start_x_base_bottom
        if current_x < limit_x_base_bottom - epsilon:
            for _ in range(num_fitted_horizontally): # Usar el número exacto calculado
                if current_x + unit_w_v > limit_x_base_bottom + epsilon: break # Seguridad
                self.outer_base_units.append({'x': current_x, 'y': y_outer_bottom, 'width': unit_w_v, 'height': unit_h_v})
                y_corridor = y_outer_bottom + unit_h_v
                self.corridor_units.append({'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_width})
                y_inner = y_corridor + corridor_width
                self.inner_base_units.append({'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v})
                current_x += unit_w_v
        
        # Lado SUPERIOR
        if self.stair_units and len(self.stair_units) >=4 :
            start_x_base_top = self.stair_units[2]['x'] + self.stair_units[2]['width']
            limit_x_base_top = self.stair_units[3]['x']
        else:
            start_x_base_top = self.inner_area['min_x']
            limit_x_base_top = self.inner_area['max_x']

        y_outer_top = self.inner_area['max_y'] - unit_h_v
        current_x = start_x_base_top
        if current_x < limit_x_base_top - epsilon:
            for _ in range(num_fitted_horizontally): # Usar el número exacto calculado
                if current_x + unit_w_v > limit_x_base_top + epsilon: break
                self.outer_base_units.append({'x': current_x, 'y': y_outer_top, 'width': unit_w_v, 'height': unit_h_v})
                y_corridor = y_outer_top - corridor_width
                self.corridor_units.append({'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_width})
                y_inner = y_corridor - unit_h_v
                self.inner_base_units.append({'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v})
                current_x += unit_w_v

        # Lado IZQUIERDO
        if self.stair_units and len(self.stair_units) >=3 :
            start_y_base_left = self.stair_units[0]['y'] + self.stair_units[0]['height']
            limit_y_base_left = self.stair_units[2]['y']
        else:
            start_y_base_left = self.inner_area['min_y']
            limit_y_base_left = self.inner_area['max_y']
            
        x_outer_left = self.inner_area['min_x']
        current_y = start_y_base_left
        if current_y < limit_y_base_left - epsilon:
            for _ in range(num_fitted_vertically): # Usar el número exacto calculado
                if current_y + unit_h_h > limit_y_base_left + epsilon: break
                self.outer_base_units.append({'x': x_outer_left, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h})
                x_corridor = x_outer_left + unit_w_h
                self.corridor_units.append({'x': x_corridor, 'y': current_y, 'width': corridor_width, 'height': unit_h_h})
                x_inner = x_corridor + corridor_width
                self.inner_base_units.append({'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h})
                current_y += unit_h_h

        # Lado DERECHO
        if self.stair_units and len(self.stair_units) >=4 :
            start_y_base_right = self.stair_units[1]['y'] + self.stair_units[1]['height']
            limit_y_base_right = self.stair_units[3]['y']
        else:
            start_y_base_right = self.inner_area['min_y']
            limit_y_base_right = self.inner_area['max_y']
            
        x_outer_right = self.inner_area['max_x'] - unit_w_h
        current_y = start_y_base_right
        if current_y < limit_y_base_right - epsilon:
            for _ in range(num_fitted_vertically): # Usar el número exacto calculado
                if current_y + unit_h_h > limit_y_base_right + epsilon: break
                self.outer_base_units.append({'x': x_outer_right, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h})
                x_corridor = x_outer_right - corridor_width
                self.corridor_units.append({'x': x_corridor, 'y': current_y, 'width': corridor_width, 'height': unit_h_h})
                x_inner = x_corridor - unit_w_h
                self.inner_base_units.append({'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h})
                current_y += unit_h_h
        
        total_base = len(self.outer_base_units) + len(self.inner_base_units)
        return True, (f"{total_base} U.Base ({len(self.outer_base_units)} Ext, {len(self.inner_base_units)} Int), "
                      f"{len(self.corridor_units)} U.Pasillo, {len(self.stair_units)} U.Escalera calculadas")


# --- Clase Application (sin cambios respecto a la versión anterior) ---
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno v2.3") # Versión actualizada
        self.geometry("950x700")

        self.kml_processor = KMLProcessor()
        self.current_figure = None
        self.canvas = None
        self.toolbar = None

        self.control_frame = tk.Frame(self)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.plot_frame = tk.Frame(self)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.create_widgets()

    def create_widgets(self):
        self.load_button = tk.Button(self.control_frame, text="Cargar KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=(5, 10))

        param_frame = tk.Frame(self.control_frame)
        param_frame.pack(side=tk.LEFT, padx=0)

        tk.Label(param_frame, text="D.Corona:").pack(side=tk.LEFT, padx=(0,1));
        self.offset_entry = tk.Entry(param_frame, width=6);
        self.offset_entry.pack(side=tk.LEFT, padx=(0, 5)); self.offset_entry.insert(0, "5")

        tk.Label(param_frame, text="An.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_width_entry = tk.Entry(param_frame, width=6);
        self.base_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_width_entry.insert(0, "3")

        tk.Label(param_frame, text="La.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_length_entry = tk.Entry(param_frame, width=6);
        self.base_length_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_length_entry.insert(0, "2")

        tk.Label(param_frame, text="An.Pasillo:").pack(side=tk.LEFT, padx=(0,1));
        self.corridor_width_entry = tk.Entry(param_frame, width=6);
        self.corridor_width_entry.pack(side=tk.LEFT, padx=(0, 10)); self.corridor_width_entry.insert(0, "1")

        self.calculate_button = tk.Button(self.control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED)
        self.calculate_button.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(); self.status_var.set("Listo. Cargue KML.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def load_kml(self):
        self._clear_plot()
        file_path = filedialog.askopenfilename(title="Seleccionar KML", filetypes=[("KML", "*.kml"), ("Todos", "*.*")])
        if file_path:
            self.status_var.set(f"Cargando {file_path}..."); self.update_idletasks()
            success, message = self.kml_processor.load_kml(file_path)
            if success:
                bb = self.kml_processor.bounding_box; fname = file_path.split('/')[-1]
                self.status_var.set(f"KML '{fname}' cargado. W={bb['width']:.2f}, H={bb['height']:.2f}. Calcule.")
                self.calculate_button['state'] = tk.NORMAL
            else:
                messagebox.showerror("Error KML", message); self.status_var.set("Error KML.")
                self.calculate_button['state'] = tk.DISABLED

    def calculate_and_visualize(self):
        if not self.kml_processor.bounding_box:
             messagebox.showwarning("Inválido", "Cargue KML primero."); return
        try:
            offset = float(self.offset_entry.get())
            base_width = float(self.base_width_entry.get())
            base_length = float(self.base_length_entry.get())
            corridor_width = float(self.corridor_width_entry.get())

            if offset < 0 or base_width <= 0 or base_length <= 0 or corridor_width <= 0:
                 messagebox.showerror("Entrada Inválida", "Offset >= 0. Anchos/Largos > 0.")
                 return
        except ValueError:
            messagebox.showerror("Entrada Inválida", "Valores numéricos inválidos."); return

        self.status_var.set("Calculando área interna..."); self.update_idletasks()
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success: messagebox.showerror("Error Cálculo", message); self.status_var.set(f"Error: {message}"); self._clear_plot(); return

        self.status_var.set("Calculando unidades..."); self.update_idletasks()
        success, message_units = self.kml_processor.calculate_units(base_width, base_length, corridor_width)
        if not success: messagebox.showerror("Error Cálculo", message_units); self.status_var.set(f"Error: {message_units}"); self._clear_plot(); return

        self.status_var.set("Generando visualización..."); self.update_idletasks()
        self._visualize_results()
        self.status_var.set(f"Listo. {message_units}")

    def _clear_plot(self):
         if self.canvas: self.canvas.get_tk_widget().destroy(); self.canvas = None
         if self.toolbar and self.toolbar.winfo_exists(): self.toolbar.destroy(); self.toolbar = None
         for widget in self.plot_frame.winfo_children(): widget.destroy()

    def _visualize_results(self):
        self._clear_plot()
        if not self.kml_processor.bounding_box: return
        fig, ax = plt.subplots(figsize=(8, 6)); ax.set_aspect('equal', adjustable='box')
        bb = self.kml_processor.bounding_box

        ax.add_patch(Rectangle((bb['min_x'], bb['min_y']), bb['width'], bb['height'],
                               edgecolor='black', facecolor='#EEEEEE', alpha=0.6, lw=1, label='Bounding Box'))

        if self.kml_processor.inner_area:
            ia = self.kml_processor.inner_area; offset = self.kml_processor.offset_value
            ax.add_patch(Rectangle((ia['min_x'], ia['min_y']), ia['width'], ia['height'],
                                   edgecolor='blue', facecolor='none', ls='--', lw=1.5, label=f'Área Interna (Off:{offset})'))
            if self.kml_processor.central_area:
                ca = self.kml_processor.central_area
                ax.add_patch(Rectangle((ca['min_x'], ca['min_y']), ca['width'], ca['height'],
                                       edgecolor='purple', facecolor='lavender', alpha=0.7, label='Área Central'))
            
            stair_plotted = False
            for unit in self.kml_processor.stair_units:
                label = 'U. Escalera' if not stair_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#8B0000', facecolor='#FFA07A', alpha=0.9, label=label))
                stair_plotted = True

            outer_base_plotted = False
            for unit in self.kml_processor.outer_base_units:
                label = 'U. Base Exterior' if not outer_base_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#006400', facecolor='#90EE90', alpha=0.8, label=label))
                outer_base_plotted = True

            corridor_plotted = False
            for unit in self.kml_processor.corridor_units:
                label = 'U. Pasillo' if not corridor_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#FF8C00', facecolor='#FFD700', alpha=0.85, label=label))
                corridor_plotted = True

            inner_base_plotted = False
            for unit in self.kml_processor.inner_base_units:
                label = 'U. Base Interior' if not inner_base_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#006400', facecolor='#98FB98', alpha=0.75, label=label))
                inner_base_plotted = True

        padding_x = bb['width'] * 0.07; padding_y = bb['height'] * 0.07
        padding_x = max(padding_x, 1); padding_y = max(padding_y, 1)
        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x); ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)
        ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
        title = "Distribución de Unidades"
        if self.kml_processor.base_width_value > 0: title += f" (B:{self.kml_processor.base_width_value}x{self.kml_processor.base_length_value}, P:{self.kml_processor.corridor_width_value})"
        ax.set_title(title); ax.grid(True, linestyle=':', alpha=0.5)
        
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), fontsize='small', loc='best')

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame); self.canvas.draw()
        canvas_widget = self.canvas.get_tk_widget(); canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame); self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

# --- Main execution block ---
if __name__ == "__main__":
    app = Application()
    app.mainloop()