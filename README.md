# Distribución de Unidades en Terreno v2.3 🏗️

Herramienta de escritorio para cargar polígonos de terreno desde archivos KML, calcular una distribución optimizada de diferentes tipos de unidades (base, pasillos, escaleras, área central) según parámetros definidos por el usuario, y visualizar el resultado gráficamente.

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
