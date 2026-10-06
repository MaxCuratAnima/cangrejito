"""Atajo del lanzador para correrlo con «pythonw -S lanzador.pyw» (el código está en lanzador.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lanzador import main

if __name__ == '__main__':
    main()
