"""Test script to generate a window that spans all monitors.
So far the only application I've seen do this was HP RGS.
"""

import ctypes
import tkinter as tk

# Force DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

user32 = ctypes.windll.user32

# Calculate the full bounding box of all monitors
v_x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
v_y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
v_width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
v_height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

# Build the UI
root = tk.Tk()
root.title('Virtual Resolution Test')
root.overrideredirect(True)  # Remove all window borders and title bars
root.geometry(f'{v_width}x{v_height}+{v_x}+{v_y}')
root.configure(bg='blue')
root.bind('<Escape>', lambda e: root.destroy())
label = tk.Label(
    root,
    text='Multi-Monitor Spanning Window\nPress ESC to close.',
    font=('Segoe UI', 48, 'bold'),
    bg='blue',
    fg='white'
)
label.pack(expand=True)

# root.attributes('-topmost', True)  # Force window on top

print(f'Spawning window at: X:{v_x}, Y:{v_y}, W:{v_width}, H:{v_height}')
root.mainloop()
