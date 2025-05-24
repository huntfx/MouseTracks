# MouseTracks

MouseTracks is an application designed to track and visualize mouse movements, clicks, keyboard activity, and gamepad inputs over time. It's designed to be unobtrusive, allowing you to leave it running indefinitely - even for years - and return later to render colourful visualisations of the data.

<img src="media/gui.jpg">

## Features

- ### Live Tracking:
  Continuously monitors mouse movements and clicks, with older movements gradually fading out to maintain a clear view of recent activity.

  Keyboard heatmaps and gamepad inputs are also supported.

- ### Live Preview
  The GUI includes an optimised real-time preview of tracking data, combining thumbnail renders with live input.

- ### Image Rendering:
  Renders are generated at full quality, regardless of resolution changes. Each input type is tracked independently and merged during the render process.

  - Mouse and gamepad thumbsticks: Track maps and position heatmaps.

  - Mouse clicks: Heatmaps.

  - Key presses: Heatmap overlaid on a keyboard image.

  - _(Gamepad rendering is not yet supported.)_

- ### Colourful Renders:
  Includes predefined and customizable color maps for all render types.

- ### Application Tracking:
  Use separate tracking profiles depending on which application has focus.

  _(New applications must be added via the GUI.)_

- ### Multi-Monitor Support:
  Tracks activity across multiple monitors. If linked to a specific application, the rendering bounds will automatically adjust to the application's window geometry.

- ### Unobtrusive:
  Designed to run silently in the background. The GUI can be hidden to the System Tray, which also removes the processing overhead of showing all the live data.

- ### Modular Design:
  The application was designed with multiple components that communicate but run independenantly of each other, ensuring the live tracking remains fully stable, even during resource-intensive tasks like rendering or waiting on GUI operations.

- ### Stability
  Will happily keep running for years without any issues.

MouseTracks is and will always remain free, but if you enjoy using it and would like to [buy me a pint](https://www.paypal.me/PeterHunt999) in appreciation (as I don't like coffee), then that would be very kind.

---

## Installation (v2.0)

_Currently, only Windows is supported. Contributions for Linux or macOS support are welcome._

### Prebuilt Executable

Launch `MouseTracks.exe` from anywhere. Recommended for ease of use.

Build it using [`build-pyinstaller.bat`](build-pyinstaller.bat), or download it from the releases.

It's also possible to run [`build-nuitka.bat`](build-nuitka.bat), but this is not recommended unless you have a commercial license, as it will be flagged by a lot of AV programs.


### Virtual Environment

Recommended if running the code locally.

1. Run `python -m venv .venv` to create the virtual environment with Python 3.11 or above.
2. Run `launch.bat`.


### Without a Virtual Environment

Run `launch.py`.

Ensure all modules in [requirements.txt](requirements.txt) are installed.

---

## Installation (v1.0 - Deprecated)

_The v1.0 version is no longer supported, but the launch process has been updated to bring it in line with v2.0._

You will be prompted with a choice to start tracking or generate images. This can be skipped by passing the `--start-tracking` or `--generate-images` flags.

### Virtual Environment

Recommended if running the code locally.

1. Run `python -m venv .venv-legacy` to create the virtual environment with any version of Python.
2. Run `launch-legacy.bat`.


### Without a Virtual Environment

Run `launch-legacy.py`.

Ensure all modules in [requirements-legacy.txt](requirements-legacy.txt) are installed.

---

## Example Output
<img src="http://i.imgur.com/UJgf0up.jpg">
<img src="http://i.imgur.com/HL023Cr.jpg">

### Colour Maps
#### Chalk
<img src="http://i.imgur.com/ReRbDnF.jpg">

#### Citrus
<img src="http://i.imgur.com/wRRsFhn.jpg">

#### Demon
<img src="http://i.imgur.com/IDLRgGn.jpg">

#### Sunburst
<img src="http://i.imgur.com/HtVF8In.jpg">

#### Ice
<img src="http://i.imgur.com/KniZy9q.jpg">

#### Hazard
<img src="http://i.imgur.com/zy9v3in.jpg">

#### Spiderman
<img src="http://i.imgur.com/CwGlzfa.jpg">

#### Graffiti
<img src="http://i.imgur.com/z1s0iTg.jpg">

#### Lightning
<img src="http://i.imgur.com/yB5udPO.jpg">

#### Razer
<img src="http://i.imgur.com/Xfu0i8E.jpg">

#### BlackWidow
<img src="http://i.imgur.com/1AqOHxC.jpg">

#### Grape
<img src="http://i.imgur.com/fcOji6t.jpg">

#### Neon
<img src="http://i.imgur.com/hd8oshz.jpg">

#### Shroud
<img src="http://i.imgur.com/HmP4kSJ.jpg">

## Game Genres
#### Twin Stick
<img src="http://i.imgur.com/mjxqbg0.png">
<img src="http://i.imgur.com/ZxBoz0i.jpg">
<img src="http://i.imgur.com/rikwsUa.jpg">

#### FPS
<img src="http://i.imgur.com/Iocmy3N.jpg">
<img src="http://i.imgur.com/ii3mhBA.jpg">

#### RTS
<img src="http://i.imgur.com/FSeAHYK.jpg">
<img src="http://i.imgur.com/Ct8A3tK.jpg">

#### MOBA
<img src="http://i.imgur.com/X34ZrwQ.jpg">
<img src="http://i.imgur.com/Y5tttVN.jpg">

## Data Privacy
All data recorded or generated by the application is stored locally on your computer. You have full control over this data, including the ability to change the storage location, export your data, and delete it.

MouseTracks does not transmit any of your personal data or usage information over the internet - the only connection made is to check for updates, and this can be completely disabled with the `--offline` flag if required.
