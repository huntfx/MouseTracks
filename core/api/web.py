from __future__ import absolute_import

from flask import Flask, jsonify, abort, request
from multiprocessing import Pipe
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

from core.api.constants import *
from core.notify import *


def create_pipe(name, duplex=False):
    name_recv = 'PIPE_{}_RECV'.format(name)
    name_send = 'PIPE_{}_SEND'.format(name)
    recv, send = Pipe(duplex=duplex)
    return {name_recv: recv, name_send: send}
    
    
def shutdown_server():
    """End the Flask server.
    Needs to be called within a Flask function,
    otherwise the request context will be wrong.
    """
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def _get_ports():
    """Get the server and socket ports."""
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_PORT)
    return app.config['PIPE_PORT_RECV'].recv()

def _get_config():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_CONFIG)
    return app.config['PIPE_CONFIG_RECV'].recv()
    
    
app = Flask(__name__)

@app.route('/')
def main_page():
    all = {}
    all['status'] = get_running_status()
    all['ports'] = _get_ports()
    all['config'] = _get_config()
    return jsonify(all)

    
@app.route('/status/')
def get_running_status():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_STATUS)
    status = app.config['PIPE_STATUS_RECV'].recv()
    return ['running', 'stopped'][status]
    

@app.route('/status/start')
@app.route('/status/run')
def script_resume():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_RUNNING)
    return get_running_status()


@app.route('/status/pause')
@app.route('/status/stop')
def script_pause():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_PAUSED)
    return get_running_status()


@app.route('/server/terminate')
def script_exit():
    app.config['PIPE_CONTROL_SEND'].send(STATUS_TERMINATED)
    shutdown_server()
    abort(503)

    
@app.route('/port/')
def get_port(json=True):
    return jsonify(_get_ports())


@app.route('/port/web')
def get_port_web():
    return jsonify(_get_ports()['web'])


@app.route('/port/server')
def get_port_server():
    return jsonify(_get_ports()['server'])
    
    
@app.route('/config/')
def config():
    return jsonify(_get_config())
    
    
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