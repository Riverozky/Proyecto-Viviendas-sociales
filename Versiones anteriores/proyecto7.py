import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.path import Path
import matplotlib.patches as patches
from pykml import parser
import numpy as np

def leer_kml(archivo):
    try:
        with open(archivo, 'r') as f:
            doc = parser.parse(f).getroot()
            polygon = doc.find(".//{http://www.opengis.net/kml/2.2}Polygon")
            if polygon is not None:
                coordinates = polygon.find(".//{http://www.opengis.net/kml/2.2}coordinates")
                if coordinates is not None:
                    coords = [tuple(map(float, c.split(',')[:2])) for c in coordinates.text.strip().split()]
                    # Convertir a numpy array para facilitar cálculos
                    return np.array(coords)
            messagebox.showerror("Error", "No se encontró un polígono válido en el archivo KML.")
            return None
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer el archivo KML: {e}")
        return None

def crear_corona_cuadrada(centro, lado_mayor, lado_menor):
    """Crea una corona cuadrada (área entre dos cuadrados concéntricos)"""
    cuadrado_mayor = plt.Rectangle((centro[0]-lado_mayor/2, centro[1]-lado_mayor/2), 
                                  lado_mayor, lado_mayor, 
                                  edgecolor='blue', facecolor='none', linestyle='--')
    cuadrado_menor = plt.Rectangle((centro[0]-lado_menor/2, centro[1]-lado_menor/2), 
                                  lado_menor, lado_menor, 
                                  edgecolor='green', facecolor='none', linestyle='--')
    return cuadrado_mayor, cuadrado_menor

