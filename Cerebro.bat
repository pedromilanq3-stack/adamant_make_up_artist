@echo off
rem Abre o chat do Cerebro no navegador. Requer Python 3.11+ (python.org, marque "Add to PATH").
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 cerebro.pyz %*
) else (
  python cerebro.pyz %*
)
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
  pause
)
