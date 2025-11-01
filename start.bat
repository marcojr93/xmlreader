@echo off
echo ========================================
echo   CaaS - Compliance as a Service
echo ========================================
echo.
echo Abrindo Landing Page...
start templates\landing_page.html
echo.
echo Aguardando 3 segundos...
timeout /t 3 /nobreak > nul
echo.
echo Iniciando aplicacao Streamlit...
echo.

REM Ativar ambiente virtual e executar Streamlit
call .venv\Scripts\activate.bat
streamlit run app.py --server.port 8501

echo.
echo Aplicacao encerrada.
pause