@echo off
setlocal enabledelayedexpansion
echo ======================================================
echo   RIMOZIONE CARTELLE __pycache__ IN CORSO
echo ======================================================
echo.

rem Imposta il file di log nella cartella corrente
set LOGFILE=%~dp0pycache_cleanup_log.txt
echo Log file: %LOGFILE%
echo ====================================================== > "%LOGFILE%"
echo Operazione avviata il %date% alle %time% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo Eliminazione cartella: %%d
        echo Eliminazione cartella: %%d >> "%LOGFILE%"
        rd /s /q "%%d"
    )
)

echo. >> "%LOGFILE%"
echo Operazione completata il %date% alle %time% >> "%LOGFILE%"
echo ====================================================== >> "%LOGFILE%"

echo.
echo Tutte le cartelle __pycache__ sono state rimosse.
echo Dettagli salvati in: %LOGFILE%
pause