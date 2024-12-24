from components.hub import Hub

if __name__ == '__main__':
    hub = Hub()
    hub.start_tracking()
    hub.start_queue_handler()
