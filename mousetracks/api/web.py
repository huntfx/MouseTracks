from __future__ import absolute_import

from flask import Flask, jsonify, abort, request

from .constants import *
from ..utils.compatibility import iteritems
from ..utils.ini import config_to_dict

#Disable Flask logging
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


def _shutdown_server():
    """End the Flask Werkzeug server.
    Can only be called within a Flask function.
    """
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()


def _get_ports():
    """Get the server and socket ports."""
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_PORT)
    return app.config['PIPE_PORT_RECV'].recv()

    
def _get_config():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_CONFIG)
    try:
        return app.config['PIPE_CONFIG_RECV'].recv()

    # In Python 3, it somehow skips running Config.__init__
    # This isn't a major feature so just disable it
    except AttributeError:
        return {}
    
    
def _get_status():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_STATUS)
    status = app.config['PIPE_STATUS_RECV'].recv()
    return ('running', 'stopped')[status]
    
    
app = Flask(__name__)

@app.route('/')
def main_page():
    all = {}
    all['status'] = _get_status()
    all['ports'] = _get_ports()
    all['config'] = config_to_dict(_get_config())
    return jsonify(all)

    
@app.route('/status/')
def get_running_status():
    return jsonify(_get_status())
    

@app.route('/status/start')
@app.route('/status/run')
def script_resume():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_RUNNING)
    return jsonify(_get_status())


@app.route('/status/pause')
@app.route('/status/stop')
def script_pause():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_PAUSED)
    return jsonify(_get_status())


@app.route('/status/terminate')
def script_exit():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_TERMINATED)
    _shutdown_server()
    abort(503)

    
@app.route('/ports/')
@app.route('/ports/<string:port_type>/')
def get_port(port_type=None):
    if port_type is None:
        return jsonify(_get_ports())
    try:
        return jsonify(_get_ports()[port_type.lower()])
    except KeyError:
        abort(404)


@app.route('/ports/<string:port_type>/close/')
def close_connection(port_type=None):
    if port_type.lower() == 'message':
        app.config['PIPE_CONTROL_SEND'].send(CLOSE_MESSAGE_CONNECTIONS)
        return jsonify(True)
    return jsonify(False)


@app.route('/config/', methods=['GET'])
@app.route('/config/<string:heading>/', methods=['GET'])
@app.route('/config/<string:heading>/<string:variable>/', methods=['GET'])
@app.route('/config/<string:heading>/<string:variable>/<string:property>', methods=['GET'])
def config_controls(heading=None, variable=None, property=None):

    #Set config value
    if heading is not None and variable is not None:
        for k, v in iteritems(request.args):
            if k == 'set':
                app.config['PIPE_CONTROL_SEND'].send(CONFIG_SET)
                app.config['PIPE_CONFIG_UPDATE_SEND'].send((heading, variable, v))

    #Return config
    _config = _get_config()
    config = config_to_dict(_config)
    if heading is None:
        return jsonify(config)
    try:
        if variable is None:
            return jsonify(config[heading])
        else:
            if property is not None:
                property = property.lower()
                try:
                    if property == 'min':
                        return jsonify(_config[heading][variable].min)
                    elif property == 'max':
                        return jsonify(_config[heading][variable].max)
                    elif property == 'default':
                        if _config[heading][variable].type == bool:
                            return jsonify(bool(_config[heading][variable].default))
                        return jsonify(_config[heading][variable].default)
                    elif property == 'valid':
                        return jsonify(_config[heading][variable].valid)
                    elif property == 'type':
                        return jsonify(_config[heading][variable].type.__name__)
                except AttributeError:
                    abort(404)
            return jsonify(config[heading][variable])
    except KeyError:
        abort(404)
    
    
#json example for future reference
'''
tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]
    
@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})
    '''

if __name__ == "__main__":
    app.run()