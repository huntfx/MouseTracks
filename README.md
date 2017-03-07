# MouseTrack (WIP)

Track and display mouse movements/clicks over time. Old movements will get faded so it can be left running indefinitely.

This was made with the intention of recording mouse movements over multiple resolutions then merging them together, since Razer Synapse tends to get artefacts. It is used by loading (and forgetting about) `start.py`, and using `generate_images.py` to create the images. Currently it only works on windows as it uses `win32api` to get all the information.

<b>Current Features</b>:
 - Track movement, clicks and key presses
 - Display movement history and click heatmap
 - Fade out movement history to keep recent tracks more visible
 - Set colours of movement history
 
<b>Planned Features:</b>
 - Track separately for different applications (switch needs to be instant but may need to load a large file and merge results)
 - Check for any changes in resolution/refresh rate and update accordingly
 - Possibly phase out refresh rate and keep it to 60 UPS
 
<b>Example Output:</b>
<img src="http://i.imgur.com/rsugV3F.jpg">

<img src="http://i.imgur.com/XuEY8yg.jpg">
