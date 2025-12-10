@echo off
REM ===== Início - Avaliação Maple Bear =====

REM Ir para a pasta do projeto
cd /d "D:\Projeto avaliação Maple Bear"

REM Opcional: mostrar onde estamos
echo Executando a partir de: %CD%

REM Rodar o app Streamlit
python -m streamlit run app.py

REM Mantém a janela aberta se der erro
pause
