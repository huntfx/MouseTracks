python -m virtualenv env
.\env\Scripts\pip.exe install numpy
.\env\Scripts\pip.exe install psutil
.\env\Scripts\pip.exe install pillow
.\env\Scripts\pip.exe install pywin32
.\env\Scripts\pip.exe install crypto
.\env\Scripts\pip.exe install flask
.\env\Scripts\pip.exe install scipy
echo..\env\scripts\python start_tracking.py>start_tracking.bat
echo..\env\scripts\python generate_images.py>generate_images.bat