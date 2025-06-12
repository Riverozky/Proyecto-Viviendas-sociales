import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle, Patch
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
                    if doc is None: f.seek(0); doc = parser.parse(f).getroot().find('.//{http://earth.google.com/kml/2.2}Document')
                    if doc is None: f.seek(0); doc = parser.parse(f).getroot()
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
                x_coords, y_coords = [c[0] for c in coords], [c[1] for c in coords]
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

    def calculate_units(self, base_width, base_length, corridor_width, stair_size, layout_type="cuadrada"):
        if not self.inner_area: return False, "Calcule área interna"
        if not all(d > 0 for d in [base_width, base_length, corridor_width]) or stair_size < 0:
            return False, "Dimensiones deben ser > 0 (stair_size >= 0)."
        self.base_width_value, self.base_length_value, self.corridor_width_value = base_width, base_length, corridor_width
        self.outer_base_units, self.inner_base_units, self.corridor_units, self.stair_units, self.central_area = [], [], [], [], None
        nominal_stair_size = stair_size
        if nominal_stair_size > self.epsilon:
            max_dim_stair = 0
            if layout_type == "cuadrada": max_dim_stair = min(self.inner_area['width'] / 2, self.inner_area['height'] / 2)
            elif layout_type == "forma_l": max_dim_stair = min(self.inner_area['width'], self.inner_area['height'])
            elif layout_type == "forma_rectangular": max_dim_stair = min(self.inner_area['width'] / 2, self.inner_area['height'])
            if nominal_stair_size > max_dim_stair: nominal_stair_size = max_dim_stair
        if nominal_stair_size <= self.epsilon: self.stair_units, nominal_stair_size = [], 0
        if layout_type == "cuadrada": self._calculate_units_cuadrada(base_width, base_length, corridor_width, nominal_stair_size)
        elif layout_type == "forma_l": self._calculate_units_forma_l(base_width, base_length, corridor_width, nominal_stair_size)
        elif layout_type == "forma_rectangular": self._calculate_units_forma_rectangular(base_width, base_length, corridor_width, nominal_stair_size)
        else: return False, "Tipo de disposición no reconocido."
        return True, "Cálculo de unidades completado."

    def _calculate_units_cuadrada(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area
        if nominal_stair_size > self.epsilon:
            self.stair_units.extend([
                {'x': ia['min_x'], 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BL'},
                {'x': ia['max_x'] - nominal_stair_size, 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BR'},
                {'x': ia['min_x'], 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TL'},
                {'x': ia['max_x'] - nominal_stair_size, 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TR'}])
        available_width, available_height = ia['width'] - (2 * nominal_stair_size), ia['height'] - (2 * nominal_stair_size)
        unit_w_horiz, unit_h_horiz = base_length, base_width
        num_fitted_horizontally = math.floor(available_width / unit_w_horiz) if available_width >= unit_w_horiz else 0
        unit_w_vert, unit_h_vert = base_width, base_length
        num_fitted_vertically = math.floor(available_height / unit_h_vert) if available_height >= unit_h_vert else 0
        start_x = ia['min_x'] + nominal_stair_size + (available_width - (num_fitted_horizontally * unit_w_horiz)) / 2
        start_y = ia['min_y'] + nominal_stair_size + (available_height - (num_fitted_vertically * unit_h_vert)) / 2
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

    # MODIFICADO: Lógica de creación de escaleras simplificada para mayor robustez.
    def _calculate_units_forma_l(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area; self.central_area = None
        su_tl, su_bl, su_br = None, None, None # Variables para controlar los límites de los brazos
        
        if nominal_stair_size > self.epsilon:
            # Colocar escalera Superior-Izquierda (TL) si cabe
            if ia['height'] >= nominal_stair_size:
                su_tl = {'x': ia['min_x'], 'y': ia['max_y'] - nominal_stair_size, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_TL'}
                self.stair_units.append(su_tl)

            # Colocar escalera Inferior-Izquierda (BL) si cabe
            if ia['height'] >= nominal_stair_size and ia['width'] >= nominal_stair_size:
                # Comprobar que no se solape con la TL si el área es muy baja
                if not (su_tl and su_tl['y'] < ia['min_y'] + nominal_stair_size):
                    su_bl = {'x': ia['min_x'], 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BL'}
                    self.stair_units.append(su_bl)

            # Colocar escalera Inferior-Derecha (BR) si cabe
            if ia['width'] >= nominal_stair_size:
                # Comprobar que no se solape con la BL si el área es muy estrecha
                if not (su_bl and ia['max_x'] - nominal_stair_size < su_bl['x'] + su_bl['width']):
                    su_br = {'x': ia['max_x'] - nominal_stair_size, 'y': ia['min_y'], 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_BR'}
                    self.stair_units.append(su_br)

        unit_w_vert, unit_h_vert = base_width, base_length
        y_start_vert, y_end_vert = ia['min_y'] + (nominal_stair_size if su_bl else 0), ia['max_y'] - (nominal_stair_size if su_tl else 0)
        available_h_vert = y_end_vert - y_start_vert
        if available_h_vert >= unit_h_vert:
            for i in range(math.floor(available_h_vert / unit_h_vert)):
                current_y = y_start_vert + (i * unit_h_vert)
                self.outer_base_units.append({'x': ia['min_x'], 'y': current_y, 'width': unit_w_vert, 'height': unit_h_vert})
                if ia['min_x'] + unit_w_vert + corridor_width <= (su_br['x'] if su_br else ia['max_x']):
                    self.corridor_units.append({'x': ia['min_x'] + unit_w_vert, 'y': current_y, 'width': corridor_width, 'height': unit_h_vert})
        
        unit_w_horiz, unit_h_horiz = base_length, base_width
        x_start_horiz, x_end_horiz = ia['min_x'] + (nominal_stair_size if su_bl else 0), ia['max_x'] - (nominal_stair_size if su_br else 0)
        available_w_horiz = x_end_horiz - x_start_horiz
        if available_w_horiz >= unit_w_horiz:
            for i in range(math.floor(available_w_horiz / unit_w_horiz)):
                current_x = x_start_horiz + (i * unit_w_horiz)
                self.outer_base_units.append({'x': current_x, 'y': ia['min_y'], 'width': unit_w_horiz, 'height': unit_h_horiz})
                if ia['min_y'] + unit_h_horiz + corridor_width <= (su_tl['y'] if su_tl else ia['max_y']):
                    self.corridor_units.append({'x': current_x, 'y': ia['min_y'] + unit_h_horiz, 'width': unit_w_horiz, 'height': corridor_width})

    def _calculate_units_forma_rectangular(self, base_width, base_length, corridor_width, nominal_stair_size):
        ia = self.inner_area
        self.central_area, self.inner_base_units = None, []
        if nominal_stair_size > self.epsilon:
            stair_y_start = ia['min_y'] + (ia['height'] - nominal_stair_size) / 2
            if stair_y_start >= ia['min_y'] and (stair_y_start + nominal_stair_size) <= ia['max_y']:
                self.stair_units.extend([
                    {'x': ia['min_x'], 'y': stair_y_start, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_L'},
                    {'x': ia['max_x'] - nominal_stair_size, 'y': stair_y_start, 'width': nominal_stair_size, 'height': nominal_stair_size, 'id': 'SU_R'}])
        x_start, x_end = ia['min_x'] + (nominal_stair_size if self.stair_units else 0), ia['max_x'] - (nominal_stair_size if self.stair_units else 0)
        available_w = x_end - x_start
        unit_w, unit_h_base, unit_h_corridor = base_length, base_width, corridor_width
        num_fitted = math.floor(available_w / unit_w) if available_w >= unit_w else 0
        if num_fitted > 0:
            y_base_start = ia['min_y'] + (ia['height'] - (unit_h_base + unit_h_corridor)) / 2
            y_corridor_start = y_base_start + unit_h_base
            if y_base_start >= ia['min_y'] and (y_corridor_start + unit_h_corridor) <= ia['max_y']:
                for i in range(num_fitted):
                    current_x = x_start + (i * unit_w)
                    self.outer_base_units.append({'x': current_x, 'y': y_base_start, 'width': unit_w, 'height': unit_h_base})
                    self.corridor_units.append({'x': current_x, 'y': y_corridor_start, 'width': unit_w, 'height': unit_h_corridor})

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno v3.4")
        self.geometry("1200x700")
        self.kml_processor = KMLProcessor()
        self.current_figure, self.canvas, self.toolbar = None, None, None
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
        
        tk.Label(param_frame, text="An.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_width_entry = tk.Entry(param_frame, width=6); self.base_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_width_entry.insert(0, "6")
        tk.Label(param_frame, text="La.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_length_entry = tk.Entry(param_frame, width=6); self.base_length_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_length_entry.insert(0, "10")
        tk.Label(param_frame, text="An.Pasillo:").pack(side=tk.LEFT, padx=(0,1));
        self.corridor_width_entry = tk.Entry(param_frame, width=6); self.corridor_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.corridor_width_entry.insert(0, "4")
        tk.Label(param_frame, text="Tam. Escalera:").pack(side=tk.LEFT, padx=(10,1));
        self.stair_size_entry = tk.Entry(param_frame, width=6); self.stair_size_entry.pack(side=tk.LEFT, padx=(0, 1)); self.stair_size_entry.insert(0, "10")
        self.auto_stair_button = tk.Button(param_frame, text="Auto", command=self.auto_calculate_stair_size); self.auto_stair_button.pack(side=tk.LEFT, padx=(0, 15));
        tk.Label(param_frame, text="Ancho Terreno:").pack(side=tk.LEFT, padx=(0,1));
        self.terrain_width_entry = tk.Entry(param_frame, width=8, state='disabled'); self.terrain_width_entry.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(param_frame, text="Alto Terreno:").pack(side=tk.LEFT, padx=(0,1));
        self.terrain_height_entry = tk.Entry(param_frame, width=8, state='disabled'); self.terrain_height_entry.pack(side=tk.LEFT, padx=(0, 15))
        tk.Label(param_frame, text="D.Corona:").pack(side=tk.LEFT, padx=(0,1));
        self.offset_entry = tk.Entry(param_frame, width=6); self.offset_entry.pack(side=tk.LEFT, padx=(0, 5)); self.offset_entry.insert(0, "5")
        tk.Label(param_frame, text="Disposición:").pack(side=tk.LEFT, padx=(10,1))
        self.layout_var = tk.StringVar(self); self.layout_options = ["Forma Cuadrada", "Forma L", "Forma Rectangular"]; self.layout_var.set(self.layout_options[0])
        self.layout_menu = tk.OptionMenu(param_frame, self.layout_var, *self.layout_options); self.layout_menu.pack(side=tk.LEFT, padx=(0,10))
        self.calculate_button = tk.Button(self.control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED); self.calculate_button.pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(); self.status_var.set("Listo. Cargue KML.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5); self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def auto_calculate_stair_size(self):
        try:
            auto_size = float(self.base_width_entry.get()) + float(self.corridor_width_entry.get())
            self.stair_size_entry.delete(0, tk.END); self.stair_size_entry.insert(0, f"{auto_size:.2f}")
        except (ValueError, tk.TclError): messagebox.showerror("Entrada Inválida", "Asegúrese de que 'An.Base' y 'An.Pasillo' sean números válidos.")

    def load_kml(self):
        self._clear_plot()
        file_path = filedialog.askopenfilename(title="Seleccionar KML", filetypes=[("KML", "*.kml"), ("Todos", "*.*")])
        if file_path:
            self.status_var.set(f"Cargando {file_path}..."); self.update_idletasks()
            success, message = self.kml_processor.load_kml(file_path)
            if success:
                bb = self.kml_processor.bounding_box; fname = file_path.split('/')[-1]
                self.status_var.set(f"KML '{fname}' cargado. W={bb['width']:.2f}, H={bb['height']:.2f}. Calcule.")
                self.terrain_width_entry.config(state='normal'); self.terrain_height_entry.config(state='normal')
                self.terrain_width_entry.delete(0, tk.END); self.terrain_width_entry.insert(0, f"{bb['width']:.2f}")
                self.terrain_height_entry.delete(0, tk.END); self.terrain_height_entry.insert(0, f"{bb['height']:.2f}")
                self.calculate_button['state'] = tk.NORMAL
                self.auto_calculate_stair_size()
            else:
                messagebox.showerror("Error KML", message); self.status_var.set("Error KML.")
                self.calculate_button['state'] = tk.DISABLED

    def calculate_and_visualize(self):
        if not self.kml_processor.original_bounding_box: messagebox.showwarning("Inválido", "Cargue KML primero."); return
        try:
            params = {name: float(entry.get()) for name, entry in {
                "offset": self.offset_entry, "base_width": self.base_width_entry, "base_length": self.base_length_entry,
                "corridor_width": self.corridor_width_entry, "stair_size": self.stair_size_entry,
                "terrain_w": self.terrain_width_entry, "terrain_h": self.terrain_height_entry}.items()}
            if any(v < 0 for v in params.values()): messagebox.showerror("Entrada Inválida", "Los valores numéricos no pueden ser negativos."); return
        except (ValueError, tk.TclError): messagebox.showerror("Entrada Inválida", "Valores numéricos inválidos."); return
        
        temp_bb = self.kml_processor.original_bounding_box.copy()
        temp_bb.update({'width': params['terrain_w'], 'height': params['terrain_h'], 'max_x': temp_bb['min_x'] + params['terrain_w'], 'max_y': temp_bb['min_y'] + params['terrain_h']})
        self.kml_processor.bounding_box = temp_bb
        
        layout_map = {"Forma L": "forma_l", "Forma Rectangular": "forma_rectangular"}
        layout_type_arg = layout_map.get(self.layout_var.get(), "cuadrada")
        
        self.status_var.set("Calculando..."); self.update_idletasks()
        success, msg = self.kml_processor.calculate_inner_area(params['offset'])
        if not success: messagebox.showerror("Error", msg); self.status_var.set("Error de cálculo."); self._clear_plot(); return
        
        success, msg = self.kml_processor.calculate_units(params['base_width'], params['base_length'], params['corridor_width'], params['stair_size'], layout_type_arg)
        if not success: messagebox.showerror("Error", msg); self.status_var.set("Error de cálculo."); self._clear_plot(); return
        
        self.status_var.set("Generando visualización..."); self.update_idletasks()
        self._visualize_results()
        self.status_var.set(msg)

    def _clear_plot(self):
        if self.canvas: self.canvas.get_tk_widget().destroy()
        if self.toolbar: self.toolbar.destroy()
        self.canvas, self.toolbar = None, None
        for widget in self.plot_frame.winfo_children(): widget.destroy()

    def _visualize_results(self):
        self._clear_plot()
        fig, ax = plt.subplots(figsize=(8, 6)); fig.subplots_adjust(right=0.72)
        bb = self.kml_processor.bounding_box
        ax.add_patch(Rectangle((bb['min_x'], bb['min_y']), bb['width'], bb['height'], ec='black', fc='#EEEEEE', alpha=0.6))
        if ia := self.kml_processor.inner_area:
            ax.add_patch(Rectangle((ia['min_x'], ia['min_y']), ia['width'], ia['height'], ec='blue', fc='none', ls='--', lw=1.5))
            if ca := self.kml_processor.central_area: ax.add_patch(Rectangle((ca['min_x'], ca['min_y']), ca['width'], ca['height'], ec='purple', fc='lavender', alpha=0.7))
            for unit in self.kml_processor.stair_units: ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], ec='#8B0000', fc='#FFA07A', alpha=0.9))
            for unit in self.kml_processor.outer_base_units: ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], ec='#006400', fc='#90EE90', alpha=0.8))
            for unit in self.kml_processor.corridor_units: ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'], ec='#FF8C00', fc='#FFD700', alpha=0.85))
        padding_x, padding_y = max(bb['width'] * 0.1, 1), max(bb['height'] * 0.1, 1)
        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x); ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)
        ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
        title = f"Distribución de Unidades ({self.layout_var.get()})\n(B:{self.base_width_entry.get()}x{self.base_length_entry.get()}, P:{self.corridor_width_entry.get()}, E:{self.stair_size_entry.get()})"
        ax.set_title(title); ax.grid(True, linestyle=':', alpha=0.5)

        legend_elements = [ Patch(fc='#EEEEEE', ec='black', label=f'Terreno'),
                            Patch(fc='none', ec='blue', ls='--', label=f"Área Interna (Off:{self.offset_entry.get()})")]
        total_base = len(self.kml_processor.outer_base_units) + len(self.kml_processor.inner_base_units)
        if self.kml_processor.stair_units: legend_elements.append(Patch(fc='#FFA07A', ec='#8B0000', label=f'U. Escalera: {len(self.kml_processor.stair_units)}'))
        if total_base > 0: legend_elements.append(Patch(fc='#90EE90', ec='#006400', label=f'U. Base: {total_base}'))
        if self.kml_processor.corridor_units: legend_elements.append(Patch(fc='#FFD700', ec='#FF8C00', label=f'U. Pasillo: {len(self.kml_processor.corridor_units)}'))
        
        if total_base > 0:
            units_per_building = total_base * 4
            legend_elements.extend([
                Patch(fc='none', ec='none', label='-'*28),
                Patch(fc='none', ec='none', label=f'Unidades x Edificio: {units_per_building}')
            ])
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., title="Resumen de Unidades")

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame); self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame); self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

if __name__ == "__main__":
    app = Application()
    app.mainloop()