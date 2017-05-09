from pyxhook import HookManager


class mouse_click(HookManager):
    def __init__(self, path):
        super().__init__()
        self.points = []
        new_hook = pyxhook.HookManager()
        new_hook.MouseAllButtonsDown = self.click
        new_hook.start()

    def click(self,event):
        x, y = event.Position
        self.points.append((x,y))
