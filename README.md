# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together. It is used by loading (and forgetting about) `start_tracking.py`, and using `generate_images.py` to create the images. All the calculations are done in a background process, so that the tracking part will be able to run constantly without any CPU spikes interfering with it.

<b>Current Features</b>:
 - Track position, clicks and key presses over multiple resolutions
 - Generate colourful mouse tracks and a heatmap of clicks
 - Fade old mouse tracks to keep recent tracks more visible
 - Automatically keep separate tracks for different applications (defined in "Program List.txt")
 - Edit settings with config.ini
 - Works fully on Windows and mostly on Linux
 
<b>Known Issues:</b>
 - (Windows) The keyboard tracking doesn't work on certain applications
 - Only tracks the main monitor (this was mostly a design choice)
 
 <b>Help Needed:</b>
 - Help decide on a more interesting name than "Mouse Tracks"
 - Mac support
 - Linux keyboard tracking
 
 <b>To Do List:</b>
 - Add more optional variables to image name
 - Write more robust code to save the image (so it doesn't crash if the folder doesn't exist)
 - Improved path options (to allow things like %APPDATA% to be used)
 - Add min/max values to config validation
 - Export raw data for others to visualize
 - Move AFK detection to background process, since in a rare case queued commands may not get saved
 - Save new image every x minutes to be used in a sequence
 - Simple analytics (with option to turn off)

 
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
<br/>FPS:
<img src="http://i.imgur.com/Iocmy3N.jpg">
<img src="http://i.imgur.com/ii3mhBA.jpg">
<br/>RTS:
<img src="http://i.imgur.com/FSeAHYK.jpg">
<img src="http://i.imgur.com/Ct8A3tK.jpg">
<br/>MOBA:
<img src="http://i.imgur.com/X34ZrwQ.jpg">
<img src="http://i.imgur.com/Y5tttVN.jpg">
