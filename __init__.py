if __name__ == '__main__':
    from core.main import start_tracking
    from core.constants import CONFIG
    
    CONFIG.save() # Rewrite the config with validated values
    start_tracking()
