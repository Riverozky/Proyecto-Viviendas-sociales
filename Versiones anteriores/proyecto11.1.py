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
                
                # Extraer coordenadas y calcular bounding box
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
        
        # Tamaño de las unidades escalera (cuadradas con lado = base_length)
        stair_size = base_length
        
        # Calcular espacio disponible para unidades base (excluyendo las áreas de las escaleras)
        available_width = self.inner_area['width'] - 2 * stair_size
        available_height = self.inner_area['height'] - 2 * stair_size
        
        # Calcular cuántas unidades base caben en el espacio disponible
        num_units_x = math.floor(available_width / base_width)
        num_units_y = math.floor(available_height / base_length)
        
        if num_units_x <= 0 or num_units_y <= 0:
            return False, "Las dimensiones de las unidades son demasiado grandes para el área disponible"
        
        # Calcular el espacio sobrante para centrar las unidades
        remaining_space_x = available_width - num_units_x * base_width
        remaining_space_y = available_height - num_units_y * base_length
        
        # Posición inicial de las unidades base (centradas)
        start_x = self.inner_area['min_x'] + stair_size + remaining_space_x / 2
        start_y = self.inner_area['min_y'] + stair_size + remaining_space_y / 2
        
        # Generar posiciones de las unidades base
        self.base_units = []
        for i in range(num_units_x):
            for j in range(num_units_y):
                x = start_x + i * base_width
                y = start_y + j * base_length
                self.base_units.append({
                    'x': x,
                    'y': y,
                    'width': base_width,
                    'height': base_length
                })
        
        # Generar posiciones de las unidades escalera (esquinas)
        # NOTA: Todas las unidades escalera tienen dimensiones base_length x base_length
        self.stair_units = [
            # Esquina inferior izquierda
            {
                'x': self.inner_area['min_x'],
                'y': self.inner_area['min_y'],
                'width': base_length,  # Corregido: ahora usa base_length para ambos lados
                'height': base_length   # Corregido: ahora usa base_length para ambos lados
            },
            # Esquina inferior derecha
            {
                'x': self.inner_area['max_x'] - base_length,  # Corregido: ahora usa base_length
                'y': self.inner_area['min_y'],
                'width': base_length,
                'height': base_length
            },
            # Esquina superior izquierda
            {
                'x': self.inner_area['min_x'],
                'y': self.inner_area['max_y'] - base_length,  # Corregido: ahora usa base_length
                'width': base_length,
                'height': base_length
            },
            # Esquina superior derecha
            {
                'x': self.inner_area['max_x'] - base_length,  # Corregido: ahora usa base_length
                'y': self.inner_area['max_y'] - base_length,  # Corregido: ahora usa base_length
                'width': base_length,
                'height': base_length
            }
        ]
        
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
        # Frame para controles
        control_frame = tk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Botón para cargar KML
        self.load_button = tk.Button(control_frame, text="Cargar Archivo KML", command=self.load_kml)
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        # Entradas para parámetros
        param_frame = tk.Frame(control_frame)
        param_frame.pack(side=tk.LEFT, padx=10)
        
        # Distancia corona
        tk.Label(param_frame, text="Distancia Corona (m):").grid(row=0, column=0, sticky=tk.W)
        self.offset_entry = tk.Entry(param_frame, width=10)
        self.offset_entry.grid(row=0, column=1, padx=5)
        self.offset_entry.insert(0, "5")
        
        # Ancho unidad base
        tk.Label(param_frame, text="Ancho Unidad Base (m):").grid(row=1, column=0, sticky=tk.W)
        self.base_width_entry = tk.Entry(param_frame, width=10)
        self.base_width_entry.grid(row=1, column=1, padx=5)
        self.base_width_entry.insert(0, "2")
        
        # Largo unidad base (y escalera)
        tk.Label(param_frame, text="Largo Unidad Base/Escalera (m):").grid(row=2, column=0, sticky=tk.W)
        self.base_length_entry = tk.Entry(param_frame, width=10)
        self.base_length_entry.grid(row=2, column=1, padx=5)
        self.base_length_entry.insert(0, "3")
        
        # Botón para calcular y visualizar
        self.calculate_button = tk.Button(control_frame, text="Calcular y Visualizar", command=self.calculate_and_visualize)
        self.calculate_button.pack(side=tk.LEFT, padx=5)
        
        # Barra de estado
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
        # Limpiar figura anterior si existe
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        if self.toolbar:
            self.toolbar.destroy()
        
        # Crear nueva figura
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal')
        
        # Dibujar bounding box
        bb = self.kml_processor.bounding_box
        ax.add_patch(Rectangle(
            (bb['min_x'], bb['min_y']), bb['width'], bb['height'],
            edgecolor='black', facecolor='none', linewidth=2
        ))
        
        # Dibujar área interna
        ia = self.kml_processor.inner_area
        ax.add_patch(Rectangle(
            (ia['min_x'], ia['min_y']), ia['width'], ia['height'],
            edgecolor='blue', facecolor='none', linestyle='dotted', linewidth=2
        ))
        
        # Dibujar unidades base (verde)
        for unit in self.kml_processor.base_units:
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='green', facecolor='lightgreen', alpha=0.7
            ))
        
        # Dibujar unidades escalera (rojo)
        for unit in self.kml_processor.stair_units:
            ax.add_patch(Rectangle(
                (unit['x'], unit['y']), unit['width'], unit['height'],
                edgecolor='red', facecolor='salmon', alpha=0.7
            ))
        
        # Configurar ejes
        ax.set_xlim(bb['min_x'] - 5, bb['max_x'] + 5)
        ax.set_ylim(bb['min_y'] - 5, bb['max_y'] + 5)
        ax.set_xlabel("Coordenada X")
        ax.set_ylabel("Coordenada Y")
        ax.set_title("Distribución de Unidades en Terreno")
        ax.grid(True)
        
        # Mostrar figura en Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Añadir barra de herramientas de navegación
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = Application()
    app.mainloop()