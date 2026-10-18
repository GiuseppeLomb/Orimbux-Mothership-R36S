@echo off
rem ORIMBUX MOTHERSHIP no PC (Windows), a partir do repositorio - abre a nave numa janela.
rem Na primeira vez prepara o Python da nave (precisa de internet, ~1 minuto).
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%~dp0.venv\pronto.txt" (
  echo A preparar o Python da nave - so na primeira vez, precisa de internet...
  if not exist "%PY%" (
    py -3 -m venv "%~dp0.venv" 2>nul || python -m venv "%~dp0.venv"
  )
  if not exist "%PY%" (
    echo Nao encontrei o Python. Instala-o em https://www.python.org/downloads/ e abre isto outra vez.
    pause
    exit /b 1
  )
  "%PY%" -m pip install --disable-pip-version-check -q pysdl2-dll "audioop-lts; python_version>='3.13'"
  if errorlevel 1 (
    echo Falhou a instalacao. Confirma a ligacao a internet e abre isto outra vez.
    pause
    exit /b 1
  )
  echo ok> "%~dp0.venv\pronto.txt"
)
"%PY%" "%~dp0ports\mothership\main.py"
if errorlevel 1 (
  echo A nave fechou com um erro: ve o ficheiro ports\mothership\log.txt
  pause
)
