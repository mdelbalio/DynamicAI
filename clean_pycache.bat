@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Pulizia Cache Python Completa

echo ======================================================
echo   PULIZIA COMPLETA CACHE PYTHON
echo ======================================================
echo.
echo Operazioni da eseguire:
echo   [1] Rimozione cartelle __pycache__
echo   [2] Rimozione file .pyc
echo   [3] Rimozione file .pyo (Python ottimizzati)
echo   [4] Rimozione file .pyd (estensioni compilate)
echo ======================================================
echo.

rem Imposta il file di log nella cartella corrente
set LOGFILE=%~dp0python_cleanup_log.txt
set COUNTER_DIRS=0
set COUNTER_PYC=0
set COUNTER_PYO=0
set COUNTER_PYD=0

echo Log file: %LOGFILE%
echo.

rem Inizializza log
echo ====================================================== > "%LOGFILE%"
echo PULIZIA COMPLETA CACHE PYTHON >> "%LOGFILE%"
echo ====================================================== >> "%LOGFILE%"
echo Operazione avviata: %date% - %time% >> "%LOGFILE%"
echo Directory: %CD% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

rem ========================================
rem 1. RIMOZIONE CARTELLE __pycache__
rem ========================================
echo [1/4] Rimozione cartelle __pycache__...
echo. >> "%LOGFILE%"
echo [FASE 1] CARTELLE __pycache__ >> "%LOGFILE%"
echo ---------------------------------------- >> "%LOGFILE%"

for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo   Eliminazione: %%d
        echo   Eliminazione: %%d >> "%LOGFILE%"
        rd /s /q "%%d" 2>nul
        if !errorlevel! equ 0 (
            set /a COUNTER_DIRS+=1
        ) else (
            echo   [ERRORE] Impossibile eliminare: %%d >> "%LOGFILE%"
        )
    )
)

echo   Totale cartelle rimosse: !COUNTER_DIRS!
echo   Totale cartelle rimosse: !COUNTER_DIRS! >> "%LOGFILE%"
echo.

rem ========================================
rem 2. RIMOZIONE FILE .pyc
rem ========================================
echo [2/4] Rimozione file .pyc...
echo. >> "%LOGFILE%"
echo [FASE 2] FILE .pyc (Bytecode Compilato) >> "%LOGFILE%"
echo ---------------------------------------- >> "%LOGFILE%"

for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        echo   Eliminazione: %%f
        echo   Eliminazione: %%f >> "%LOGFILE%"
        del /f /q "%%f" 2>nul
        if !errorlevel! equ 0 (
            set /a COUNTER_PYC+=1
        ) else (
            echo   [ERRORE] Impossibile eliminare: %%f >> "%LOGFILE%"
        )
    )
)

echo   Totale file .pyc rimossi: !COUNTER_PYC!
echo   Totale file .pyc rimossi: !COUNTER_PYC! >> "%LOGFILE%"
echo.

rem ========================================
rem 3. RIMOZIONE FILE .pyo (Ottimizzati)
rem ========================================
echo [3/4] Rimozione file .pyo...
echo. >> "%LOGFILE%"
echo [FASE 3] FILE .pyo (Bytecode Ottimizzato) >> "%LOGFILE%"
echo ---------------------------------------- >> "%LOGFILE%"

for /r . %%f in (*.pyo) do (
    if exist "%%f" (
        echo   Eliminazione: %%f
        echo   Eliminazione: %%f >> "%LOGFILE%"
        del /f /q "%%f" 2>nul
        if !errorlevel! equ 0 (
            set /a COUNTER_PYO+=1
        ) else (
            echo   [ERRORE] Impossibile eliminare: %%f >> "%LOGFILE%"
        )
    )
)

echo   Totale file .pyo rimossi: !COUNTER_PYO!
echo   Totale file .pyo rimossi: !COUNTER_PYO! >> "%LOGFILE%"
echo.

rem ========================================
rem 4. RIMOZIONE FILE .pyd (Estensioni)
rem ========================================
echo [4/4] Rimozione file .pyd (opzionale)...
echo. >> "%LOGFILE%"
echo [FASE 4] FILE .pyd (Estensioni Compilate) >> "%LOGFILE%"
echo ---------------------------------------- >> "%LOGFILE%"
echo ATTENZIONE: File .pyd potrebbero essere necessari! >> "%LOGFILE%"
echo.

set /p REMOVE_PYD="Rimuovere anche file .pyd? (S/N): "
if /i "!REMOVE_PYD!"=="S" (
    for /r . %%f in (*.pyd) do (
        if exist "%%f" (
            echo   Eliminazione: %%f
            echo   Eliminazione: %%f >> "%LOGFILE%"
            del /f /q "%%f" 2>nul
            if !errorlevel! equ 0 (
                set /a COUNTER_PYD+=1
            ) else (
                echo   [ERRORE] Impossibile eliminare: %%f >> "%LOGFILE%"
            )
        )
    )
    echo   Totale file .pyd rimossi: !COUNTER_PYD!
    echo   Totale file .pyd rimossi: !COUNTER_PYD! >> "%LOGFILE%"
) else (
    echo   File .pyd NON rimossi (utente ha scelto NO)
    echo   File .pyd NON rimossi (utente ha scelto NO) >> "%LOGFILE%"
)
echo.

rem ========================================
rem RIEPILOGO FINALE
rem ========================================
echo. >> "%LOGFILE%"
echo ====================================================== >> "%LOGFILE%"
echo RIEPILOGO OPERAZIONE >> "%LOGFILE%"
echo ====================================================== >> "%LOGFILE%"
echo Cartelle __pycache__ rimosse: !COUNTER_DIRS! >> "%LOGFILE%"
echo File .pyc rimossi: !COUNTER_PYC! >> "%LOGFILE%"
echo File .pyo rimossi: !COUNTER_PYO! >> "%LOGFILE%"
echo File .pyd rimossi: !COUNTER_PYD! >> "%LOGFILE%"
set /a TOTAL_ITEMS=!COUNTER_DIRS!+!COUNTER_PYC!+!COUNTER_PYO!+!COUNTER_PYD!
echo TOTALE ELEMENTI RIMOSSI: !TOTAL_ITEMS! >> "%LOGFILE%"
echo. >> "%LOGFILE%"
echo Operazione completata: %date% - %time% >> "%LOGFILE%"
echo ====================================================== >> "%LOGFILE%"

echo ======================================================
echo   OPERAZIONE COMPLETATA CON SUCCESSO!
echo ======================================================
echo.
echo Riepilogo:
echo   - Cartelle __pycache__: !COUNTER_DIRS!
echo   - File .pyc: !COUNTER_PYC!
echo   - File .pyo: !COUNTER_PYO!
echo   - File .pyd: !COUNTER_PYD!
echo   ----------------------------------------
echo   TOTALE: !TOTAL_ITEMS! elementi rimossi
echo.
echo Log salvato in: %LOGFILE%
echo ======================================================
echo.
pause