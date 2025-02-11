import sys
from multiprocessing import freeze_support

from mousetracks.config.settings import CONFIG, CONFIG_PATH
from mousetracks.track import track
from mousetracks.utils.os import tray, console, open_folder, open_file, get_key_press


if __name__ == '__main__':
    freeze_support()

    start_tracking = '--start-tracking' in sys.argv
    generate_images = '--generate-images' in sys.argv
    if not (start_tracking or generate_images):
        from mousetracks.image import select_options
        print('What would you like to do?')
        options = [
            ['start_tracking', True, 'Start Tracking (--start-tracking)'],
            ['generate_images', False, 'Generate Images (--generate-images)'],
        ]

        result = select_options(options, multiple_choice=False)

        if result == 'start_tracking':
            start_tracking = True
        elif result == 'generate_images':
            generate_images = True
        elif result == 'debug_apps':
            debug_app_detection = True

    if start_tracking:
        no_gui = tray is None or not CONFIG['API']['WebServer']

        #Elevate and quit the process
        if CONFIG['Main']['RunAsAdministrator']:
            console.elevate(visible=not CONFIG['Main']['StartMinimised'] or no_gui)

        #Run normally
        if no_gui:
            track()

        #Generate images
        elif console.is_set('GenerateImages'):
            from generate_images import user_generate
            user_generate()

        #Create new message client
        elif console.is_set('MessageServer'):
            from mousetracks.api import local_message_connect

            offset = sys.argv.index('MessageServer')
            port = int(sys.argv[offset+1])
            secret = sys.argv[offset+2]
            local_message_connect(port=port, secret=secret)

        #Create tray icon
        else:
            import uuid
            from threading import Thread

            from mousetracks.api import local_address, shutdown_server, calculate_api_timeout
            from mousetracks.applications import APP_LIST_PATH, AppList
            from mousetracks.config.language import LANGUAGE
            from mousetracks.constants import APP_LIST_FILE, DEFAULT_PATH
            from mousetracks.files import Lock, DATA_FOLDER
            from mousetracks.misc import format_file_path, get_script_path
            from mousetracks.notify import NOTIFY
            from mousetracks.utils.compatibility import Message, input
            from mousetracks.utils.internet import get_url_json, send_request
            from mousetracks.utils.sockets import get_free_port


            def _end_thread(cls):
                """Close the tracking thread."""
                quit_message_client(cls)
                if cls.cache['WebPort'] is not None:
                    shutdown_server(cls.cache['WebPort'])
                cls.cache['Thread'].join()

            def _start_tracking(cls, web_port=None, message_port=None, server_secret=None, _thread=None):
                """Start new tracking thread after closing old one."""
                #End old thread
                if _thread:
                    _end_thread(cls)
                    NOTIFY(LANGUAGE.strings['Tracking']['ScriptRestart'])
                    web_port = None

                #Start thread
                web_port = get_free_port() if web_port is None else web_port
                message_port = get_free_port() if message_port is None else message_port
                server_secret = uuid.uuid4() if server_secret is None else server_secret
                thread = Thread(target=track, kwargs={'web_port': web_port, 'message_port': message_port, 'console': False, 'lock': False, 'server_secret': server_secret})
                thread.start()

                #Set new port
                if cls is not None:
                    cls.cache['WebPort'] = web_port
                    cls.cache['Thread'] = thread
                    cls.set_menu_item('track', name='Pause Tracking')
                    cls.set_menu_item('restore2', args=['MessageServer', str(message_port), str(server_secret)])
                    if _thread:
                        cls.set_menu_item('restart', kwargs={'web_port': web_port, '_thread': thread})
                return thread

            def toggle_tracking(cls):
                """Pause or resume tracking.
                Add a timeout for if the script crashes.
                """
                web_port = cls.cache['WebPort']
                status_url = '{}/status'.format(local_address(web_port))
                status = get_url_json(status_url, timeout=calculate_api_timeout())

                if status == 'running':
                    send_request('{}/stop'.format(status_url), timeout=calculate_api_timeout(), output=True)
                elif status == 'stopped':
                    send_request('{}/start'.format(status_url), timeout=calculate_api_timeout(), output=True)

            def quit(cls):
                """End the script and close the window."""
                _end_thread(cls)
                del cls.cache['WebPort']
                del cls.cache['Thread']
                tray.quit(cls)

                #Bring back to front in case of console launch
                bring_to_front(cls)

            def new_window(cls, *args):
                """Launch a new console."""
                console.new(*args)

            def on_menu_open(cls):
                """Run this just before the menu opens."""
                web_port = cls.cache['WebPort']
                status_url = '{}/status'.format(local_address(web_port))
                status = get_url_json(status_url, timeout=calculate_api_timeout())

                if status == 'running':
                    cls.set_menu_item('track', name='Pause Tracking', hidden=False)
                elif status == 'stopped':
                    cls.set_menu_item('track', name='Resume Tracking', hidden=False)

                #Enable debug menu if shift is held
                if get_key_press(16):
                    cls.set_menu_item('debug', hidden=False)

                cls._refresh_menu()

            def on_menu_close(cls):
                """Run this after the menu has closed."""
                cls.set_menu_item('track', hidden=True)
                cls.set_menu_item('debug', hidden=True)

            def hide_in_tray(cls):
                cls.minimise_to_tray()

            def bring_to_front(cls):
                """Bring to front or restart if it fails for whatever reason."""
                cls.bring_to_front()

                #Currently restart is disabled since returning False
                #doesn't actually mean the script isn't working
                if False and not cls.bring_to_front():
                    print('Unknown error. Automatically restarting program...')
                    _end_thread(cls)
                    _start_tracking(cls)

            def on_hide(cls):
                cls.set_menu_item('hide', hidden=True)
                cls.set_menu_item('restore', hidden=False)

            def on_restore(cls):
                cls.set_menu_item('hide', hidden=False)
                cls.set_menu_item('restore', hidden=True)

            def applist_update(cls):
                AppList().update(save=True)

            def quit_message_client(cls):
                web_port = cls.cache['WebPort']
                close_mesage_url = '{}/ports/message/close'.format(local_address(web_port))
                status = send_request(close_mesage_url, timeout=calculate_api_timeout(), output=True)

            def start_message_client(cls, port, secret):
                new_window(None, 'MessageServer', str(port), str(secret))

            def open_applist(cls):
                open_file(APP_LIST_PATH)

            def open_config(cls):
                open_file(CONFIG_PATH)

            def open_documents_folder(cls):
                open_folder(format_file_path(DEFAULT_PATH))

            def open_script_folder(cls):
                open_folder(get_script_path())

            def open_data_folder(cls):
                open_folder(DATA_FOLDER)

            def open_images_folder(cls):
                open_folder(format_file_path(CONFIG['Paths']['Images'].replace('[Name]', '')))

            is_hidden = console.has_been_elevated() and CONFIG['Main']['StartMinimised'] and console.is_elevated()

            with Lock() as locked:
                if locked:
                    web_port = get_free_port()
                    message_port = get_free_port()
                    server_secret = uuid.uuid4()
                    thread = _start_tracking(cls=None, web_port=web_port, message_port=message_port, server_secret=server_secret)
                    menu_options = (
                        {'name': 'Navigation', 'action': (
                            {'name': 'AppList.txt', 'action': open_applist},
                            {'name': 'config.ini', 'action': open_config},
                            {'name': 'Documents Folder', 'action': open_documents_folder},
                            {'name': 'Image Folder', 'action': open_images_folder},
                            {'name': 'Data Folder', 'action': open_data_folder},
                            {'name': 'Program Folder', 'action': open_script_folder}
                        )},
                        {'id': 'generate', 'name': 'Generate Images', 'action': new_window, 'args': ['GenerateImages']},
                        {'id': 'track', 'name': 'Toggle pause/start', 'action': toggle_tracking, 'hidden': True},
                        {'id': 'restart', 'name': 'Restart', 'action': _start_tracking, 'kwargs': {'web_port': web_port, 'message_port': message_port, 'server_secret': server_secret, '_thread': thread}},
                        {'id': 'hide', 'name': 'Minimise to Tray', 'action': hide_in_tray, 'hidden': is_hidden},
                        {'id': 'restore', 'name': 'Bring to Front', 'action': bring_to_front, 'hidden': not is_hidden},
                        {'id': 'debug', 'name': 'Advanced', 'hidden': True, 'action': (
                            {'name': 'Force Update "{}" (requires internet)'.format(APP_LIST_FILE), 'action': applist_update, 'hidden': not CONFIG['Internet']['Enable']},
                            {'name': 'Start message client', 'hidden': not CONFIG['API']['SocketServer'], 'action': start_message_client, 'kwargs': {'port': message_port, 'secret': server_secret}},
                            {'name': 'Close all message clients', 'hidden': not CONFIG['API']['SocketServer'], 'action': quit_message_client},
                        )},
                        {'id': 'exit', 'name': 'Quit', 'action': quit},
                    )
                    t = tray.Tray(menu_options, program_name='Mouse Tracks')
                    t.minimise_override = is_hidden
                    t.cache['Thread'] = thread
                    t.cache['WebPort'] = web_port
                    t.set_event('OnMenuOpen', on_menu_open)
                    t.set_event('OnMenuClose', on_menu_close)
                    t.set_event('OnWindowHide', on_hide)
                    t.set_event('OnWindowRestore', on_restore)
                    t.listen()

                else:

                    Message(LANGUAGE.strings['Tracking']['ScriptDuplicate'])

                    #If program is hidden, don't wait for input
                    if not is_hidden:
                        input()

    if generate_images:
        from mousetracks.image import user_generate
        user_generate()
