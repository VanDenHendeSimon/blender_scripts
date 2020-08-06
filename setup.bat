:: Elevate this script, because it needs admin user
(
    :: Check Admin rights and create VBS Script to elevate
    >nul fsutil dirty query %SYSTEMDRIVE% 2>&1 || (

        :: Create VBS script
        echo Set UAC = CreateObject^("Shell.Application"^)>"%TEMP%\elevate.vbs"
        echo UAC.ShellExecute "%~f0", "%TEMP%\elevate.vbs", "", "runas", 1 >>"%TEMP%\elevate.vbs"
        if exist "%TEMP%\elevate.vbs" start /b /wait >nul cscript /nologo "%TEMP%\elevate.vbs" 2>&1

        :: Delete elevation script if exist
        if exist "%TEMP%\elevate.vbs" >nul del /f "%TEMP%\elevate.vbs" 2>&1

        exit /b
    )    
)

pushd "%~dp0"
echo Starting setup... > setup.log

:: Detect supported Blender installation(s)
set list=2.81 2.82 2.83

for %%a in (%list%) do (
	:: Check if the version of blender exists
	IF EXIST "C:\Program Files\Blender Foundation\Blender %%a\%%a\scripts\startup\" (
		echo Found installation of Blender %%a >> setup.log
		:: Copy the files to the startup folder
		xcopy /f /y /r /c /e /s /i "%CD%\PromptoBlenderRepository" "C:\Program Files\Blender Foundation\Blender %%a\%%a\scripts\startup\PromptoBlenderRepository" >> setup.log
		echo f | xcopy /f /y /r /c "%CD%\blender_import_unreal_scene.py" "C:\Program Files\Blender Foundation\Blender %%a\%%a\scripts\startup\blender_import_unreal_scene.py" >> setup.log
		echo f | xcopy /f /y /r /c "%CD%\export_blendfile_to_shapespark.py" "C:\Program Files\Blender Foundation\Blender %%a\%%a\scripts\startup\export_blendfile_to_shapespark.py" >> setup.log
		echo f | xcopy /f /y /r /c "%CD%\generate_shapespark_import_data.py" "C:\Program Files\Blender Foundation\Blender %%a\%%a\scripts\startup\generate_shapespark_import_data.py" >> setup.log

	)	ELSE (
		:: Not really required but could help to determine whether or not any Blender installation is found by the batch script
		echo Could not find installation of Blender %%a >> setup.log
	)
)
