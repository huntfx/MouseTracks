import pyxhook

class mouse_click(pyxhook.HookManager):
    def __init__(self, path):
        super().__init__()
        self.path = path
        new_hook = pyxhook.HookManager()
        new_hook.MouseAllButtonsDown = self.click
        new_hook.start()

    def click(self,event):
        file = open(self.path, 'a')
        x, y = event.Position
        file.write('{},{}'.format(x, y))
        file.write('\n')

