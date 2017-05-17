from pyxhook import HookManager


class MouseClick(HookManager):
    def __init__(self):
        super().__init__()
        self.reset()
        new_hook = HookManager()
        new_hook.MouseAllButtonsDown = self.click
        new_hook.start()

    def click(self, event):
        """Mark buttons as clicked."""
        self.clicks[0] = 1
    
    def return_click(self):
        """Get any pressed buttons and reset."""
        clicks = self.clicks
        self.reset()
        return clicks
    
    def reset(self):
        """Mark buttons as unclicked."""
        self.clicks = [0]
        
        
def get_mouse_click():
    return CLICKS.return_click()


CLICKS = MouseClick()
