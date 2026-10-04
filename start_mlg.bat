@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist venv (
    echo Tworze srodowisko Pythona...
    python -m venv venv || goto :error
    call venv\Scripts\activate.bat
    pip install -r requirements.txt || goto :error
) else (
    call venv\Scripts\activate.bat
)

if not exist .env (
    echo Brak pliku .env. Skopiuj .env.example jako .env i uzupelnij token.
    pause
    exit /b 1
)

python -m mlg
pause
exit /b 0

:error
echo Cos poszlo nie tak. Sprawdz, czy Python jest zainstalowany i dodany do PATH.
pause
exit /b 1
