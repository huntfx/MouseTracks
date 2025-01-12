from multiprocessing import freeze_support
from mousetracks2.components.hub import Hub


if __name__ == '__main__':
    freeze_support()
    Hub().run(gui=True)
