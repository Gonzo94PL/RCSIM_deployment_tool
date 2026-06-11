# -*- coding: utf-8 -*-
"""
Aplikacja Wdrożeniowa RCSIM RPi5 (Deployment Tool) - Web Launcher.
Uruchamia serwer Flask dla interfejsu webowego.

Wersja v8.0.0 (2026-06-11)
Author: RCSIM / Mateusz 
"""

import sys
import os

# Dodaj bieżący katalog do ścieżki
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_server import start_server

if __name__ == "__main__":
    start_server()
