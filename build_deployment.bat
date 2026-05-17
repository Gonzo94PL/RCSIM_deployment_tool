@echo off
rem ============================================================================
rem RCSIM Deployment Tool Build Script
rem Copyright (c) 2025-2026 RCSIM Project. All rights reserved.
rem License: Proprietary / RCSIM Standard License
rem ============================================================================
echo [RCSIM BUILD] Inicjalizacja kompilacji narzedzia wdrozeniowego...
echo [RCSIM BUILD] Upewnianie sie, ze wymagane pakiety sa zainstalowane...

python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [RCSIM BUILD] PyInstaller nie jest zainstalowany. Instalowanie...
    pip install pyinstaller
)

python -c "import paramiko" 2>nul
if %errorlevel% neq 0 (
    echo [RCSIM BUILD] Paramiko nie jest zainstalowane. Instalowanie...
    pip install paramiko cryptography pyinstaller-hooks-contrib
)

echo [RCSIM BUILD] Uruchamianie kompilacji za pomoca build_deployment.py...
python "%~dp0core\build_deployment.py"

if %errorlevel% equ 0 (
    echo ============================================================================
    echo [RCSIM BUILD] SUKCES! Kompilacja zakonczona pomyslnie.
    echo [RCSIM BUILD] Plik wykonywalny znajduje sie w:
    echo               RCSIM_deployment_tool\dist\RCsimDeployment.exe
    echo ============================================================================
) else (
    echo ============================================================================
    echo [RCSIM BUILD] BLAD! Proces kompilacji zakonczyl sie niepowodzeniem.
    echo ============================================================================
)

pause
