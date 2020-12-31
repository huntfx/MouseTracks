import platform

if platform.system() == 'Windows':
    from .win import *
elif platform.system() == 'Linux':
    from .linux import *
elif platform.system() == 'Darwin':
    from .mac import *


if 'get_monitor_locations' not in globals():
    def get_monitor_locations():
        """Get the location of each monitor.
        This is a placeholder function which will use the primary
        monitor resolution.

        Returns:
            ((x1, y1, x2, y2),) as 4 integers for each monitor
        """
        width, height = main_monitor_resolution()
        return ((0, 0, width, height),)


if 'check_key_press' not in globals():
    check_key_press = lambda key: False


if 'DOUBLE_CLICK_INTERVAL' not in globals():
    DOUBLE_CLICK_INTERVAL = 0.5
