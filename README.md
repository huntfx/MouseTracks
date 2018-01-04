# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together. It is used by loading (and forgetting about) `start_tracking.py`, and using `generate_images.py` to create the images. All the calculations are done in a background process, so that the tracking part will be able to run constantly without any CPU heavy calculations interfering with it.

By default, the tracking area is limited to the application window, but with no application detected, all monitors will be used, and merged over each other.

<b>Current Features:</b>
 - Track position, clicks, key presses and gamepad usage over multiple resolutions and monitors
 - Generate colourful mouse tracks and a heatmap of clicks and key presses (for everything or just the latest session)
 - Fade old mouse tracks to keep recent tracks more visible
 - Record and adjust resolution based on the currently focused window
 - Automatically keep separate tracks for different applications (defined in "AppList.txt")
 - Perodically update AppList.txt from the internet, keeping and sorting all the old values, and adding any new ones
 - Edit settings with config.ini
 - Full Windows support
 - Some Linux support (WIP)
 - Some Mac support (WIP)
 
<b>Example Output:</b>
<img src="http://i.imgur.com/UJgf0up.jpg">
<img src="http://i.imgur.com/HL023Cr.jpg">

<b>Colour Maps:</b>
<br/>Chalk:
<img src="http://i.imgur.com/ReRbDnF.jpg">
<br/>Citrus:
<img src="http://i.imgur.com/wRRsFhn.jpg">
<br/>Demon:
<img src="http://i.imgur.com/IDLRgGn.jpg">
<br/>Sunburst:
<img src="http://i.imgur.com/HtVF8In.jpg">
<br/>Ice:
<img src="http://i.imgur.com/KniZy9q.jpg">
<br/>Hazard:
<img src="http://i.imgur.com/zy9v3in.jpg">
<br/>Spiderman:
<img src="http://i.imgur.com/CwGlzfa.jpg">
<br/>Sketch:
<img src="http://i.imgur.com/z1s0iTg.jpg">
<br/>Lightning:
<img src="http://i.imgur.com/yB5udPO.jpg">
<br/>Razer:
<img src="http://i.imgur.com/Xfu0i8E.jpg">
<br/>BlackWidow:
<img src="http://i.imgur.com/1AqOHxC.jpg">
<br/>Grape:
<img src="http://i.imgur.com/fcOji6t.jpg">
<br/>Neon:
<img src="http://i.imgur.com/hd8oshz.jpg">
<br/>Shroud:
<img src="http://i.imgur.com/HmP4kSJ.jpg">

<b>Game Genres:</b>
<br/>Twin Stick:
<img src="http://i.imgur.com/mjxqbg0.png">
<img src="http://i.imgur.com/ZxBoz0i.jpg">
<img src="http://i.imgur.com/rikwsUa.jpg">
<br/>FPS:
<img src="http://i.imgur.com/Iocmy3N.jpg">
<img src="http://i.imgur.com/ii3mhBA.jpg">
<br/>RTS:
<img src="http://i.imgur.com/FSeAHYK.jpg">
<img src="http://i.imgur.com/Ct8A3tK.jpg">
<br/>MOBA:
<img src="http://i.imgur.com/X34ZrwQ.jpg">
<img src="http://i.imgur.com/Y5tttVN.jpg">

<b>Requirements:</b>
 - [Numpy](https://pypi.python.org/pypi/numpy)
 - [psutil](https://pypi.python.org/pypi/psutil)
 - [Pillow](https://pypi.python.org/pypi/Pillow) (required to generate images)
 - [scipy](https://pypi.python.org/pypi/scipy) (required to generate images) - included in code for Windows only
 - [pywin32](https://sourceforge.net/projects/pywin32/files/pywin32) (optional - preferred method of Windows tracking)
 - [AppKit](https://pypi.python.org/pypi/AppKit/0.2.8) (required for Mac tracking)
 - [xlib](https://pypi.python.org/pypi/python-xlib) (required for Linux tracking)
 - [Flask](http://flask.pocoo.org/) (required for web based API)
 - ~~[pyxhook](https://github.com/JeffHoogland/pyxhook/blob/master/pyxhook.py) (required for Linux tracking)~~ - included in code
 - ~~[pyglet](https://pypi.python.org/pypi/pyglet/1.3.0)~~ - included in code
 - ~~[xinput](https://github.com/r4dian/Xbox-360-Controller-for-Python/blob/master/xinput.py) (required for gamepad tracking (Windows only))~~ - included in code
