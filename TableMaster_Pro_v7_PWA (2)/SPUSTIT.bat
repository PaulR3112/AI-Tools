@echo off
REM ============================================================
REM  TableMaster Pro v7 - Spustit ako desktop aplikaciu
REM ============================================================

REM Cesta k HTML suboru (offline verzia v rovnakom adresari)
set "HTML_FILE=%~dp0index.offline.html"

REM Skontrolujem ci HTML existuje
if not exist "%HTML_FILE%" (
    echo CHYBA: Nenasiel som "%HTML_FILE%"
    echo Tento BAT subor musi byt v rovnakom adresari ako index.offline.html
    pause
    exit /b 1
)

REM ============================================================
REM Hladam Chrome / Edge / Brave - postupne kontrolujem cesty
REM ============================================================

set "BROWSER="

REM Chrome - lokalna instalacia (per-user)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Chrome - Program Files
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Chrome - Program Files x86
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Edge - Program Files x86 (default location)
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
    goto :found
)

REM Edge - Program Files
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
    goto :found
)

REM Brave - lokalna instalacia
if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" (
    set "BROWSER=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
    goto :found
)

REM Brave - Program Files
if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" (
    set "BROWSER=%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"
    goto :found
)

REM Ak prehliadac nebol najdeny
echo CHYBA: Nenasiel som ziadny podporovany prehliadac
echo Aplikacia potrebuje Chrome, Edge alebo Brave
echo.
echo Skontroloval som nasledovne cesty:
echo  - %LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
echo  - %ProgramFiles%\Google\Chrome\Application\chrome.exe
echo  - %ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
echo  - %ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
echo  - %ProgramFiles%\Microsoft\Edge\Application\msedge.exe
echo.
echo Stiahnite si Chrome z: https://www.google.com/chrome/
pause
exit /b 1

:found
REM ============================================================
REM Spustim aplikaciu ako "app" - bez adresneho riadku
REM ============================================================

echo Spustam TableMaster Pro v7 ako aplikaciu...
echo Prehliadac: %BROWSER%

REM Konvertujem cestu k HTML suboru na file:// URL
set "URL=file:///%HTML_FILE:\=/%"

start "" "%BROWSER%" --app="%URL%" --window-size=1400,900

REM Pockam moment a zatvorim - aplikacia bezi v pozadi
timeout /t 1 /nobreak >nul
exit /b 0
