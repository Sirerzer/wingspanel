from flask import Flask, request, jsonify, redirect, url_for
import docker
import db
import re
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
from functools import wraps
from yml import token
import proxy

from flask_sockets import Sockets

app = Flask(__name__)
sockets = Sockets(app)

app.secret_key = 'MOMOGHGFIqhqduihguiuiFGIUGHUIZETZGIUZEIUHYDFQUIHUIDSDHFUIDSHFIUHDQSIUHFUIHFIUHGVUIHBUIFHIUODHFIUDQHFIUDHFIUHDFIUDHGUIFDHIUDQUIGQSDIUQG'
client = docker.from_env()

ACCESS_TOKEN = "Bearer " + token

CORS(app)  

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        proxy.reload()
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        if token != ACCESS_TOKEN:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


def handle_docker_error(e):
    if isinstance(e, docker.errors.NotFound):
        return jsonify({'message': 'Container not found'}), 404
    elif isinstance(e, docker.errors.APIError):
        return jsonify({'message': 'Docker API error', 'error': str(e)}), 500
    else:
        return jsonify({'message': 'Error', 'error': str(e)}), 500




from datetime import datetime
from dateutil import parser
import docker
import mimetypes
import os
import stat
@app.route('/api/servers/<container_id>/files/contents', methods=['GET'])
@token_required
def get_file_content(container_id):
    path = request.args.get('file')
    path = "/usr/share/nginx/html"+path
    if not path:
        return jsonify({'error': 'File path is required'}), 400

    container = db.get_docker_uuid(container_id)
    command = f"cat {path}"
    container = client.containers.get(container)
    result = container.exec_run(command)

    if result.exit_code != 0:
        return jsonify({'error': 'Failed to read file content'}), 500

    return result.output.decode(), 200

@app.route('/api/servers/<container_id>/files/write', methods=['POST'])
@token_required
def write_file(container_id):
    path = request.args.get('file')
    content = request.data.decode('utf-8')
    path = "/usr/share/nginx/html"+path


    if not path:
        return jsonify({'error': 'File path is required'}), 400
    if not content:
        return jsonify({'error': 'File content is required'}), 400

    container = db.get_docker_uuid(container_id)
    # Escape single quotes in content
    sanitized_content = content.replace("'", "'\\''")
    command = f"sh -c 'echo \"{sanitized_content}\" > {path}'"
    container = client.containers.get(container)

    result = container.exec_run(command)

    if result.exit_code != 0:
        return jsonify({'error': 'Failed to write to file'}), 500

    return jsonify({'message': 'File written successfully'}), 200

