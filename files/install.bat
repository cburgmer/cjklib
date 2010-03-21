@echo off

:initial
if "%1"=="all" goto all
if "%1"=="EDICT" goto edict
if "%1"=="edict" goto edict
if "%1"=="CEDICT" goto cedict
if "%1"=="cedict" goto cedict
if "%1"=="CEDICTGR" goto cedictgr
if "%1"=="cedictgr" goto cedictgr
if "%1"=="HanDeDict" goto handedict
if "%1"=="handedict" goto handedict
if "%1"=="CFDICT" goto cfdict
if "%1"=="cfdict" goto cfdict
if "%1"=="" goto done
goto error


:edict
mkdir build\tmp
python downloaddict.py EDICT --targetName=build\tmp\edict.gz

python -m cjklib.build.cli -r build EDICT --filePath=build\tmp\edict.gz --database=sqlite:///build/edict.db --attach=

echo Installing to "%APPDATA%\cjklib" ..
mkdir "%APPDATA%\cjklib"
move build/edict.db "%APPDATA%\cjklib"

goto return


:cedict
mkdir build\tmp
python downloaddict.py CEDICT --targetName=build\tmp\cedict.gz

python -m cjklib.build.cli -r build CEDICT --filePath=build\tmp\cedict.gz --database=sqlite:///build/cedict.db --attach=

echo Installing to "%APPDATA%\cjklib" ..
mkdir "%APPDATA%\cjklib"
move build/cedict.db "%APPDATA%\cjklib"

goto return


:cedictgr
mkdir build\tmp
python downloaddict.py CEDICTGR --targetName=build\tmp\cedictgr.zip

python -m cjklib.build.cli -r build CEDICTGR --filePath=build\tmp\cedictgr.zip --database=sqlite:///build/cedictgr.db --attach=

echo Installing to "%APPDATA%\cjklib" ..
mkdir "%APPDATA%\cjklib"
move build/cedictgr.db "%APPDATA%\cjklib"

goto return


:handedict
mkdir build\tmp
python downloaddict.py HanDeDict --targetName=build\tmp\handedict.tar.bz2

python -m cjklib.build.cli -r build HanDeDict --filePath=build\tmp\handedict.tar.bz2 --database=sqlite:///build/handedict.db --attach=

echo Installing to "%APPDATA%\cjklib" ..
mkdir "%APPDATA%\cjklib"
move build/handedict.db "%APPDATA%\cjklib"

goto return


:cfdict
mkdir build\tmp
python downloaddict.py CFDICT --targetName=build\tmp\cfdict.tar.bz2

python -m cjklib.build.cli -r build CFDICT --filePath=build\tmp\cfdict.tar.bz2 --database=sqlite:///build/cfdict.db --attach=

echo Installing to "%APPDATA%\cjklib" ..
mkdir "%APPDATA%\cjklib"
move build/cfdict.db "%APPDATA%\cjklib"

goto return


:all
call install.bat edict cedict cedictgr handedict cfdict
goto done


:return
shift
call install.bat %1 %2 %3 %4 %5 %6
goto done


:error
echo %0 unknown dictionary
echo Specify a dictionary out of EDICT, CEDICT, CEDICTGR, HanDeDict, CFDICT
echo to build and install, e.g. install.bat CEDICT.
goto done


:done
echo Done
