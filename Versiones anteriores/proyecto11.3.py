import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from pykml import parser
import math

class KMLProcessor:
    def __init__(self):
        self.bounding_box = None
        self.inner_area = None
        self.base_units = []
        self.stair_units = []
        self.central_area = None
    
    def load_kml(self, file_path):
        try:
            with open(file_path, 'r') as f:
                doc = parser.parse(f).getroot()
                polygon = doc.find(".//{http://www.opengis.net/kml/2.2}Polygon")
                if polygon is None:
                    return False, "No se encontró un polígono en el archivo KML"
                
                coordinates = polygon.find(".//{http://www.opengis.net/kml/2.2}coordinates")
                if coordinates is None:
                    return False, "No se encontraron coordenadas en el polígono"
                
                coords = [tuple(map(float, c.split(',')[:2])) for c in coordinates.text.strip().split()]
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
        except Exception as e:
            return False, f"Error al leer el archivo KML: {str(e)}"
    
    def calculate_inner_area(self, offset):
        if not self.bounding_box:
            return False, "Primero debe cargar un archivo KML"
        
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
        
        stair_size = base_length
        
        # Definir las 4 unidades escalera en las esquinas
        self.stair_units = [
            # Esquina inferior izquierda (stair1)
            {
                'x': self.inner_area['min_x'],
                'y': self.inner_area['min_y'],
                'width': stair_size,
                'height': stair_size
            },
            # Esquina inferior derecha (stair2)
            {
                'x': self.inner_area['max_x'] - stair_size,
                'y': self.inner_area['min_y'],
                'width': stair_size,
                'height': stair_size
            },
            # Esquina superior izquierda (stair3)
            {
                'x': self.inner_area['min_x'],
                'y': self.inner_area['max_y'] - stair_size,
                'width': stair_size,
                'height': stair_size
            },
            # Esquina superior derecha (stair4)
            {
                'x': self.inner_area['max_x'] - stair_size,
                'y': self.inner_area['max_y'] - stair_size,
                'width': stair_size,
                'height': stair_size
            }
        ]
        
        # Calcular área central cuadrada (dejando espacio para las escaleras)
        central_size = min(self.inner_area['width'], self.inner_area['height']) * 0.4  # 40% del tamaño menor
        center_x = (self.inner_area['min_x'] + self.inner_area['max_x']) / 2
        center_y = (self.inner_area['min_y'] + self.inner_area['max_y']) / 2
        
        self.central_area = {
            'min_x': center_x - central_size/2,
            'max_x': center_x + central_size/2,
            'min_y': center_y - central_size/2,
            'max_y': center_y + central_size/2,
            'width': central_size,
            'height': central_size
        }
        
        # Generar unidades base solo en los lados no adyacentes a la corona
        self.base_units = []
        
        # Lado derecho (desde stair1 hacia arriba)
        x = self.stair_units[0]['x'] + stair_size
        y = self.stair_units[0]['y']
        while y + base_length <= self.stair_units[2]['y'] and x + base_width <= self.central_area['min_x']:
            self.base_units.append({
                'x': x,
                'y': y,
                'width': base_width,
                'height': base_length
            })
            y += base_length
        
        # Lado superior (desde stair3 hacia la derecha)
        x = self.stair_units[2]['x']
        y = self.stair_units[2]['y'] + stair_size
        while x + base_width <= self.stair_units[3]['x'] and y + base_length <= self.central_area['min_y']:
            self.base_units.append({
                'x': x,
                'y': y,
                'width': base_width,
                'height': base_length
            })
            x += base_width
        
        # Lado izquierdo (desde stair4 hacia abajo)
        x = self.stair_units[3]['x'] - base_width
        y = self.stair_units[3]['y']
        while y - base_length >= self.stair_units[1]['y'] and x >= self.central_area['max_x']:
            self.base_units.append({
                'x': x,
                'y': y - base_length,
                'width': base_width,
                'height': base_length
            })
            y -= base_length
        
        # Lado inferior (desde stair2 hacia la izquierda)
        x = self.stair_units[1]['x']
        y = self.stair_units[1]['y'] - base_length
        while x - base_width >= self.stair_units[0]['x'] and y >= self.central_area['max_y']:
            self.base_units.append({
                'x': x - base_width,
                'y': y,
                'width': base_width,
                'height': base_length
            })
            x -= base_width
        
        return True, f"{len(self.base_units)} unidades base y 4 unidades escalera calculadas"

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distribución de Unidades en Terreno")
        self.geometry("800x600")
        
        self.kml_processor = KMLProcessor()
        self.current_figure = None
        self.canvas = None
        self.toolbar = None
        
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
        self.base_width_entry.insert(0, "2")
        
        tk.Label(param_frame, text="Largo Unidad Base/Escalera (m):").grid(row=2, column=0, sticky=tk.W)
        self.base_length_entry = tk.Entry(param_frame, width=10)
        self.base_length_entry.grid(row=2, column=1, padx=5)
        self.base_length_entry.insert(0, "3")
        
        self.calculate_button = tk.Button(control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize)
        self.calculate_button.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        self.status_label = tk.Label(control_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def load_kml(self):
        file_path = filedialog.askopenfilename(filetypes=[("KML files", "*.kml")])
        if file_path:
            self.status_var.set("Procesando KML...")
            self.update()
            
            success, message = self.kml_processor.load_kml(file_path)
            if success:
                self.status_var.set(message)
            else:
                messagebox.showerror("Error", message)
                self.status_var.set("Error al cargar KML")
    
    def calculate_and_visualize(self):
        try:
            offset = float(self.offset_entry.get())
            base_width = float(self.base_width_entry.get())
            base_length = float(self.base_length_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
            return
        
        self.status_var.set("Calculando área interna...")
        self.update()
        
        success, message = self.kml_processor.calculate_inner_area(offset)
        if not success:
            messagebox.showerror("Error", message)
            self.status_var.set("Error en cálculo")
            return
        
        self.status_var.set("Calculando unidades...")
        self.update()
        
        success, message = self.kml_processor.calculate_units(base_width, base_length)
        if not success:
            messagebox.showerror("Error", message)
            self.status_var.set("Error en cálculo")
            return
        
        self.status_var.set("Generando visualización...")
        self.update()
        
        self.visualize()
        self.status_var.set(message)
    
    def visualize(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        if self.toolbar:
            self.toolbar.destroy()
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal')
        
        bb = self.kml_processor.bounding_box
        ax.add_patch(Rectangle(
            (bb['min_x'], bb['min_y']), bb['width'], bb['height'],
            edgecolor='black', facecolor='none', linewidth=2
        ))
        
        ia = self.kml_processor.inner_area
        ax.add_patch(Rectangle(
            (ia['min_x'], ia['min_y']), ia['width'], ia['height'],
            edgecolor='blue', facecolor='none', linestyle='dotted', linewidth=2
        ))
        
        if self.kml_processor.central_area:
            ca = self.kml_processor.central_area
            ax.add_patch(Rectangle(
                (ca['min_x'], ca['min_y']), ca['width'], ca['height'],
                edgecolor='purple', facecolor='lavender', alpha=0.5
            ))
        
        for unit in self.kml_processor.base_units:
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='green', facecolor='lightgreen', alpha=0.7
            ))
        
        for unit in self.kml_processor.stair_units:
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='red', facecolor='salmon', alpha=0.7
            ))
        
        ax.set_xlim(bb['min_x'] - 5, bb['max_x'] + 5)
        ax.set_ylim(bb['min_y'] - 5, bb['max_y'] + 5)
        ax.set_xlabel("Coordenada X")
        ax.set_ylabel("Coordenada Y")
        ax.set_title("Distribución de Unidades en Terreno")
        ax.grid(True)
        
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = Application()
    app.mainloop()