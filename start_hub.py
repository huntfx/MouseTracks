from mousetracks2.components.hub import Hub

if __name__ == '__main__':
    hub = Hub()
    hub.start_gui()
    hub.start_queue_handler()
