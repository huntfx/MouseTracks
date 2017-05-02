# MouseTrack

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together. It is used by loading (and forgetting about) `__init__.py`, and using `generate_images.py` to create the images. All the calculations are done in a background process so that the tracking part shouldn't ever take a performance hit. Currently it only works on windows as it uses `pywin32` to get all the information, though it would be easy to add support for another operating system.

<b>Current Features</b>:
 - Track movement, clicks and key presses, over multiple resolutions
 - Display mouse tracks and click heatmap
 - Fade old mouse tracks to keep recent tracks more visible
 - Change colours used to generate tracks and heatmap
 - Keep separate tracks for different applications defined in "Program List.txt"
 - Edit settings with config.ini
 
<b>Known Issues:</b>
 - They keyboard stops being properly detected during full screen games.
 - No support (yet) for Linux or Mac
 
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
