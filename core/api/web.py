from __future__ import absolute_import

from flask import Flask, jsonify, abort, request

from core.api.constants import *


def shutdown_server():
    """End the Flask server.
    Needs to be called within a Flask function,
    otherwise the request context will be wrong.
    """
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

    
app = Flask(__name__)


@app.route('/status/')
def get_running_status():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_STATUS)
    status = app.config['PIPE_STATUS_RECV'].recv()
    return ['running', 'paused', 'stopped'][status]


@app.route('/status/start')
@app.route('/status/run')
def script_resume():
    app.config['PIPE_CONTROL_SEND'].send(SCRIPT_RUN)
    return get_running_status()


@app.route('/status/pause')
def script_pause():
    app.config['PIPE_CONTROL_SEND'].send(SCRIPT_PAUSE)
    return get_running_status()


@app.route('/status/stop')
@app.route('/status/exit')
def script_exit():
    app.config['PIPE_CONTROL_SEND'].send(SCRIPT_EXIT)
    shutdown_server()
    abort(503)


@app.route('/port/')
def get_port():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_PORT)
    server_port, web_port = app.config['PIPE_PORT_RECV'].recv()
    return jsonify({'server': server_port, 'web': web_port})


@app.route('/port/web')
def get_port():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_PORT)
    server_port, web_port = app.config['PIPE_PORT_RECV'].recv()
    return web_port


@app.route('/port/server')
def get_port():
    app.config['PIPE_REQUEST_SEND'].send(FEEDBACK_PORT)
    server_port, web_port = app.config['PIPE_PORT_RECV'].recv()
    return server_port
    
    
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