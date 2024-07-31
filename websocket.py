from flask import Flask, request
import gevent
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.websocket import WebSocket

app = Flask(__name__)

@app.route('/api/servers/<uuid>/ws')
def echo_socket(uuid):
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        print(f"New connection with UUID: {uuid}")
        while not ws.closed:
            message = ws.receive()
            if message:
                print(f"Received message: {message}")
                # Assuming you need to handle the auth message and validate it
                if message.startswith('{"event":"auth"'):
                    ws.send('{"event":"auth success"}')
                else:
                    ws.send('{"event":"unknown message"}')
        return ""
    else:
        print("No WebSocket found in the environment.")
        print(f"Request environment: {request.environ}")
    return "This is a WebSocket endpoint."

@app.route('/')
def index():
    return 'Hello, this is a Flask application running with WebSocket support.'

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5000
    server = WSGIServer((host, port), app, handler_class=WebSocketHandler)
    print(f"Server started at ws://{host}:{port}")
    server.serve_forever()
