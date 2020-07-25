import platform

if platform.system() == 'Windows':
    from .win import *
elif platform.system() == 'Linux':
    from .linux import *
elif platform.system() == 'Darwin':
    from .mac import *
