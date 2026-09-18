@echo off
setlocal enabledelayedexpansion
title WissTek-IoT - Instalacao das bibliotecas Python

echo ==============================================================
echo    WissTek-IoT - Instalacao das bibliotecas Python
echo ==============================================================
echo.
echo  Serao instaladas:
echo    pyserial      - comunicacao com a porta serial (USB)
echo    pandas        - manipulacao de tabelas de dados
echo    matplotlib    - graficos
echo    schedule      - agendamento de tarefas
echo    Pillow        - imagens
echo    customtkinter - interface grafica
echo    paho-mqtt     - framework MQTT
echo.

REM ---------------------------------------------------------------
REM  Procura o Python: primeiro o launcher "py", depois "python"
REM ---------------------------------------------------------------
set "PY="
where py >nul 2>nul
if %errorlevel%==0 set "PY=py"
if not defined PY (
    where python >nul 2>nul
    if !errorlevel!==0 set "PY=python"
)
if not defined PY goto sem_python

echo --------------------------------------------------------------
echo  Interpretador encontrado:
%PY% --version
echo --------------------------------------------------------------
echo.

echo [1/3] Atualizando o pip...
%PY% -m pip install --upgrade pip
echo.

echo [2/3] Instalando as bibliotecas...
%PY% -m pip install pyserial pandas matplotlib schedule Pillow customtkinter paho-mqtt
if errorlevel 1 goto erro
echo.

echo [3/3] Verificando a instalacao...
%PY% -c "import serial, pandas, matplotlib, schedule, PIL, customtkinter, paho.mqtt.client; print('OK - todas as bibliotecas foram importadas com sucesso.')"
if errorlevel 1 goto erro

echo.
echo ==============================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO
echo ==============================================================
goto fim

:sem_python
echo ==============================================================
echo    ERRO: Python nao foi encontrado neste computador.
echo ==============================================================
echo.
echo  Instale o Python a partir de https://www.python.org/downloads/
echo  IMPORTANTE: marque a opcao "Add Python to PATH" durante a
echo  instalacao e depois execute este arquivo novamente.
goto fim

:erro
echo.
echo ==============================================================
echo    ERRO durante a instalacao - leia as mensagens acima.
echo ==============================================================
echo.
echo  Dicas:
echo   - verifique a conexao com a internet;
echo   - se houver erro de permissao, clique com o botao direito
echo     neste arquivo e escolha "Executar como administrador".

:fim
echo.
pause
endlocal
