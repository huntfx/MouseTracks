pyinstaller start_tracking.py --name "Start Tracking" --exclude-module Tkinter
pyinstaller generate_images.py --name "Generate Images" --exclude-module Tkinter
pyinstaller get_stats.py --name "Get Stats" --exclude-module Tkinter
python _build.py "Build/Mouse Tracks" "dist/Start Tracking" "dist/Generate Images" "dist/Get Stats"
