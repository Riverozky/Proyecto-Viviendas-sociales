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
        self.outer_base_units = [] # Anillo exterior
        self.inner_base_units = [] # Anillo interior
        self.corridor_units = []   # Unidades de conexión
        self.stair_units = []
        self.central_area = None
        self.offset_value = 0
        self.base_width_value = 0
        self.base_length_value = 0
        self.corridor_width_value = 0 # Nuevo valor

    # --- load_kml (sin cambios) ---
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
                        else: print(f"Warn: Coords incompleto '{pair}'")
                    except ValueError: print(f"Warn: Coords inválido '{pair}'")
                if not coords or len(coords) < 3: return False, "Coords insuficientes."

                x_coords = [c[0] for c in coords]; y_coords = [c[1] for c in coords]
                self.bounding_box = {'min_x': min(x_coords), 'max_x': max(x_coords), 'min_y': min(y_coords), 'max_y': max(y_coords), 'width': max(x_coords) - min(x_coords), 'height': max(y_coords) - min(y_coords)}
                self.inner_area = None; self.outer_base_units = []; self.inner_base_units = []; self.corridor_units = []; self.stair_units = []; self.central_area = None
                return True, "KML cargado"
        except FileNotFoundError: return False, f"Error: Archivo no encontrado '{file_path}'"
        except Exception as e: return False, f"Error inesperado KML: {str(e)}"

    # --- calculate_inner_area (sin cambios) ---
    def calculate_inner_area(self, offset):
        if not self.bounding_box: return False, "Cargue KML"
        if offset < 0: return False, "Offset >= 0"
        self.offset_value = offset
        inner_width = self.bounding_box['width'] - 2 * offset; inner_height = self.bounding_box['height'] - 2 * offset
        if inner_width <= 0 or inner_height <= 0: self.inner_area = None; return False, "Offset grande, área interna inválida."
        self.inner_area = {'min_x': self.bounding_box['min_x'] + offset, 'max_x': self.bounding_box['max_x'] - offset, 'min_y': self.bounding_box['min_y'] + offset, 'max_y': self.bounding_box['max_y'] - offset, 'width': inner_width, 'height': inner_height}
        return True, "Área interna calculada"

    # --- calculate_units (MODIFICADO EXTENSAMENTE) ---
    def calculate_units(self, base_width, base_length, corridor_width):
        if not self.inner_area: return False, "Calcule área interna"
        if base_width <= 0 or base_length <= 0 or corridor_width <= 0: return False, "Dims base y pasillo deben ser > 0."

        # Guardar valores
        self.base_width_value = base_width
        self.base_length_value = base_length
        self.corridor_width_value = corridor_width

        # Calcular dimensiones base y pasillo
        long_base = max(base_width, base_length)
        short_base = min(base_width, base_length)

        # NUEVO CÁLCULO TAMAÑO UNIDAD ESCALERA
        stair_size = long_base + short_base + corridor_width
        print(f"Debug: long={long_base}, short={short_base}, corr={corridor_width}, stair_size={stair_size}")


        # Ajustar stair_size si no cabe
        required_dim = 2 * stair_size
        if required_dim > self.inner_area['width'] or required_dim > self.inner_area['height']:
             available_space = min(self.inner_area['width'], self.inner_area['height'])
             if available_space < required_dim and available_space > 0 :
                 stair_size_old = stair_size
                 stair_size = available_space / 2
                 print(f"Advertencia: Tamaño U.Escalera ({stair_size_old:.2f}) excede área interna. Reducido a {stair_size:.2f}.")
             elif available_space <=0:
                 return False, "Área interna no tiene espacio para U. Escalera."
             # Si required_dim cabe, no hacemos nada

        if stair_size <= 0 :
             return False, "Tamaño U. Escalera es <= 0. Verifique dimensiones y offset."


        # --- Unidades Escalera (con nuevo tamaño) ---
        self.stair_units = [
            {'x': self.inner_area['min_x'], 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size}, # inf-izq
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size}, # inf-der
            {'x': self.inner_area['min_x'], 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}, # sup-izq
            {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}  # sup-der
        ]

        # --- Área Central (recalcular basado en espacio restante interno a escaleras) ---
        center_avail_width = max(0, self.inner_area['width'] - 2 * stair_size)
        center_avail_height = max(0, self.inner_area['height'] - 2 * stair_size)
        # Mantener cálculo anterior relativo a este espacio disponible
        central_size = min(center_avail_width, center_avail_height) * 0.4
        if central_size > 0:
            center_x = self.inner_area['min_x'] + stair_size + center_avail_width / 2
            center_y = self.inner_area['min_y'] + stair_size + center_avail_height / 2
            self.central_area = {'min_x': center_x - central_size / 2, 'max_x': center_x + central_size / 2, 'min_y': center_y - central_size / 2, 'max_y': center_y + central_size / 2, 'width': central_size, 'height': central_size}
        else: self.central_area = None


        # --- Generar Unidades Base Exteriores, Pasillos y Unidades Base Interiores ---
        self.outer_base_units = []
        self.inner_base_units = []
        self.corridor_units = []
        epsilon = 1e-9

        # Dimensiones Vertical (Ancho=LargoBase, Alto=AnchoBase)
        unit_w_v = base_length
        unit_h_v = base_width
        # Dimensiones Horizontal (Ancho=AnchoBase, Alto=LargoBase)
        unit_w_h = base_width
        unit_h_h = base_length

        # Dimensión corta para pasillo
        corridor_length = short_base # La longitud del pasillo es la dim corta de la base
        corridor_h = corridor_width  # El "alto" (o ancho) del pasillo es el ingresado

        # Lado INFERIOR (Base Ext: Vertical, Pasillo: Vertical, Base Int: Vertical)
        x_start = self.stair_units[0]['x'] + stair_size
        x_end = self.stair_units[1]['x']
        y_outer = self.inner_area['min_y']
        current_x = x_start
        while current_x + unit_w_v <= x_end + epsilon:
            # Base Exterior
            outer_unit = {'x': current_x, 'y': y_outer, 'width': unit_w_v, 'height': unit_h_v, 'side': 'bottom'}
            self.outer_base_units.append(outer_unit)
            # Pasillo (vertical, encima de base exterior)
            y_corridor = y_outer + unit_h_v
            corridor = {'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_h, 'side': 'bottom'}
            self.corridor_units.append(corridor)
            # Base Interior (vertical, encima de pasillo)
            y_inner = y_corridor + corridor_h
            inner_unit = {'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v, 'side': 'bottom'}
            self.inner_base_units.append(inner_unit)
            current_x += unit_w_v

        # Lado SUPERIOR (Base Ext: Vertical, Pasillo: Vertical, Base Int: Vertical)
        x_start = self.stair_units[2]['x'] + stair_size
        x_end = self.stair_units[3]['x']
        y_outer = self.inner_area['max_y'] - unit_h_v # Posición Y de la base exterior
        current_x = x_start
        while current_x + unit_w_v <= x_end + epsilon:
            # Base Exterior
            outer_unit = {'x': current_x, 'y': y_outer, 'width': unit_w_v, 'height': unit_h_v, 'side': 'top'}
            self.outer_base_units.append(outer_unit)
            # Pasillo (vertical, debajo de base exterior)
            y_corridor = y_outer - corridor_h
            corridor = {'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_h, 'side': 'top'}
            self.corridor_units.append(corridor)
            # Base Interior (vertical, debajo de pasillo)
            y_inner = y_corridor - unit_h_v
            inner_unit = {'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v, 'side': 'top'}
            self.inner_base_units.append(inner_unit)
            current_x += unit_w_v

        # Lado IZQUIERDO (Base Ext: Horizontal, Pasillo: Horizontal, Base Int: Horizontal)
        x_outer = self.inner_area['min_x']
        y_start = self.stair_units[0]['y'] + stair_size
        y_end = self.stair_units[2]['y']
        current_y = y_start
        while current_y + unit_h_h <= y_end + epsilon:
            # Base Exterior
            outer_unit = {'x': x_outer, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h, 'side': 'left'}
            self.outer_base_units.append(outer_unit)
            # Pasillo (horizontal, a la derecha de base exterior)
            x_corridor = x_outer + unit_w_h
            # El "ancho" del pasillo es corridor_width, su "altura" es la dim corta (corridor_length)
            # ¡Ajuste! La dimensión del pasillo que corre paralela a la base debe ser corridor_length (short_base)
            # ¡Corrección! Para pasillo horizontal, ancho=corridor_h, alto=unit_h_h
            corridor = {'x': x_corridor, 'y': current_y, 'width': corridor_h, 'height': unit_h_h, 'side': 'left'}
            self.corridor_units.append(corridor)
            # Base Interior (horizontal, a la derecha de pasillo)
            x_inner = x_corridor + corridor_h
            inner_unit = {'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h, 'side': 'left'}
            self.inner_base_units.append(inner_unit)
            current_y += unit_h_h

        # Lado DERECHO (Base Ext: Horizontal, Pasillo: Horizontal, Base Int: Horizontal)
        x_outer = self.inner_area['max_x'] - unit_w_h # Posición X de la base exterior
        y_start = self.stair_units[1]['y'] + stair_size
        y_end = self.stair_units[3]['y']
        current_y = y_start
        while current_y + unit_h_h <= y_end + epsilon:
            # Base Exterior
            outer_unit = {'x': x_outer, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h, 'side': 'right'}
            self.outer_base_units.append(outer_unit)
            # Pasillo (horizontal, a la izquierda de base exterior)
            x_corridor = x_outer - corridor_h
            corridor = {'x': x_corridor, 'y': current_y, 'width': corridor_h, 'height': unit_h_h, 'side': 'right'}
            self.corridor_units.append(corridor)
            # Base Interior (horizontal, a la izquierda de pasillo)
            x_inner = x_corridor - unit_w_h
            inner_unit = {'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h, 'side': 'right'}
            self.inner_base_units.append(inner_unit)
            current_y += unit_h_h

        total_base = len(self.outer_base_units) + len(self.inner_base_units)
        return True, (f"{total_base} U.Base ({len(self.outer_base_units)} Ext, {len(self.inner_base_units)} Int), "
                      f"{len(self.corridor_units)} U.Pasillo, {len(self.stair_units)} U.Escalera calculadas")


# --- Clase Application (GUI con nuevo campo) ---
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno v2")
        self.geometry("950x700") # Ajustar tamaño

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
        # Botón Cargar
        self.load_button = tk.Button(self.control_frame, text="Cargar KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=(5, 10))

        # Frame para parámetros
        param_frame = tk.Frame(self.control_frame)
        param_frame.pack(side=tk.LEFT, padx=0)

        # Distancia Corona
        tk.Label(param_frame, text="D.Corona:").pack(side=tk.LEFT, padx=(0,1));
        self.offset_entry = tk.Entry(param_frame, width=6);
        self.offset_entry.pack(side=tk.LEFT, padx=(0, 5)); self.offset_entry.insert(0, "5")

        # Ancho Base
        tk.Label(param_frame, text="An.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_width_entry = tk.Entry(param_frame, width=6);
        self.base_width_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_width_entry.insert(0, "3")

        # Largo Base
        tk.Label(param_frame, text="La.Base:").pack(side=tk.LEFT, padx=(0,1));
        self.base_length_entry = tk.Entry(param_frame, width=6);
        self.base_length_entry.pack(side=tk.LEFT, padx=(0, 5)); self.base_length_entry.insert(0, "2")

        # *** NUEVO CAMPO: Ancho Pasillo ***
        tk.Label(param_frame, text="An.Pasillo:").pack(side=tk.LEFT, padx=(0,1));
        self.corridor_width_entry = tk.Entry(param_frame, width=6);
        self.corridor_width_entry.pack(side=tk.LEFT, padx=(0, 10)); self.corridor_width_entry.insert(0, "1") # Ejemplo

        # Botón Calcular
        self.calculate_button = tk.Button(self.control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize, state=tk.DISABLED)
        self.calculate_button.pack(side=tk.LEFT, padx=5)

        # Barra de Estado
        self.status_var = tk.StringVar(); self.status_var.set("Listo. Cargue KML.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # --- load_kml (sin cambios) ---
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

    # --- calculate_and_visualize (pasa nuevo parámetro) ---
    def calculate_and_visualize(self):
        if not self.kml_processor.bounding_box:
             messagebox.showwarning("Inválido", "Cargue KML primero."); return
        try:
            offset = float(self.offset_entry.get())
            base_width = float(self.base_width_entry.get())
            base_length = float(self.base_length_entry.get())
            corridor_width = float(self.corridor_width_entry.get()) # Obtener nuevo valor

            if offset < 0 or base_width <= 0 or base_length <= 0 or corridor_width <= 0:
                 messagebox.showerror("Entrada Inválida", "Offset >= 0. Anchos/Largos > 0.")
                 return
        except ValueError:
            messagebox.showerror("Entrada Inválida", "Valores numéricos inválidos."); return

        self.status_var.set("Calculando área interna..."); self.update_idletasks()
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success: messagebox.showerror("Error Cálculo", message); self.status_var.set(f"Error: {message}"); self._clear_plot(); return

        self.status_var.set("Calculando unidades..."); self.update_idletasks()
        # Pasar corridor_width a calculate_units
        success, message = self.kml_processor.calculate_units(base_width, base_length, corridor_width)
        if not success: messagebox.showerror("Error Cálculo", message); self.status_var.set(f"Error: {message}"); self._clear_plot(); return

        self.status_var.set("Generando visualización..."); self.update_idletasks()
        self._visualize_results()
        self.status_var.set(f"Listo. {message}") # Mostrar mensaje de éxito con counts

    # --- _clear_plot (sin cambios) ---
    def _clear_plot(self):
         if self.canvas: self.canvas.get_tk_widget().destroy(); self.canvas = None
         if self.toolbar and self.toolbar.winfo_exists(): self.toolbar.destroy(); self.toolbar = None
         for widget in self.plot_frame.winfo_children(): widget.destroy()

    # --- _visualize_results (dibuja nuevos tipos de unidad) ---
    def _visualize_results(self):
        self._clear_plot()
        if not self.kml_processor.bounding_box: return
        fig, ax = plt.subplots(figsize=(8, 6)); ax.set_aspect('equal', adjustable='box')
        bb = self.kml_processor.bounding_box

        # 1. Bounding Box
        ax.add_patch(Rectangle((bb['min_x'], bb['min_y']), bb['width'], bb['height'],
                               edgecolor='black', facecolor='#EEEEEE', alpha=0.6, lw=1, label='Bounding Box'))

        if self.kml_processor.inner_area:
            ia = self.kml_processor.inner_area; offset = self.kml_processor.offset_value
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
                label = 'U. Escalera' if not stair_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#8B0000', facecolor='#FFA07A', alpha=0.9, label=label)) # DarkRed/LightSalmon
                stair_plotted = True

            # 5. Outer Base Units
            outer_base_plotted = False
            for unit in self.kml_processor.outer_base_units:
                label = 'U. Base Exterior' if not outer_base_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#006400', facecolor='#90EE90', alpha=0.8, label=label)) # DarkGreen/LightGreen
                outer_base_plotted = True

            # 6. Corridor Units *** NUEVO ***
            corridor_plotted = False
            for unit in self.kml_processor.corridor_units:
                label = 'U. Pasillo' if not corridor_plotted else ""
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#FF8C00', facecolor='#FFD700', alpha=0.85, label=label)) # DarkOrange/Gold
                corridor_plotted = True

            # 7. Inner Base Units *** NUEVO ***
            inner_base_plotted = False
            for unit in self.kml_processor.inner_base_units:
                label = 'U. Base Interior' if not inner_base_plotted else ""
                # Mismo color que exterior pero quizás un poco más oscuro/claro? Usar el mismo por ahora.
                ax.add_patch(Rectangle((unit['x'], unit['y']), unit['width'], unit['height'],
                                       edgecolor='#006400', facecolor='#98FB98', alpha=0.75, label=label)) # DarkGreen/PaleGreen
                inner_base_plotted = True


        # --- Plot Setup ---
        padding_x = bb['width'] * 0.07; padding_y = bb['height'] * 0.07
        padding_x = max(padding_x, 1); padding_y = max(padding_y, 1)
        ax.set_xlim(bb['min_x'] - padding_x, bb['max_x'] + padding_x); ax.set_ylim(bb['min_y'] - padding_y, bb['max_y'] + padding_y)
        ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
        title = "Distribución de Unidades"
        if self.kml_processor.base_width_value > 0: title += f" (B:{self.kml_processor.base_width_value}x{self.kml_processor.base_length_value}, P:{self.kml_processor.corridor_width_value})"
        ax.set_title(title); ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(fontsize='small', loc='best')

        # --- Embed in Tkinter ---
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame); self.canvas.draw()
        canvas_widget = self.canvas.get_tk_widget(); canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame); self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

# --- Main execution block ---
if __name__ == "__main__":
    app = Application()
    app.mainloop()