#!/usr/bin/env python3
"""
Punto de entrada principal del proyecto Zaragoza Map PWA

Este archivo coordina la ejecución de los agentes y la generación de datos.
"""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent))

# Importar configuración
from config import *

# Importar agentes
from agentes.agente_1_buscador import Agente1Buscador
from agentes.agente_2_publicador import Agente2Publicador

# Importar herramientas
from tools.google_sheets_tool import GoogleSheetsTool


def main():
    """
    Función principal que orquesta la ejecución de los agentes.
    """
    print("=== Iniciando Zaragoza Map PWA ===\n")
    
    # TODO: Implementar la lógica principal
    # - Ejecutar agente 1 (buscador)
    # - Ejecutar agente 2 (publicador)
    # - Generar informe
    # - Actualizar web
    
    print("Sistema listo para ejecutar agentes.\n")


if __name__ == "__main__":
    main()
