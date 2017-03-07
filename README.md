# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions, and merging them together. It is used by loading (and forgetting about) `start.py`, and using `generate_images.py` to create the images. Currently it only works on windows as it uses `win32api` to get all the information.

The next planned feature is to split the files for different applications, and check for screen changes. Currently the resolution and refresh rate is determined as the file is loaded, so changing anything will result in wrong coordinates.
