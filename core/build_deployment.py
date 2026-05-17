"""
Skrypt do budowania pliku wykonywalnego aplikacji wdrożeniowej przy użyciu PyInstaller.
Script for building the deployment application executable using PyInstaller.
"""

import os

import PyInstaller.__main__

if __name__ == "__main__":
    # Zmień katalog na katalog główny narzędzia wdrożeniowego (rodzic folderu 'core')
    # Change directory to the root of the deployment tool (parent of 'core')
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Uruchomienie PyInstallera bezpośrednio z pliku .spec dla poprawności pakowania i zależności
    # Run PyInstaller directly using the .spec file to ensure correct packaging and dependencies
    PyInstaller.__main__.run(
        [
            "RCsimDeployment.spec",
            "--clean",
            "--log-level=INFO",
        ]
    )
