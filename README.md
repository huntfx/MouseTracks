# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together. It is used by loading (and forgetting about) `start_tracking.py`, and using `generate_images.py` to create the images. All the calculations are done in a background process, so that the tracking part will be able to run constantly without any CPU spikes interfering with it.

<b>Current Features</b>:
 - Track position, speed, both combined, clicks and key presses over multiple resolutions
 - Display mouse tracks, mouse speed and click heatmap
 - Fade old mouse tracks to keep recent tracks more visible
 - Change colours used to generate the images
 - Automatically keep separate tracks for different applications defined in "Program List.txt"
 - Edit settings with config.ini
 
<b>Known Issues (that I can't personally fix):</b>
 - (Windows) The keyboard stops being properly detected during full screen games
 - (Linux) No support yet, but it's being worked on by Isometries
 - (Mac) No support
 
 <b>To Do List:</b>
 - Find a nice reduction value for the speed and combined maps
 - Detect if .data.old is more recent than .data and load that instead
 - Add more optional variables to image name
 - Write more robust code to save the image (so it doesn't crash if the folder doesn't exist)
 - Improved path options (to allow things like %APPDATA% to be used)
 - Add min/max values to config validation
 - Export raw data for others to visualize
 - Move AFK detection to background process, since queued commands may not get saved
 
<b>Example Output:</b>
<img src="http://i.imgur.com/rsugV3F.jpg">
<img src="http://i.imgur.com/XuEY8yg.jpg">

<b>Colour Maps:</b>
<br/>Default:
<img src="http://i.imgur.com/lTCByLO.png">
<br/>Chalk:
<img src="http://i.imgur.com/R8BDVyH.jpg">
<br/>LimeZest:
<img src="http://i.imgur.com/IFEneWZ.jpg">
<br/>Sunburst:
<img src="http://i.imgur.com/AN1CYPD.jpg">
<br/>Ice:
<img src="http://i.imgur.com/mXAEV1G.jpg">
<br/>Hazard:
<img src="http://i.imgur.com/QftEuAF.png">
<br/>Street:
<img src="http://i.imgur.com/IlMHRgg.jpg">
<br/>Lightning:
<img src="http://i.imgur.com/O4iqFau.png">
<br/>Razer:
<img src="http://i.imgur.com/jxfdWJq.png">
<br/>Grape:
<img src="http://i.imgur.com/rye5VAw.png">
<br/>Neon:
<img src="http://i.imgur.com/FAVmiK1.png">
