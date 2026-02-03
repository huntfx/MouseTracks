# MouseTracks

MouseTracks is an application designed to track and visualize mouse movements, clicks, keyboard activity, and gamepad inputs over time. It's designed to be unobtrusive, allowing you to leave it running indefinitely - even for years - and return later to render colourful visualisations of the data.

<img src="media/gui.jpg">

Questions? Check out the [FAQ](https://github.com/huntfx/MouseTracks/wiki#faq), or [raise an issue](https://github.com/huntfx/MouseTracks/issues) if you can't find an answer.

MouseTracks is and will always remain free, but if you enjoy using it and would like to [buy me a pint](https://ko-fi.com/huntfx) in appreciation (as I don't like coffee), then that would be very kind.

---

## Featured On

> _"Peter Hunt has taken r/dataisbeautiful by storm by dropping some incredible heatmaps tracking his mouse movements."._
>
> — **[Motherboard - VICE](https://www.vice.com/en/article/these-trippy-heatmaps-show-the-differences-between-fps-and-rts-games/)**, May 2017

> _"MouseTracks turns your everyday clicks, moves, and key presses into a kind of digital diary. You can watch heatmaps of where your mouse spends the most time, see just how much you actually type, or even compare your gaming sessions over weeks or years. It’s like getting a quirky little behind-the-scenes replay of how you really use your PC.<br>Oddly addictive."_
>
> — **[MajorGeeks Newsletter](https://mailchi.mp/majorgeeks/majorgeeks-newsletter-september-2025)**, September 2025

---

## Features

- ### Live Tracking
  Continuously monitors mouse movements and clicks. Older movements gradually fade, keeping the view focused on recent activity.

  Keyboard heatmaps and gamepad inputs are also supported.

- ### Live Preview
  The GUI displays an optimised real-time render of tracking data.

- ### Image Rendering
  Renders are generated at full quality, regardless of resolution changes. Each resolution is tracked independently and merged during the render process.

  - Mouse and gamepad thumbsticks: Track maps and position heatmaps.

  - Mouse clicks: Heatmaps.

  - Key presses: Heatmap overlaid on a keyboard image.

  - _(Gamepad rendering is not yet supported.)_

- ### Colourful Renders
  Includes predefined colour maps for all render types, with the option to customise or create your own.

- ### Application Tracking
  Use separate tracking profiles depending on which application has focus.

  _(New applications must be added via the GUI.)_

- ### Multi-Monitor Support
  Tracks activity across multiple monitors. If linked to a specific application, the rendering bounds will automatically adjust to the application's window geometry.

- ### Unobtrusive
  Designed to run silently in the background. It can be configured to launch on startup and minimise directly to the System Tray.

- ### Modular Design
  The application was designed with multiple components that communicate but run independently of each other, ensuring the live tracking remains fully stable, even during resource intensive tasks like rendering or waiting on GUI operations.

- ### Stability
  A lot of effort has been put into making this as error free as possible, so it will happily keep running for years without any issues.

---

## Installation (v2.0)

- Fully compatible with Windows.
- Compatible with Linux.

_On Linux, MouseTracks requires an __X11 (Xorg)__ session to work. On modern distributions like Ubuntu, you may need to select "Ubuntu on Xorg" from the gear icon on the login screen._

---

### Download the Prebuilt Executable (Recommended)

This is the simplest way to get started. No installation is required.

1. Go to the [latest release](https://github.com/huntfx/MouseTracks/releases/latest) page.
2. Download the appropriate file for your system (eg. `MouseTracks-2.0.0-windows-x64.exe`).
3. If on Linux, make the file executable: `chmod +x MouseTracks-2.0.0-linux-x64`
4. Run the executable to launch the application.

#### Linux Prerequisites

MouseTracks requires the XCB cursor library to be installed.

- Ubuntu/Debian:
    ```bash
    sudo apt install libxcb-cursor-dev
    ```
- Arch Linux:
    ```bash
    sudo pacman -Syu xcb-util-cursor
    ```

#### Mirrors
_These are not guaranteed to be the latest version._
- MouseTracks has been tested, reviewed and hosted by the amazing team over at [MajorGeeks](https://www.majorgeeks.com/files/details/mousetracks.html).

---

### Running from Source

This is recommended if you want to view or contribute to the code.
Python 3.11 or higher is required.

1. Clone the repository and create the virtual environment:
    ```cmd
    git clone https://github.com/huntfx/MouseTracks.git
    cd MouseTracks
    python -m venv .venv
    ```

2. Run the launch script. It will automatically install dependencies and start the app:
    - Windows:
      ```cmd
      launch.bat
      ```
    - Linux:
      ```bash
      chmod +x launch.sh
      ./launch.sh
      ```

---

### Building from Source

PyInstaller is used for the build process.

_Using a custom bootloader is entirely optional, but it may help reduce AV false positives._

- Windows:
  ```cmd
  build-pyinstaller-bootloader.bat
  build-pyinstaller.bat
  ```
  To package the built executables into an installer, use `build-installer.bat`.

- Linux:
  ```bash
  ./build-pyinstaller-bootloader.sh
  ./build-pyinstaller.sh
  ```
---

## Installation (v1.0 - Deprecated)

_The v1.0 version is no longer supported, but the launch process has been updated to bring it in line with v2.0._

- Fully compatible with Windows.

You will be prompted with a choice to start tracking or generate images. This can be skipped by passing the `--start-tracking` or `--generate-images` flags.

### Running from Source

Any version of Python may be used.

1. Clone the repository and create the virtual environment:
    ```cmd
    git clone https://github.com/huntfx/MouseTracks.git
    cd MouseTracks
    python -m venv .venv-legacy
    ```

2. Run the launch script. It will automatically install dependencies and start the app:
    ```cmd
    launch-legacy.bat
    ```

---

## Render Types
Multiple data types can be rendered.<br>
There are additional options, but the main ones are highlighted below.

The majority of these renders are from 500 hours of general PC use, excluding coding and gaming.<br>
The gamepad renders are from a game that was played for 30 hours.

### Mouse Movement
<img src="media/render-types/mouse-movement.jpg">

### Mouse Speed
<img src="media/render-types/mouse-speed.jpg">

### Mouse Position
<img src="media/render-types/mouse-position.jpg">

### Mouse Clicks
<img src="media/render-types/mouse-clicks.jpg">

## Keyboard Heatmap
<img src="media/render-types/keyboard-heatmap.jpg">

### Gamepad Thumbstick Movement
<img src="media/render-types/gamepad-thumbstick-movement.jpg">

### Gamepad Thumbstick Position
<img src="media/render-types/gamepad-thumbstick-position.jpg">

## Colour Maps
Each render is given a colour map.<br>
There are additional options, but the main ones are highlighted below.<br>
It's also possible to [define your own](https://github.com/huntfx/MouseTracks/wiki/Colour-Maps).

### Ice
<img src="media/render-types/mouse-movement.jpg">

### Citrus
<img src="media/render-colours/tracks/citrus.jpg">

### Demon
<img src="media/render-colours/tracks/demon.jpg">

### Sunburst
<img src="media/render-colours/tracks/sunburst.jpg">

### Jet
<img src="media/render-types/mouse-clicks.jpg">

### Explosion
<img src="media/render-colours/heatmaps/explosion.jpg">

### Submerged
<img src="media/render-colours/heatmaps/submerged.jpg">

### Aqua
<img src="media/render-types/keyboard-heatmap.jpg">

### Nature
<img src="media/render-colours/keyboard/nature.jpg">

### Fire
<img src="media/render-colours/keyboard/fire.jpg">

### Chalk
<img src="media/render-colours/keyboard/chalk.jpg">

## Example Renders
#### Desktop
<img src="media/render-types/mouse-movement.jpg">
<img src="media/render-types/mouse-clicks.jpg">

## Path of Exile
<img src="media/examples/pathofexile-movement.jpg">
<img src="media/examples/pathofexile-clicks.jpg">

#### Factorio
<img src="media/examples/factorio-movement.jpg">
<img src="media/examples/factorio-clicks.jpg">

#### Overwatch
<img src="media/examples/overwatch-movement.jpg">

#### Torchlight 2
<img src="media/examples/torchlight2-movement.jpg">

#### Heroes of the Storm
<img src="media/examples/heroesofthestorm-movement.jpg">
<img src="media/examples/heroesofthestorm-clicks.jpg">

#### Hogwarts Legacy
<img src="media/examples/hogwartslegacy-movement.jpg">

#### Livelock
<img src="media/examples/livelock-movement.jpg">
<img src="media/examples/livelock-clicks.jpg">

#### Alien Swarm
<img src="media/examples/alienswarm-movement.jpg">
<img src="media/examples/alienswarm-clicks.jpg">

#### Age of Empires IV
<img src="media/examples/ageofempiresiv-movement.jpg">
<img src="media/examples/ageofempiresiv-clicks.jpg">

#### Adobe Lightroom
<img src="media/examples/adobelightroom-movement.jpg">

---

## Data Privacy
All data recorded or generated by MouseTracks is stored entirely locally on your computer. You have full control over this data, including the ability to change the storage location, export your data, and delete it.

MouseTracks does not transmit any of your personal data or usage information over the internet - the only connection made is to check for updates, and this feature can be completely disabled with the `--offline` flag if required.
