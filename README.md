# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together. It is used by loading (and forgetting about) `__init__.py`, and using `generate_images.py` to create the images. All the calculations are done in a background process so that the tracking part will run constantly without any CPU spikes.

<b>Current Features</b>:
 - Track position, speed, both combined, clicks and key presses over multiple resolutions
 - Display mouse tracks, mouse speed and click heatmap
 - Fade old mouse tracks to keep recent tracks more visible
 - Change colours used to generate the images
 - Automatically keep separate tracks for different applications defined in "Program List.txt"
 - Edit settings with config.ini
 
<b>Known Issues:</b>
 - (Windows) The keyboard stops being properly detected during full screen games
 - (Linux) No support yet
 - (Mac) No support yet
 - (All) Image generation will crash if folder doesn't exist
 
 <b>To Do List:</b>
  - Redesign colour map code to work with small ranges
  - Detect if .data.old is more recent than .data and load that instead
  - Add more optional variables to image name
  - Write more robust code to save the image
  - Add min/max values to config validation
  - Export raw data for others to visualize
  - Write a few extra functions to make it easier to use the `Config` class
 
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
