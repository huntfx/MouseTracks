from core.main import start_tracking
from core.constants import CONFIG
from core.functions import error_output
import traceback
    
if __name__ == '__main__':
    
    CONFIG.save() # Rewrite the config with validated values

    try:
        error = start_tracking()
        if error.startswith('Traceback (most recent call last)'):
            error_output(error)
    except Exception as e:
        error_output(traceback.format_exc())
