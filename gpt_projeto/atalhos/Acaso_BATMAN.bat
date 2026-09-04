@echo off
rem Clique duplo: o acaso age sobre BATMAN e os arquivos das salas sao regenerados.
cd /d "%~dp0\..\.."
python -m nucleo mente acaso BATMAN --quantos 2
python -m nucleo empacotar >nul
python -m nucleo mente estado BATMAN
pause
