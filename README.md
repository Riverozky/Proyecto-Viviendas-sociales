# Distribución de Unidades en Terreno v2.3 🏗️

Herramienta de escritorio para cargar polígonos de terreno desde archivos KML, calcular una distribución optimizada de diferentes tipos de unidades (base, pasillos, escaleras, área central) según parámetros definidos por el usuario, y visualizar el resultado gráficamente.

##⚠️ **Descargo de Responsabilidad Importante:**
* **Esta aplicación se encuentra en desarrollo activo. Actualmente, **no es operativa con todo tipo de archivos KML.** Por el momento, se ha probado y funciona de manera más predecible con archivos KML específicos denominados `terreno.kml` y `terreno.copy.kml` que siguen una estructura particular de polígono. Se recomienda precaución al usar otros archivos KML, ya que podrían no ser procesados correctamente.

## 🌟 Funcionalidades Principales

* **Carga de Geometría KML**: Importa el contorno de un terreno a partir de un archivo `.kml`.
* **Definición de Parámetros de Diseño**:
    * Distancia de Corona (offset para el área interna utilizable).
    * Dimensiones de Unidades Base (ancho y largo).
    * Ancho de Pasillos.
* **Cálculo de Distribución de Unidades**:
    * Determina el área interna útil.
    * Calcula y posiciona:
        * Unidades Base Exteriores e Interiores.
        * Unidades de Pasillo.
        * Unidades de Escalera (con ajuste dinámico de tamaño y posición).
        * Un posible Área Central.
* **Visualización Gráfica Interactiva**:
    * Muestra el "bounding box" del terreno, el área interna y todas las unidades calculadas.
    * Utiliza `matplotlib` integrado en la interfaz gráfica.
    * Incluye barra de herramientas para navegar el gráfico (zoom, pan, guardar).
* **Interfaz Gráfica de Usuario (GUI)**:
    * Construida con `tkinter` para una fácil interacción.
    * Campos de entrada para todos los parámetros.
    * Botones para cargar archivos y ejecutar cálculos.
    * Barra de estado para mostrar mensajes y resultados del proceso.

## 🛠️ Tecnologías Utilizadas

* **Python**: Lenguaje de programación principal.
* **Tkinter**: Para la construcción de la interfaz gráfica de usuario.
* **Matplotlib**: Para la generación de gráficos 2D y su integración en Tkinter.
* **pykml**: Para el parseo (lectura y análisis) de archivos KML.
* **math**: Para cálculos matemáticos diversos en la lógica de distribución.

## 🚀 Empezando

Sigue estas instrucciones para poner en funcionamiento el programa en tu máquina local.

### Prerrequisitos

Asegúrate de tener instalado:

* Python 3.x
* Pip (el gestor de paquetes de Python)

## 📋 Uso

1.  **Ejecuta la aplicación:**
    Navega a la carpeta donde se encuentra el script principal (ej: `nombre_del_script.py`) y ejecútalo:
    ```bash
    python nombre_del_script.py
    ```
2.  **Cargar KML**:
    * Haz clic en el botón **"Cargar KML"**.
    * Selecciona el archivo `.kml` que define el polígono del terreno.
    * La barra de estado mostrará información del KML cargado.
3.  **Ingresar Parámetros**:
    * **D.Corona**: Define el offset desde el borde del terreno para el área interna.
    * **An.Base**: Ancho de las unidades base.
    * **La.Base**: Largo de las unidades base.
    * **An.Pasillo**: Ancho de los pasillos.
4.  **Calcular y Visualizar**:
    * Haz clic en el botón **"Calcular y Visualizar"**.
    * La aplicación procesará los datos y mostrará la distribución en el área de gráfico.
    * La barra de estado indicará el resultado del cálculo (cantidad de unidades).
5.  **Interactuar con el Gráfico**:
    * Usa la barra de herramientas de Matplotlib debajo del gráfico para hacer zoom, mover la vista, o guardar la imagen.
