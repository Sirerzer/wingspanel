import json
from flask import Flask, jsonify, request
from flask_sockets import Sockets
import logging

# Initialize Flask and Flask-Sockets
app = Flask(__name__)
sockets = Sockets(app)

# Configure the logger for debugging
logging.basicConfig(level=logging.DEBUG)

# HTTP route for /api/system
@app.route('/api/system', methods=['GET'])
def system_info():
    return jsonify({
        'status': 'running',
        'message': 'System is operational',
    })

# WebSocket route for /api/servers/<uuid>/ws
@sockets.route('/api/servers/<uuid>/ws')
def echo(ws, uuid):
    print(f"New connection with UUID: {uuid}")
    while():
        message = ws.receive()
        if message:
            print(f"Received message: {message}")
            message_data = json.loads(message)
            event = message_data.get("event")
            if event == "auth":
                ws.send(json.dumps({"event": "auth success"}))
            elif event == "send logs":
                ws.send(json.dumps({"event": "logs", "data": "Here are the logs"}))
            elif event == "send stats":
                ws.send(json.dumps({"event": "stats", "data": "Here are the stats"}))
            else:
                ws.send(json.dumps({"event": "error", "message": "Unknown event"}))
if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    # Start the server with WebSocket support
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    print("Server started at ws://0.0.0.0:5000")
    server.serve_forever()
