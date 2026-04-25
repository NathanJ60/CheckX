@echo off
echo ============================================
echo    Compilation Check 10 pour Windows
echo ============================================
echo.

REM Nettoyage
echo Nettoyage des anciens builds...
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul
del /Q *.spec 2>nul
echo.

REM Compilation
echo Compilation en cours...
py -m PyInstaller --onefile --windowed ^
    --add-data "check10_model.py;." ^
    --add-data "check10_visualization.py;." ^
    --add-data "check10_model_history.py;." ^
    --add-data "check_unique_check10.py;." ^
    --collect-all ortools ^
    --collect-all PyQt5 ^
    --collect-all PIL ^
    --collect-all reportlab ^
    --collect-all svgwrite ^
    --hidden-import check10_model ^
    --hidden-import check10_visualization ^
    --hidden-import check10_model_history ^
    --hidden-import check_unique_check10 ^
    --hidden-import ortools ^
    --hidden-import ortools.sat ^
    --hidden-import ortools.sat.python ^
    --hidden-import ortools.sat.python.cp_model ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import PIL.ImageFont ^
    --hidden-import svgwrite ^
    --hidden-import reportlab ^
    --name Check10Builder ^
    check10_gui.py

echo.
if exist dist\Check10Builder.exe (
    echo ============================================
    echo    SUCCES ! Executable cree :
    echo    dist\Check10Builder.exe
    echo ============================================
    powershell -command "Write-Host ('Taille : ' + [math]::Round((Get-Item dist\Check10Builder.exe).Length / 1MB, 1) + ' MB')"
) else (
    echo ============================================
    echo    ECHEC de la compilation
    echo ============================================
)
echo.
pause
