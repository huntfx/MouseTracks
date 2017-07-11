import time
import traceback
from multiprocessing import freeze_support

from core.config import CONFIG
from core.misc import error_output
from core.main import start_tracking


if __name__ == '__main__':

    freeze_support()

    #Rewrite the config with validated values
    CONFIG.save()

    #Run the script and exit safely if an error happens
    try:
        error = start_tracking()
        if error.startswith('Traceback (most recent call last)'):
            error_output(error)
    except Exception as e:
        error_output(traceback.format_exc())
