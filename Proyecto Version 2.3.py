import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from pykml import parser
import math

# --- Clase KMLProcessor ---
class KMLProcessor:
    def __init__(self):
        self.bounding_box = None
        self.original_bounding_box = None
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
        self.epsilon = 1e-9

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
                self.original_bounding_box = self.bounding_box.copy()
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

    # MODIFICADO: Acepta 'stair_size' como parámetro en lugar de calcularlo internamente
    def calculate_units(self, base_width, base_length, corridor_width, stair_size, layout_type="cuadrada"):
        if not self.inner_area: return False, "Calcule área interna"
        if base_width <= 0 or base_length <= 0 or corridor_width <= 0 or stair_size < 0:
            return False, "Dimensiones deben ser > 0 (stair_size >= 0)."

        self.base_width_value = base_width
        self.base_length_value = base_length
        self.corridor_width_value = corridor_width
        
        self.outer_base_units, self.inner_base_units, self.corridor_units, self.stair_units, self.central_area = [], [], [], [], None
        
        nominal_stair_size = stair_size

        if nominal_stair_size > self.epsilon:
            max_dim_stair = 0
            if layout_type == "cuadrada":
                 max_dim_stair = min(self.inner_area['width'] / 2, self.inner_area['height'] / 2)
            elif layout_type == "forma_l":
                 max_dim_stair = min(self.inner_area['width'], self.inner_area['height'])
            elif layout_type == "forma_rectangular":
                 max_dim_stair = min(self.inner_area['width'] / 2, self.inner_area['height'])
            
            if nominal_stair_size > max_dim_stair and max_dim_stair > self.epsilon:
                nominal_stair_size = max_dim_stair
            elif nominal_stair_size > max_dim_stair and max_dim_stair <= self.epsilon :
                 nominal_stair_size = 0

        if nominal_stair_size <= self.epsilon:
            self.stair_units = []
            nominal_stair_size = 0

        if layout_type == "cuadrada":
            self._calculate_units_cuadrada(base_width, base_length, corridor_width, nominal_stair_size)
        elif layout_type == "forma_l":
            self._calculate_units_forma_l(base_width, base_length, corridor_width, nominal_stair_size)
        elif layout_type == "forma_rectangular":
            self._calculate_units_forma_rectangular(base_width, base_length, corridor_width, nominal_stair_size)
        else:
            return False, "Tipo de disposición no reconocido."

        total_base = len(self.outer_base_units) + len(self.inner_base_units)
        return True, (f"{total_base} U.Base ({len(self.outer_base_units)} Ext, {len(self.inner_base_units)} Int), "
                      f"{len(self.corridor_units)} U.Pasillo, {len(self.stair_units)} U.Escalera calculadas para '{layout_type}'")

    def _calculate_units_cuadrada(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area
        
        if nominal_stair_size > self.epsilon:
            self.stair_units.append({'x': ia['min_x'], 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BL'})
            self.stair_units.append({'x': ia['max_x'] - nominal_stair_size, 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BR'})
            self.stair_units.append({'x': ia['min_x'], 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TL'})
            self.stair_units.append({'x': ia['max_x'] - nominal_stair_size, 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TR'})

        available_width = ia['width'] - (2 * nominal_stair_size)
        available_height = ia['height'] - (2 * nominal_stair_size)

        unit_w_horiz, unit_h_horiz = base_length, base_width
        num_fitted_horizontally = 0
        if available_width >= unit_w_horiz:
            num_fitted_horizontally = math.floor(available_width / unit_w_horiz)
        
        unit_w_vert, unit_h_vert = base_width, base_length
        num_fitted_vertically = 0
        if available_height >= unit_h_vert:
            num_fitted_vertically = math.floor(available_height / unit_h_vert)

        gap_x = available_width - (num_fitted_horizontally * unit_w_horiz)
        start_x = ia['min_x'] + nominal_stair_size + (gap_x / 2)
        
        gap_y = available_height - (num_fitted_vertically * unit_h_vert)
        start_y = ia['min_y'] + nominal_stair_size + (gap_y / 2)

        for i in range(num_fitted_horizontally):
            current_x = start_x + (i * unit_w_horiz)
            self.outer_base_units.append({'x': current_x, 'y': ia['min_y'], 'width': unit_w_horiz, 'height': unit_h_horiz})
            self.corridor_units.append({'x': current_x, 'y': ia['min_y'] + unit_h_horiz, 'width': unit_w_horiz, 'height': corridor_width})
            self.outer_base_units.append({'x': current_x, 'y': ia['max_y'] - unit_h_horiz, 'width': unit_w_horiz, 'height': unit_h_horiz})
            self.corridor_units.append({'x': current_x, 'y': ia['max_y'] - unit_h_horiz - corridor_width, 'width': unit_w_horiz, 'height': corridor_width})

        for i in range(num_fitted_vertically):
            current_y = start_y + (i * unit_h_vert)
            self.outer_base_units.append({'x': ia['min_x'], 'y': current_y, 'width': unit_w_vert, 'height': unit_h_vert})
            self.corridor_units.append({'x': ia['min_x'] + unit_w_vert, 'y': current_y, 'width': corridor_width, 'height': unit_h_vert})
            self.outer_base_units.append({'x': ia['max_x'] - unit_w_vert, 'y': current_y, 'width': unit_w_vert, 'height': unit_h_vert})
            self.corridor_units.append({'x': ia['max_x'] - unit_w_vert - corridor_width, 'y': current_y, 'width': corridor_width, 'height': unit_h_vert})
            
    def _calculate_units_forma_l(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area; self.central_area = None
        su_tl, su_bl, su_br = None, None, None
        if nominal_stair_size > self.epsilon:
            if ia['height'] >= nominal_stair_size:
                 su_tl = {'x': ia['min_x'], 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TL'}; self.stair_units.append(su_tl)
            if ia['height'] >= nominal_stair_size and ia['width'] >= nominal_stair_size :
                 su_bl = {'x': ia['min_x'], 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BL'}
                 if not any(s['id'] == 'SU_BL' for s in self.stair_units if s['x'] == su_bl['x'] and s['y'] == su_bl['y']):
                    is_overlapping_tl = su_tl and (su_bl['y'] < su_tl['y'] + su_tl['height'] - self.epsilon and su_bl['y'] + su_bl['height'] > su_tl['y'] + self.epsilon)
                    if not is_overlapping_tl: self.stair_units.append(su_bl)
                    else: su_bl = None
            if ia['width'] >= nominal_stair_size:
                su_br = {'x': ia['max_x'] - nominal_stair_size, 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BR'}
                is_overlapping_bl = su_bl and (su_br['x'] < su_bl['x'] + su_bl['width'] - self.epsilon and su_br['x'] + su_br['width'] > su_bl['x'] + self.epsilon)
                if not is_overlapping_bl: self.stair_units.append(su_br)
                else: su_br = None
        unit_w_vert_arm, unit_h_vert_arm = base_width, base_length
        y_start_vert = ia['min_y'] + (nominal_stair_size if su_bl else 0)
        y_end_vert = ia['max_y'] - (nominal_stair_size if su_tl else 0)
        available_h_vert = y_end_vert - y_start_vert
        if available_h_vert >= unit_h_vert_arm - self.epsilon:
            num_fitted_vert = math.floor(available_h_vert / unit_h_vert_arm + self.epsilon)
            current_y = y_start_vert
            for _ in range(num_fitted_vert):
                if current_y + unit_h_vert_arm > y_end_vert + self.epsilon: break
                self.outer_base_units.append({'x': ia['min_x'], 'y': current_y, 'width': unit_w_vert_arm, 'height': unit_h_vert_arm})
                x_corridor_vert = ia['min_x'] + unit_w_vert_arm
                limit_x_for_inner_vert = (su_br['x'] if su_br else ia['max_x'])
                if x_corridor_vert + corridor_width <= limit_x_for_inner_vert + self.epsilon :
                    self.corridor_units.append({'x': x_corridor_vert, 'y': current_y, 'width': corridor_width, 'height': unit_h_vert_arm})
                current_y += unit_h_vert_arm
        unit_w_horiz_arm, unit_h_horiz_arm = base_length, base_width
        x_start_horiz = ia['min_x'] + (nominal_stair_size if su_bl else 0)
        x_end_horiz = ia['max_x'] - (nominal_stair_size if su_br else 0)
        available_w_horiz = x_end_horiz - x_start_horiz
        if available_w_horiz >= unit_w_horiz_arm - self.epsilon:
            num_fitted_horiz = math.floor(available_w_horiz / unit_w_horiz_arm + self.epsilon)
            current_x = x_start_horiz
            for _ in range(num_fitted_horiz):
                if current_x + unit_w_horiz_arm > x_end_horiz + self.epsilon: break
                self.outer_base_units.append({'x': current_x, 'y': ia['min_y'], 'width': unit_w_horiz_arm, 'height': unit_h_horiz_arm})
                y_corridor_horiz = ia['min_y'] + unit_h_horiz_arm
                limit_y_for_inner_horiz = (su_tl['y'] if su_tl else ia['max_y'])
                if y_corridor_horiz + corridor_width <= limit_y_for_inner_horiz + self.epsilon :
                    self.corridor_units.append({'x': current_x, 'y': y_corridor_horiz, 'width': unit_w_horiz_arm, 'height': corridor_width})
                current_x += unit_w_horiz_arm
                
    def _calculate_units_forma_rectangular(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area
        self.central_area, self.inner_base_units = None, []
        if nominal_stair_size > self.epsilon:
            stair_y_start = ia['min_y'] + (ia['height'] / 2) - (nominal_stair_size / 2)
            if stair_y_start >= ia['min_y'] and (stair_y_start + nominal_stair_size) <= ia['max_y']:
                self.stair_units.append({'x': ia['min_x'], 'y': stair_y_start, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_L'})
                self.stair_units.append({'x': ia['max_x'] - nominal_stair_size, 'y': stair_y_start, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_R'})
        x_start = ia['min_x'] + (nominal_stair_size if self.stair_units else 0)
        x_end = ia['max_x'] - (nominal_stair_size if self.stair_units else 0)
        available_w = x_end - x_start
        unit_w, unit_h_base, unit_h_corridor = base_length, base_width, corridor_width
        num_fitted = 0
        if available_w >= unit_w - self.epsilon:
            num_fitted = math.floor(available_w / unit_w + self.epsilon)
        if num_fitted > 0:
            vertical_centerline = ia['min_y'] + ia['height'] / 2
            block_height = unit_h_base + unit_h_corridor
            y_base_start = vertical_centerline - (block_height / 2)
            y_corridor_start = y_base_start + unit_h_base
            if y_base_start >= ia['min_y'] and (y_corridor_start + unit_h_corridor) <= ia['max_y']:
                current_x = x_start
                for _ in range(num_fitted):
                    self.outer_base_units.append({'x': current_x, 'y': y_base_start, 'width': unit_w, 'height': unit_h_base})
                    self.corridor_units.append({'x': current_x, 'y': y_corridor_start, 'width': unit_w, 'height': unit_h_corridor})
                    current_x += unit_w

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno v3.1")
        self.geometry("1200x700") # Aumentado el ancho para los nuevos campos
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
        
        # --- Parámetros de Unidades ---
        tk.Label(param_frame, text="An.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_width_entry = tk.Entry(param_frame, width=6);
        self.base_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_width_entry.insert(0, "6")
        tk.Label(param_frame, text="La.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_length_entry = tk.Entry(param_frame, width=6);
        self.base_length_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_length_entry.insert(0, "10")
        tk.Label(param_frame, text="An.Pasillo:").pack(side=tk.LEFT, padx=(0,1));
        self.corridor_width_entry = tk.Entry(param_frame, width=6);
        self.corridor_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.corridor_width_entry.insert(0, "4")
        
        # NUEVO: Campo de entrada para el tamaño de la escalera
        tk.Label(param_frame, text="Tam. Escalera:").pack(side=tk.LEFT, padx=(10,1));
        self.stair_size_entry = tk.Entry(param_frame, width=6);
        self.stair_size_entry.pack(side=tk.LEFT, padx=(0, 1)); self.stair_size_entry.insert(0, "10")
        self.auto_stair_button = tk.Button(param_frame, text="Auto", command=self.auto_calculate_stair_size);
        self.auto_stair_button.pack(side=tk.LEFT, padx=(0, 15));
        
        # --- Parámetros del Terreno ---
        tk.Label(param_frame, text="Ancho Terreno:").pack(side=tk.LEFT, padx=(0,1));
        self.terrain_width_entry = tk.Entry(param_frame, width=8, state='disabled');
        self.terrain_width_entry.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(param_frame, text="Alto Terreno:").pack(side=tk.LEFT, padx=(0,1));
        self.terrain_height_entry = tk.Entry(param_frame, width=8, state='disabled');
        self.terrain_height_entry.pack(side=tk.LEFT, padx=(0, 15))

        # --- Parámetros de Corona y Disposición ---
        tk.Label(param_frame, text="D.Corona:").pack(side=tk.LEFT, padx=(0,1));
        self.offset_entry = tk.Entry(param_frame, width=6);
        self.offset_entry.pack(side=tk.LEFT, padx=(0, 5)); self.offset_entry.insert(0, "5")
        tk.Label(param_frame, text="Disposición:").pack(side=tk.LEFT, padx=(10,1))
        self.layout_var = tk.StringVar(self)
        self.layout_options = ["Forma Cuadrada", "Forma L", "Forma Rectangular"]
        self.layout_var.set(self.layout_options[0])
        self.layout_menu = tk.OptionMenu(param_frame, self.layout_var, *self.layout_options)
        self.layout_menu.pack(side=tk.LEFT, padx=(0,10))

        self.calculate_button = tk.Button(self.control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED)
        self.calculate_button.pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(); self.status_var.set("Listo. Cargue KML.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # NUEVO: Método para el botón "Auto"
    def auto_calculate_stair_size(self):
        try:
            base_width = float(self.base_width_entry.get())
            corridor_width = float(self.corridor_width_entry.get())
            auto_size = base_width + corridor_width
            self.stair_size_entry.delete(0, tk.END)
            self.stair_size_entry.insert(0, f"{auto_size:.2f}")
        except ValueError:
            messagebox.showerror("Entrada Inválida", "Asegúrese de que 'An.Base' y 'An.Pasillo' sean números válidos.")

    def load_kml(self):
        self._clear_plot()
        file_path = filedialog.askopenfilename(title="Seleccionar KML", filetypes=[("KML", "*.kml"), ("Todos", "*.*")])
        if file_path:
            self.status_var.set(f"Cargando {file_path}..."); self.update_idletasks()
            success, message = self.kml_processor.load_kml(file_path)
            if success:
                bb = self.kml_processor.bounding_box
                fname = file_path.split('/')[-1]
                self.status_var.set(f"KML '{fname}' cargado. W={bb['width']:.2f}, H={bb['height']:.2f}. Calcule.")
                
                self.terrain_width_entry.config(state='normal')
                self.terrain_height_entry.config(state='normal')
                self.terrain_width_entry.delete(0, tk.END)
                self.terrain_width_entry.insert(0, f"{bb['width']:.2f}")
                self.terrain_height_entry.delete(0, tk.END)
                self.terrain_height_entry.insert(0, f"{bb['height']:.2f}")
                
                self.calculate_button['state'] = tk.NORMAL
                self.auto_calculate_stair_size() # Calcular tamaño de escalera por defecto al cargar
            else:
                messagebox.showerror("Error KML", message); self.status_var.set("Error KML.")
                self.calculate_button['state'] = tk.DISABLED

    def calculate_and_visualize(self):
        if not self.kml_processor.original_bounding_box:
            messagebox.showwarning("Inválido", "Cargue KML primero."); return
        try:
            offset = float(self.offset_entry.get())
            base_width = float(self.base_width_entry.get())
            base_length = float(self.base_length_entry.get())
            corridor_width = float(self.corridor_width_entry.get())
            stair_size = float(self.stair_size_entry.get()) # Leer tamaño de escalera
            layout_choice_str = self.layout_var.get()
            terrain_w = float(self.terrain_width_entry.get())
            terrain_h = float(self.terrain_height_entry.get())

            if any(v < 0 for v in [offset, base_width, base_length, corridor_width, stair_size, terrain_w, terrain_h]):
                messagebox.showerror("Entrada Inválida", "Los valores numéricos no pueden ser negativos.")
                return
        except ValueError:
            messagebox.showerror("Entrada Inválida", "Valores numéricos inválidos."); return

        temp_bb = self.kml_processor.original_bounding_box.copy()
        temp_bb['width'] = terrain_w
        temp_bb['height'] = terrain_h
        temp_bb['max_x'] = temp_bb['min_x'] + terrain_w
        temp_bb['max_y'] = temp_bb['min_y'] + terrain_h
        self.kml_processor.bounding_box = temp_bb

        layout_type_arg = "cuadrada"
        if layout_choice_str == "Forma L":
            layout_type_arg = "forma_l"
        elif layout_choice_str == "Forma Rectangular":
            layout_type_arg = "forma_rectangular"
        
        self.status_var.set("Calculando área interna..."); self.update_idletasks()
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success: messagebox.showerror("Error Cálculo", message); self.status_var.set(f"Error: {message}"); self._clear_plot(); return
        
        self.status_var.set(f"Calculando unidades ({layout_choice_str})..."); self.update_idletasks()
        # MODIFICADO: Pasar stair_size a la función de cálculo
        success, message_units = self.kml_processor.calculate_units(base_width, base_length, corridor_width, stair_size, layout_type_arg)
        if not success: messagebox.showerror("Error Cálculo", message_units); self.status_var.set(f"Error: {message_units}"); self._clear_plot(); return
        
        self.status_var.set("Generando visualización..."); self.update_idletasks()
        self._visualize_results()
        self.status_var.set(f"Listo. {message_units}")

    def _clear_plot(self):
        if self.canvas: self.canvas.get_tk_widget().destroy(); self.canvas = None
        if self.toolbar and self.toolbar.winfo_exists(): self.toolbar.destroy(); self.toolbar = None
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

    def _visualize_results(self):
        self._clear_plot()
        if not self.kml_processor.bounding_box: return
        fig, ax = plt.subplots(figsize=(8, 6)); ax.set_aspect('equal', adjustable='box')
        bb = self.kml_processor.bounding_box
        ax.add_patch(Rectangle((bb['min_x'], bb['min_y']), bb['width'], bb['height'], edgecolor='black', facecolor='#EEEEEE', alpha=0.6, lw=1, label='Bounding Box'))
        if self.kml_processor.inner_area:
            ia = self.kml_processor.inner_area; offset = self.kml_processor.offset_value
            ax.add_patch(Rectangle((ia['min_x'], ia['min_y']), ia['width'], ia['height'], edgecolor='blue', facecolor='none', ls='--', lw=1.5, label=f'Área Interna (Off:{offset})'))
            if self.kml_processor.central_area:
                ca = self.kml_processor.central_area
                ax.add_patch(Rectangle((ca['min_x'], ca['min_y']), ca['width'], ca['height'], edgecolor='purple', facecolor='lavender', alpha=0.7, label='Área Central'))
            stair_plotted = False
            for unit in self.kml_processor.stair_units:
                label = 'U. Escalera' if not stair_plotted else ""; ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], edgecolor='#8B0000', facecolor='#FFA07A', alpha=0.9, label=label)); stair_plotted = True
            outer_base_plotted = False
            for unit in self.kml_processor.outer_base_units:
                label = 'U. Base Exterior' if not outer_base_plotted else ""; ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], edgecolor='#006400', facecolor='#90EE90', alpha=0.8, label=label)); outer_base_plotted = True
            corridor_plotted = False
            for unit in self.kml_processor.corridor_units:
                label = 'U. Pasillo' if not corridor_plotted else ""; ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], edgecolor='#FF8C00', facecolor='#FFD700', alpha=0.85, label=label)); corridor_plotted = True
            inner_base_plotted = False
            for unit in self.kml_processor.inner_base_units:
                label = 'U. Base Interior' if not inner_base_plotted else ""; ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], edgecolor='#006400', facecolor='#98FB98', alpha=0.75, label=label)); inner_base_plotted = True
        padding_x = bb['width'] * 0.1; padding_y = bb['height'] * 0.1
        padding_x = max(padding_x, 1); padding_y = max(padding_y, 1)
        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x)
        ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)
        ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
        title = f"Distribución de Unidades ({self.layout_var.get()})"
        if self.kml_processor.base_width_value > 0: title += f" (B:{self.kml_processor.base_width_value}x{self.kml_processor.base_length_value}, P:{self.kml_processor.corridor_width_value})"
        ax.set_title(title); ax.grid(True, linestyle=':', alpha=0.5)
        handles, labels = ax.get_legend_handles_labels(); by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), fontsize='small', loc='best')
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame); self.canvas.draw()
        canvas_widget = self.canvas.get_tk_widget(); canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame); self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

if __name__ == "__main__":
    app = Application()
    app.mainloop()