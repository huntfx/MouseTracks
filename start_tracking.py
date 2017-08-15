from __future__ import absolute_import
from multiprocessing import freeze_support

from core.track import start_tracking


if __name__ == '__main__':
    
    freeze_support()
    start_tracking()
