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

    # --- calculate_units (CON NUEVO CÁLCULO DE STAIR_SIZE) ---
    def calculate_units(self, base_width, base_length, corridor_width):
        if not self.inner_area: return False, "Calcule área interna"
        if base_width <= 0 or base_length <= 0 or corridor_width <= 0: return False, "Dims base y pasillo deben ser > 0."

        self.base_width_value = base_width
        self.base_length_value = base_length
        self.corridor_width_value = corridor_width

        # *** NUEVO CÁLCULO DE STAIR_SIZE ***
        # El tamaño de la escalera es la suma de las "profundidades" de las capas:
        # Profundidad de capa base exterior = base_width
        # Profundidad de capa pasillo = corridor_width
        # Profundidad de capa base interior = base_width
        stair_size = (2 * base_width) + corridor_width
        # print(f"Debug: base_width={base_width}, corridor_width={corridor_width}, STAIR_SIZE_CALCULATED={stair_size}")


        required_dim_for_stairs = 2 * stair_size
        if required_dim_for_stairs > self.inner_area['width'] or required_dim_for_stairs > self.inner_area['height']:
             available_space_for_one_stair = min(self.inner_area['width'] / 2, self.inner_area['height'] / 2)
             if stair_size > available_space_for_one_stair and available_space_for_one_stair > 0 :
                 stair_size_old = stair_size
                 stair_size = available_space_for_one_stair
                 print(f"Advertencia: Tamaño U.Escalera ({stair_size_old:.2f}) excede área interna. Reducido a {stair_size:.2f}.")
             elif available_space_for_one_stair <= 0:
                  self.stair_units = []
                  # Considerar si retornar False o solo advertir. Por ahora, advertimos y continuamos.
                  print("Advertencia: No hay espacio suficiente en el área interna para las unidades escalera.")


        if stair_size <= 0 :
             # Si después de los ajustes, el tamaño es inválido, no podemos continuar con las escaleras.
             self.stair_units = []
             print(f"Advertencia: Tamaño U. Escalera final es <= 0 ({stair_size:.2f}). No se generarán U. Escalera.")
             # Podríamos retornar False aquí si las escaleras son críticas.
             # return False, f"Tamaño U. Escalera calculado es <= 0 ({stair_size:.2f})."


        if stair_size > 0 and self.inner_area:
            self.stair_units = [
                {'x': self.inner_area['min_x'], 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size},
                {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['min_y'], 'width': stair_size, 'height': stair_size},
                {'x': self.inner_area['min_x'], 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size},
                {'x': self.inner_area['max_x'] - stair_size, 'y': self.inner_area['max_y'] - stair_size, 'width': stair_size, 'height': stair_size}
            ]
        else:
            self.stair_units = []


        effective_stair_size_for_center = stair_size if self.stair_units and stair_size > 0 else 0

        center_avail_width = max(0, self.inner_area['width'] - 2 * effective_stair_size_for_center)
        center_avail_height = max(0, self.inner_area['height'] - 2 * effective_stair_size_for_center)
        central_size_dim = min(center_avail_width, center_avail_height) * 0.4
        
        if central_size_dim > 0:
            center_start_x = self.inner_area['min_x'] + effective_stair_size_for_center
            center_start_y = self.inner_area['min_y'] + effective_stair_size_for_center
            center_x_coord = center_start_x + center_avail_width / 2
            center_y_coord = center_start_y + center_avail_height / 2
            self.central_area = {
                'min_x': center_x_coord - central_size_dim / 2, 'max_x': center_x_coord + central_size_dim / 2,
                'min_y': center_y_coord - central_size_dim / 2, 'max_y': center_y_coord + central_size_dim / 2,
                'width': central_size_dim, 'height': central_size_dim
            }
        else:
            self.central_area = None

        self.outer_base_units = []
        self.inner_base_units = []
        self.corridor_units = []
        epsilon = 1e-9

        unit_w_v = base_length
        unit_h_v = base_width
        unit_w_h = base_width
        unit_h_h = base_length
        
        start_offset_x_bottom = (self.stair_units[0]['x'] + self.stair_units[0]['width']
                                 if self.stair_units and len(self.stair_units) > 0 else self.inner_area['min_x'])
        end_limit_x_bottom = (self.stair_units[1]['x']
                              if self.stair_units and len(self.stair_units) > 1 else self.inner_area['max_x'])
        
        y_outer_bottom = self.inner_area['min_y']
        current_x = start_offset_x_bottom
        
        if current_x < end_limit_x_bottom:
            while current_x + unit_w_v <= end_limit_x_bottom + epsilon:
                outer_unit = {'x': current_x, 'y': y_outer_bottom, 'width': unit_w_v, 'height': unit_h_v}
                self.outer_base_units.append(outer_unit)
                y_corridor = y_outer_bottom + unit_h_v
                corridor = {'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_width}
                self.corridor_units.append(corridor)
                y_inner = y_corridor + corridor_width
                inner_unit = {'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v}
                self.inner_base_units.append(inner_unit)
                current_x += unit_w_v

        start_offset_x_top = (self.stair_units[2]['x'] + self.stair_units[2]['width']
                              if self.stair_units and len(self.stair_units) > 2 else self.inner_area['min_x'])
        end_limit_x_top = (self.stair_units[3]['x']
                           if self.stair_units and len(self.stair_units) > 3 else self.inner_area['max_x'])

        y_outer_top = self.inner_area['max_y'] - unit_h_v
        current_x = start_offset_x_top

        if current_x < end_limit_x_top:
            while current_x + unit_w_v <= end_limit_x_top + epsilon:
                outer_unit = {'x': current_x, 'y': y_outer_top, 'width': unit_w_v, 'height': unit_h_v}
                self.outer_base_units.append(outer_unit)
                y_corridor = y_outer_top - corridor_width
                corridor = {'x': current_x, 'y': y_corridor, 'width': unit_w_v, 'height': corridor_width}
                self.corridor_units.append(corridor)
                y_inner = y_corridor - unit_h_v
                inner_unit = {'x': current_x, 'y': y_inner, 'width': unit_w_v, 'height': unit_h_v}
                self.inner_base_units.append(inner_unit)
                current_x += unit_w_v

        x_outer_left = self.inner_area['min_x']
        start_offset_y_left = (self.stair_units[0]['y'] + self.stair_units[0]['height']
                               if self.stair_units and len(self.stair_units) > 0 else self.inner_area['min_y'])
        end_limit_y_left = (self.stair_units[2]['y']
                             if self.stair_units and len(self.stair_units) > 2 else self.inner_area['max_y'])
        current_y = start_offset_y_left

        if current_y < end_limit_y_left:
            while current_y + unit_h_h <= end_limit_y_left + epsilon:
                outer_unit = {'x': x_outer_left, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h}
                self.outer_base_units.append(outer_unit)
                x_corridor = x_outer_left + unit_w_h
                corridor = {'x': x_corridor, 'y': current_y, 'width': corridor_width, 'height': unit_h_h}
                self.corridor_units.append(corridor)
                x_inner = x_corridor + corridor_width
                inner_unit = {'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h}
                self.inner_base_units.append(inner_unit)
                current_y += unit_h_h

        x_outer_right = self.inner_area['max_x'] - unit_w_h
        start_offset_y_right = (self.stair_units[1]['y'] + self.stair_units[1]['height']
                                if self.stair_units and len(self.stair_units) > 1 else self.inner_area['min_y'])
        end_limit_y_right = (self.stair_units[3]['y']
                              if self.stair_units and len(self.stair_units) > 3 else self.inner_area['max_y'])
        current_y = start_offset_y_right

        if current_y < end_limit_y_right:
            while current_y + unit_h_h <= end_limit_y_right + epsilon:
                outer_unit = {'x': x_outer_right, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h}
                self.outer_base_units.append(outer_unit)
                x_corridor = x_outer_right - corridor_width
                corridor = {'x': x_corridor, 'y': current_y, 'width': corridor_width, 'height': unit_h_h}
                self.corridor_units.append(corridor)
                x_inner = x_corridor - unit_w_h
                inner_unit = {'x': x_inner, 'y': current_y, 'width': unit_w_h, 'height': unit_h_h}
                self.inner_base_units.append(inner_unit)
                current_y += unit_h_h
        
        total_base = len(self.outer_base_units) + len(self.inner_base_units)
        return True, (f"{total_base} U.Base ({len(self.outer_base_units)} Ext, {len(self.inner_base_units)} Int), "
                      f"{len(self.corridor_units)} U.Pasillo, {len(self.stair_units)} U.Escalera calculadas")


# --- Clase Application ---
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno v2.2") # Versión actualizada
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