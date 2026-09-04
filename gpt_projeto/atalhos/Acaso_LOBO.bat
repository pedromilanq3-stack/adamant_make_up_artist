@echo off
rem Clique duplo: o acaso age sobre LOBO e os arquivos das salas sao regenerados.
cd /d "%~dp0\..\.."
python -m nucleo mente acaso LOBO --quantos 2
python -m nucleo empacotar >nul
python -m nucleo mente estado LOBO
pause