def parse_datetime(datetime_str):
    """
    Parses a datetime string and handles extra spaces or characters.
    """
    # Remove unwanted characters and extra spaces
    cleaned_str = re.sub(r'\.\d+', '', datetime_str).strip()  # Remove nanoseconds and extra spaces

    try:
        # Try parsing the datetime string with and without milliseconds
        return datetime.strptime(cleaned_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print(f"Datetime parsing failed for string: {cleaned_str}")
        return None

def get_container_files(uuid, path='/'):
    """
    Retrieves file information from a Docker container given a UUID.
    """
    client = docker.from_env()
    
    try:
        container = client.containers.get(uuid)
        files_info = []
        
        # Run a command inside the container to list files
        command = f"find {path} -type f"
        file_paths = container.exec_run(command).output.decode().splitlines()

        for file_path in file_paths:
            try:
                # Collect file metadata
                stat_command = f"stat --format='%a %s %y %n' {file_path}"
                file_stat = container.exec_run(stat_command).output.decode().split()
                mode_bits = int(file_stat[0], 8)
                size = int(file_stat[1])
                
                # Handle possible extra characters in datetime
                modified_str = ' '.join(file_stat[2:4])
                modified = parse_datetime(modified_str)
                
                # Append file metadata
                file_data = {
                    'name': os.path.basename(file_path),
                    'mode': stat.filemode(mode_bits),
                    'mode_bits': mode_bits,
                    'size': size,
                    'file': True,
                    'symlink': False,
                    'mime': mimetypes.guess_type(file_path)[0] or 'unknown',
                    'created': 'unknown',  # Docker does not provide creation time
                    'modified': modified.isoformat() + 'Z' if modified else 'unknown'
                }
                files_info.append(file_data)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        return files_info
    
    except docker.errors.NotFound:
        raise ValueError("Container not found")
    except Exception as e:
        print(f"Error retrieving files from container {uuid}: {e}")
        raise

@app.route('/api/servers/<container_id>/files/list-directory', methods=['GET'])
@token_required
def navigate_file(container_id):
    try:
        file_path = request.args.get('directory', '/')  # Default to root directory if not provided
        file_path = "/usr/share/nginx/html"+file_path
        # Simulate fetching UUID from a database
        uuid = db.get_docker_uuid(container_id)  # Replace with actual database call

        if not uuid:
            raise ValueError("UUID not found for the provided container_id")
        
        # List files
        files = get_container_files(uuid, path=file_path)

        # Format data
        formatted_files = [
            {
                'name': item.get('name'),
                'mode': item.get('mode'),
                'mode_bits': item.get('mode_bits'),
                'size': item.get('size'),
                'is_file': item.get('file', True),
                'is_symlink': item.get('symlink', False),
                'mimetype': item.get('mime', 'application/octet-stream'),
                'created_at': item.get('created'),
                'modified_at': item.get('modified')
            }
            for item in files
        ]

        return jsonify(formatted_files)

    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<container_id>/files/create-directory', methods=['POST'])
@token_required
def create_directory(container_id):
    data = request.json
    name = data.get('name')
    path = data.get('path', '/')
    path = "/usr/share/nginx/html"+path

    if not name:
        return jsonify({'error': 'Directory name is required'}), 400

    container = db.get_docker_uuid(container_id)
    command = f"mkdir -p {os.path.join(path, name)}"
    container = client.containers.get(container)

    result = container.exec_run(command)

    if result.exit_code != 0:
        return jsonify({'error': 'Failed to create directory'}), 500

    return jsonify({'message': 'Directory created successfully'}), 200

@app.route('/api/servers/<container_id>/files/rename', methods=['PUT'])
@token_required
def rename_file(container_id):
    data = request.json
    root = data.get('root', '/')
    files = data.get('files', [])
    root = "/usr/share/nginx/html"+root

    if not files:
        return jsonify({'error': 'Files to rename are required'}), 400

    container = db.get_docker_uuid(container_id)
    for file in files:
        from_path = os.path.join(root, file['from'])
        to_path = os.path.join(root, file['to'])
        command = f"mv {from_path} {to_path}"
        container = client.containers.get(container)
        result = container.exec_run(command)
        if result.exit_code != 0:
            return jsonify({'error': f'Failed to rename {from_path} to {to_path}'}), 500

    return jsonify({'message': 'Files renamed successfully'}), 200

@app.route('/api/servers/<container_id>/files/delete', methods=['POST'])
@token_required
def delete_files(container_id):
    data = request.json
    root = data.get('root', '/')
    files = data.get('files', [])
    root = "/usr/share/nginx/html"+root

    if not files:
        return jsonify({'error': 'Files to delete are required'}), 400

    container = db.get_docker_uuid(container_id)
    for file in files:
        path = os.path.join(root, file)
        command = f"rm -rf {path}"
        container = client.containers.get(container)
        result = container.exec_run(command)
        if result.exit_code != 0:
            return jsonify({'error': f'Failed to delete {path}'}), 500

    return jsonify({'message': 'Files deleted successfully'}), 200

@app.route('/api/servers/<container_id>/files/compress', methods=['POST'])
@token_required
def compress_files(container_id):
    data = request.json
    root = data.get('root', '/')
    files = data.get('files', [])
    root = "/usr/share/nginx/html"+root

    if not files:
        return jsonify({'error': 'Files to compress are required'}), 400

    container = db.get_docker_uuid(container_id)
    container = client.containers.get(container)
    command = f"tar -czf /tmp/archive.tar.gz -C {root} {' '.join(files)}"

    result = container.exec_run(command)

    if result.exit_code != 0:
        print(result)
        return jsonify({'error': 'Failed to compress files'}), 500

    return jsonify({'message': 'Files compressed successfully'}), 200

@app.route('/api/servers/<container_id>/files/decompress', methods=['POST'])
@token_required
def decompress_file(container_id):
    data = request.json
    root = data.get('root', '/')
    file = data.get('file')
    root = "/usr/share/nginx/html"+root

    if not file:
        return jsonify({'error': 'File to decompress is required'}), 400

    container = db.get_docker_uuid(container_id)
    command = f"tar -xzf {os.path.join(root, file)} -C {root}"
    container = client.containers.get(container)
    result = container.exec_run(command)
    if result.exit_code != 0:
        return jsonify({'error': f'Failed to decompress {file}'}), 500

    return jsonify({'message': 'File decompressed successfully'}), 200

@app.route('/api/servers/<container_id>/files/chmod', methods=['POST'])
@token_required
def chmod_files(container_id):
    data = request.json
    root = data.get('root', '/')
    files = data.get('files', [])
    root = "/usr/share/nginx/html"+root

    if not files:
        return jsonify({'error': 'Files to chmod are required'}), 400

    container = db.get_docker_uuid(container_id)
    for file in files:
        path = os.path.join(root, file['path'])
        mode = file['mode']
        
        command = f"chmod {mode} {path}"
        container = client.containers.get(container)
        result = container.exec_run(command)
        if result.exit_code != 0:
            return jsonify({'error': f'Failed to chmod {path}'}), 500

    return jsonify({'message': 'Files chmoded successfully'}), 200

@app.route('/api/servers/<container_id>/files/pull', methods=['POST'])
@token_required
def pull_file(container_id):
    data = request.json
    url = data.get('url')
    directory = data.get('root', '/')
    filename = data.get('file_name', None)
    use_header = data.get('use_header', None)
    foreground = data.get('foreground', None)
    directory = "/usr/share/nginx/html"+directory

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    container = db.get_docker_uuid(container_id)
    command = f"wget {url} -O {os.path.join(directory, filename or 'file')}"
    container = client.containers.get(container)
    result = container.exec_run(command)
    if result.exit_code != 0:
        return jsonify({'error': f'Failed to pull file from {url}'}), 500

    return jsonify({'message': 'File pulled successfully'}), 200
# Modifier la fonction upload_file

@app.route('/api/servers', methods=['POST'])
@token_required
def create_server():
    if request.is_json:
        # Récupère les données JSON envoyées
        data = request.get_json()
        
        # Extrait le UUID des données JSON
        uuid = data.get('uuid')
        
        # Affiche les données reçues dans la console
        print("Données reçues :")
        print(data)
        
        # Récupère d'autres paramètres depuis les arguments de la requête
    
        
       
            
        db.runsqlaction("INSERT INTO server (port, image, uuid, dockeruuid, status, ndd) VALUES (?, ?, ?, ?, ?, ?)", (port, image_name, uuid, container.id, get_container_status(container.id), ndd))
                
        return jsonify({
            'message': 'Server created successfully',
            
        }), 200
       
    else:
        return jsonify({
            'message': 'Request must be in JSON format'
        }), 400
    
@app.route('/api/servers/<uuid>', methods=['DELETE'])
@token_required
def delete_server(uuid):
    try:
        # Recherche le conteneur avec le UUID spécifié
        container = client.containers.get(db.get_docker_uuid(uuid))
        
        # Arrête et supprime le conteneur
        container.stop()
        container.remove()
        
        # Suppression de l'entrée correspondante dans la base de données
        # db.runsqlaction("DELETE FROM server WHERE uuid = ?", (uuid,))
        
        return jsonify({
            'message': 'Server deleted successfully',
            'container_id': uuid
        }), 200
    except docker.errors.NotFound:
        return jsonify({
            'message': 'Container not found'
        }), 404
    except Exception as e:
        return jsonify({
            'message': 'Error deleting server',
            'error': str(e)
        }), 500
from werkzeug.exceptions import BadRequest


import json
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
@app.route('/api/system', methods=['GET'])
@token_required
def nodestatus():
    return jsonify({
        'etat':'running',
        'version': '0.0.9',
    })

def run(debug=True,port=5000):
    #app.run(debug=debug,host='0.0.0.0',port=port)
    from gevent import pywsgi
    
    from geventwebsocket.handler import WebSocketHandler
    time = db.print_current_time()
    print(f"[{time}] Starting Webpanel wings on port {port}")
    # Start the server with WebSocket support
    server = pywsgi.WSGIServer(('0.0.0.0', port), app, handler_class=WebSocketHandler)
    server.serve_forever()
