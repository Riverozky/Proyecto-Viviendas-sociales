Distribución de Unidades en Terreno v3.1 🏗️📍

Herramienta de escritorio para cargar polígonos de terreno desde archivos KML, calcular una distribución optimizada de diferentes tipos de unidades (base, pasillos, escaleras) según parámetros definidos por el usuario y visualizar el resultado gráficamente 🗺️
✨ Novedades en la Versión 3.1

🎛️ Control Total sobre las Dimensiones: Ahora puedes editar manualmente el ancho y alto del terreno después de cargar un KML, así como especificar el tamaño exacto de las unidades de escalera.

🤖 Botón Auto para Escaleras: Para facilitar el diseño, un nuevo botón "Auto" calcula un tamaño de escalera proporcional al ancho de una unidad base más un pasillo.

🎨 Nuevas Formas de Distribución: Se han añadido dos nuevos diseños: Forma L y Forma Rectangular, que se suman a la clásica Forma Cuadrada.

💅 Diseños Mejorados y Simplificados:

•La Forma Cuadrada ha sido rediseñada para ser siempre simétrica y alineada, eliminando espacios irregulares.

•Tanto la Forma Cuadrada como la Forma L se han simplificado para usar una sola fila de unidades base, resultando en un diseño más limpio y eficiente.

⚠️ Descargo de Responsabilidad Importante

Esta aplicación se encuentra en desarrollo activo. Actualmente no es operativa con todo tipo de archivos KML. Por el momento, se ha probado y funciona de manera más predecible con archivos KML que siguen una estructura de polígono simple. Se recomienda precaución al usar otros archivos KML, ya que podrían no ser procesados correctamente.
🌟 Funcionalidades Principales
📂 Carga de Geometría KML

•Importa el contorno de un terreno a partir de un archivo .kml

📋 Múltiples Diseños de Distribución

•Elige entre diferentes plantillas de layout:

•Forma Cuadrada (perímetro)

•Forma L

•Forma Rectangular

✍️ Definición de Parámetros de Diseño

•Dimensiones del Terreno: Ancho y alto (autocompletados desde el KML pero totalmente editables)

•Dimensiones de Unidades: Ancho y largo para unidades base, ancho para pasillos y tamaño para escaleras

•Distancia de Corona: Offset para el área interna utilizable

🧮 Cálculo de Distribución de Unidades

•Determina el área interna útil basándose en la corona

•Calcula y posiciona unidades base, de pasillo y de escalera según el diseño seleccionado

📊 Visualización Gráfica Interactiva

•Muestra el "bounding box" del terreno, el área interna y todas las unidades calculadas

•Utiliza matplotlib integrado en la interfaz gráfica

•Incluye barra de herramientas para navegar el gráfico (zoom, pan, guardar)

🖥️ Interfaz Gráfica de Usuario (GUI)

•Construida con tkinter para una fácil interacción

•Campos de entrada para todos los parámetros

•Botones para cargar archivos y ejecutar cálculos

•Barra de estado para mostrar mensajes y resultados del proceso

🛠️ Tecnologías Utilizadas

🐍 Python: Lenguaje de programación principal

🖼️ Tkinter: Para la construcción de la interfaz gráfica de usuario

📈 Matplotlib: Para la generación de gráficos 2D y su integración en Tkinter

🌐 pykml: Para el parseo (lectura y análisis) de archivos KML

➕ math: Para cálculos matemáticos diversos en la lógica de distribución

🚀 Empezando

Sigue estas instrucciones para poner en funcionamiento el programa en tu máquina local.
✅ Prerrequisitos

Asegúrate de tener instalado:

•Python 3.x

•Pip (el gestor de paquetes de Python)

•Las bibliotecas necesarias (ejecutando pip install tk matplotlib pykml)

📋 Uso
▶️ Ejecuta la aplicación:

•Navega a la carpeta donde se encuentra el script principal.

•Ejecútalo: python nombre_del_script.py

📂 Cargar KML:

•Haz clic en el botón "Cargar KML".

•Selecciona el archivo .kml que define el polígono del terreno.

•Los campos "Ancho Terreno" y "Alto Terreno" se rellenarán automáticamente.

✏️ Ingresar Parámetros:

•Ajusta las dimensiones de las unidades (An.Base, La.Base, An.Pasillo).

•Define el "Tam.Escalera" manualmente o presiona "Auto" para un cálculo proporcional.

•Si lo deseas, modifica las dimensiones del terreno en "Ancho Terreno" y "Alto Terreno".

•Establece la "D.Corona" (offset).

👇 Seleccionar Disposición:

•Elige el diseño que prefieras en el menú desplegable: Forma Cuadrada, Forma L o Forma Rectangular.

⚡ Calcular y Visualizar:

•Haz clic en el botón "Calcular y Visualizar".

•La aplicación procesará los datos y mostrará la distribución en el área de gráfico.

•La barra de estado indicará el resultado del cálculo (cantidad de unidades).

🔍 Interactuar con el Gráfico:

•Usa la barra de herramientas de Matplotlib debajo del gráfico para hacer zoom, mover la vista o guardar la imagen.
