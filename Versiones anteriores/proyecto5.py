import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.path import Path
from pykml import parser

# Función para leer las coordenadas del polígono desde un archivo KML
def leer_kml(archivo):
    try:
        with open(archivo, 'r') as f:
            doc = parser.parse(f).getroot()
            # Extraer las coordenadas del polígono
            coordenadas = doc.Document.Placemark.Polygon.outerBoundaryIs.LinearRing.coordinates.text
            coordenadas = [tuple(map(float, c.split(',')[:2])) for c in coordenadas.strip().split()]
            return coordenadas
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer el archivo KML: {e}")
        return None

# Función para verificar si una unidad base está dentro del terreno
def unidad_dentro_del_terreno(vertices_unidad, terreno_path):
    return all(terreno_path.contains_points(vertices_unidad))

# Función para visualizar el terreno y las unidades base
def visualizar_terreno(coordenadas, ancho_unidad, alto_unidad, patron):
    fig, ax = plt.subplots()
    ax.set_aspect('equal')

    # Dibujar el polígono del terreno
    x, y = zip(*coordenadas)
    ax.fill(x, y, edgecolor='black', facecolor='lightgray', alpha=0.5)

    # Crear un objeto Path para el terreno
    terreno_path = Path(coordenadas)

    # Dibujar las unidades base según el patrón
    if patron == "cuadricula":
        for i in range(0, int(max(x)), int(ancho_unidad)):
            for j in range(0, int(max(y)), int(alto_unidad)):
                # Definir los vértices de la unidad base
                vertices_unidad = [
                    (i, j),
                    (i + ancho_unidad, j),
                    (i + ancho_unidad, j + alto_unidad),
                    (i, j + alto_unidad)
                ]
                # Verificar si la unidad base está dentro del terreno
                if unidad_dentro_del_terreno(vertices_unidad, terreno_path):
                    # Dibujar la unidad base en rojo
                    unidad = plt.Rectangle((i, j), ancho_unidad, alto_unidad, edgecolor='red', facecolor='red', alpha=0.5)
                    ax.add_patch(unidad)
    # Implementar otros patrones aquí

    # Ajustar los límites de la gráfica para que se vea todo
    ax.set_xlim(min(x), max(x))
    ax.set_ylim(min(y), max(y))

    return fig

# Interfaz gráfica
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MVP Terreno y Unidades Base")

        self.archivo = None
        self.coordenadas = []
        self.ancho_unidad = 0
        self.alto_unidad = 0
        self.patron = "cuadricula"

        self.crear_interfaz()

    def crear_interfaz(self):
        # Botón para cargar archivo
        self.boton_cargar = tk.Button(self.root, text="Cargar Archivo KML", command=self.cargar_archivo)
        self.boton_cargar.pack()

        # Entradas para las dimensiones de la unidad base
        self.label_ancho_unidad = tk.Label(self.root, text="Ancho Unidad Base (metros):")
        self.label_ancho_unidad.pack()
        self.entrada_ancho_unidad = tk.Entry(self.root)
        self.entrada_ancho_unidad.pack()

        self.label_alto_unidad = tk.Label(self.root, text="Alto Unidad Base (metros):")
        self.label_alto_unidad.pack()
        self.entrada_alto_unidad = tk.Entry(self.root)
        self.entrada_alto_unidad.pack()

        # Selección de patrón
        self.label_patron = tk.Label(self.root, text="Seleccione el patrón de colocación:")
        self.label_patron.pack()
        self.patron_var = tk.StringVar(value="cuadricula")
        self.opciones_patron = [
            ("Cuadrícula", "cuadricula"),
            ("Diagonal", "diagonal"),
            ("Rectangular Vertical", "rectangular_vertical"),
            ("Rectangular Horizontal", "rectangular_horizontal")
        ]
        for texto, valor in self.opciones_patron:
            tk.Radiobutton(self.root, text=texto, variable=self.patron_var, value=valor).pack()

        # Botón para visualizar
        self.boton_visualizar = tk.Button(self.root, text="Visualizar", command=self.visualizar)
        self.boton_visualizar.pack()

        # Canvas para la gráfica
        self.canvas = None

    def cargar_archivo(self):
        self.archivo = filedialog.askopenfilename(filetypes=[("KML files", "*.kml")])
        if self.archivo:
            self.coordenadas = leer_kml(self.archivo)
            if self.coordenadas:
                messagebox.showinfo("Éxito", "Archivo KML cargado correctamente.")

    def visualizar(self):
        try:
            self.ancho_unidad = float(self.entrada_ancho_unidad.get())
            self.alto_unidad = float(self.entrada_alto_unidad.get())
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos.")
            return

        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        self.patron = self.patron_var.get()
        fig = visualizar_terreno(self.coordenadas, self.ancho_unidad, self.alto_unidad, self.patron)
        self.canvas = FigureCanvasTkAgg(fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

# Ejecutar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()