def visualizar_terreno(coordenadas, ancho_unidad, alto_unidad, tipo_unidad, ancho_pasillo):
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    
    # Dibujar el terreno
    x, y = coordenadas[:, 0], coordenadas[:, 1]
    ax.fill(x, y, edgecolor='black', facecolor='lightgray', alpha=0.5)
    
    # Crear grid en metros
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.set_xticks(np.arange(min(x), max(x)+1, 1))
    ax.set_yticks(np.arange(min(y), max(y)+1, 1))
    
    # Calcular centro y dimensiones para la corona cuadrada
    centro = [np.mean(x), np.mean(y)]
    lado_mayor = min(max(x)-min(x), max(y)-min(y)) * 0.8
    lado_menor = lado_mayor * 0.6
    
    # Dibujar corona cuadrada
    cuadrado_mayor, cuadrado_menor = crear_corona_cuadrada(centro, lado_mayor, lado_menor)
    ax.add_patch(cuadrado_mayor)
    ax.add_patch(cuadrado_menor)
    
    # Distribuir unidades en la región central (cuadrado menor)
    region_central = {
        'x_min': centro[0] - lado_menor/2,
        'x_max': centro[0] + lado_menor/2,
        'y_min': centro[1] - lado_menor/2,
        'y_max': centro[1] + lado_menor/2
    }
    
    # Ajustar según tipo de unidad
    if tipo_unidad == "rectangulo":
        # Distribución con pasillos
        x_pos = region_central['x_min']
        y_pos = region_central['y_max'] - alto_unidad
        
        while y_pos >= region_central['y_min']:
            while x_pos + ancho_unidad <= region_central['x_max']:
                # Dibujar unidad base
                unidad = patches.Rectangle((x_pos, y_pos), ancho_unidad, alto_unidad, 
                                         edgecolor='red', facecolor='red', alpha=0.5)
                ax.add_patch(unidad)
                
                # Dibujar pasillo debajo si hay espacio
                if y_pos - alto_unidad - ancho_pasillo >= region_central['y_min']:
                    pasillo = patches.Rectangle((x_pos, y_pos - alto_unidad - ancho_pasillo), 
                                              ancho_unidad, ancho_pasillo, 
                                              edgecolor='yellow', facecolor='yellow', alpha=0.3)
                    ax.add_patch(pasillo)
                    
                    # Dibujar unidad base debajo del pasillo
                    if y_pos - alto_unidad*2 - ancho_pasillo >= region_central['y_min']:
                        unidad_debajo = patches.Rectangle((x_pos, y_pos - alto_unidad*2 - ancho_pasillo), 
                                                        ancho_unidad, alto_unidad, 
                                                        edgecolor='red', facecolor='red', alpha=0.5)
                        ax.add_patch(unidad_debajo)
                
                x_pos += ancho_unidad
            
            x_pos = region_central['x_min']
            y_pos -= alto_unidad * 2 + ancho_pasillo
    
    # Ajustar límites
    ax.set_xlim(min(x), max(x))
    ax.set_ylim(min(y), max(y))
    
    return fig

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Distribución de Unidades en Terreno")
        
        self.archivo = None
        self.coordenadas = None
        self.ancho_unidad = 1.0
        self.alto_unidad = 1.0
        self.ancho_pasillo = 0.5
        self.tipo_unidad = "rectangulo"
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        # Marco para archivo
        frame_archivo = tk.LabelFrame(self.root, text="Archivo KML")
        frame_archivo.pack(pady=5, fill="x")
        
        self.boton_cargar = tk.Button(frame_archivo, text="Cargar Archivo KML", command=self.cargar_archivo)
        self.boton_cargar.pack(pady=5)
        
        # Marco para unidades
        frame_unidades = tk.LabelFrame(self.root, text="Configuración de Unidades")
        frame_unidades.pack(pady=5, fill="x")
        
        # Tipo de unidad
        tk.Label(frame_unidades, text="Tipo de unidad base:").pack()
        self.tipo_var = tk.StringVar(value="rectangulo")
        tk.Radiobutton(frame_unidades, text="Cuadrado", variable=self.tipo_var, value="cuadrado").pack()
        tk.Radiobutton(frame_unidades, text="Rectángulo", variable=self.tipo_var, value="rectangulo").pack()
        
        # Dimensiones
        tk.Label(frame_unidades, text="Ancho unidad base (m):").pack()
        self.entrada_ancho = tk.Entry(frame_unidades)
        self.entrada_ancho.insert(0, "1.0")
        self.entrada_ancho.pack()
        
        tk.Label(frame_unidades, text="Alto unidad base (m):").pack()
        self.entrada_alto = tk.Entry(frame_unidades)
        self.entrada_alto.insert(0, "1.0")
        self.entrada_alto.pack()
        
        tk.Label(frame_unidades, text="Ancho pasillo (m):").pack()
        self.entrada_pasillo = tk.Entry(frame_unidades)
        self.entrada_pasillo.insert(0, "0.5")
        self.entrada_pasillo.pack()
        
        # Botón visualizar
        self.boton_visualizar = tk.Button(self.root, text="Visualizar Distribución", 
                                         command=self.visualizar, state="disabled")
        self.boton_visualizar.pack(pady=10)
        
        # Canvas para gráfico
        self.canvas = None
    
    def cargar_archivo(self):
        self.archivo = filedialog.askopenfilename(filetypes=[("KML files", "*.kml")])
        if self.archivo:
            self.coordenadas = leer_kml(self.archivo)
            if self.coordenadas is not None:
                self.boton_visualizar.config(state="normal")
                messagebox.showinfo("Éxito", "Archivo KML cargado correctamente.")
    
    def visualizar(self):
        try:
            self.ancho_unidad = float(self.entrada_ancho.get())
            self.alto_unidad = float(self.entrada_alto.get())
            self.ancho_pasillo = float(self.entrada_pasillo.get())
            self.tipo_unidad = self.tipo_var.get()
            
            # Si es cuadrado, forzar mismo ancho y alto
            if self.tipo_unidad == "cuadrado":
                self.alto_unidad = self.ancho_unidad
            
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
            
            fig = visualizar_terreno(self.coordenadas, self.ancho_unidad, self.alto_unidad, 
                                   self.tipo_unidad, self.ancho_pasillo)
            self.canvas = FigureCanvasTkAgg(fig, master=self.root)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()