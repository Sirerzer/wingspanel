from flask import Flask, request, jsonify
import docker
import db
import logging
import re
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
import io
import tarfile
from functools import wraps
from yml import token

class DockerFileManager:
    def __init__(self):
        self.clienta = docker.from_env()

    def list_files(self, container_id, file_path="."):
        container = self.clienta.containers.get(container_id)
        cmd = f"ls -a {file_path}"
        files = container.exec_run(cmd).output.decode().split()
        return files

    def read_file(self, container_id, file_path):
        container = self.clienta.containers.get(container_id)
        try:
            # Vérifier si file_path est un fichier
            if container.exec_run(f"test -f {file_path}").exit_code == 0:
                cmd = f"cat {file_path}"
                content = container.exec_run(cmd).output.decode()
                return content
            else:
                return f"{file_path} is not a regular file\n"
        except docker.errors.APIError as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def write_file(self, container_id, file_path, content):
        container = self.clienta.containers.get(container_id)
        
        # Create an in-memory tar archive with the content
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=os.path.basename(file_path))
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content.encode('utf-8')))
        
        tar_stream.seek(0)

        try:
            # Ensure the directory exists
            container.exec_run(f"mkdir -p {os.path.dirname(file_path)}")
            # Put the archive in the container
            container.put_archive(os.path.dirname(file_path), tar_stream)
            return True
        except Exception as e:
            print(f"Error while writing file: {e}")
            return False

app = Flask(__name__)
client = docker.from_env()
docker_fm = DockerFileManager()
def get_container_status(container_id):
    container = client.containers.get(container_id)
    return container.status
ACCESS_TOKEN = token

CORS(app)  

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
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
    
@app.route('/files/<container_id>/<path:file_path>', methods=['GET'])

def navigate_file(container_id, file_path):
    
    try:
        content = docker_fm.read_file(container_id, file_path)
        # Check if the content indicates that the file is not a regular file
        if content and 'file' in content:
            # If it's not a regular file, list files instead
            return docker_fm.list_files(container_id, file_path=file_path)

            
        else:
            content = docker_fm.read_file(container_id, file_path)

        # If content is None or it's a regular file, return the content
        return content
    
    except Exception as e:
        # Handle exceptions appropriately (log or return an error response)
        print(f"Error reading file: {e}")
        return f"Error reading file: {e}", 500


@app.route('/files/<container_id>/', methods=['GET'])
@token_required
def list_files(container_id):
    files = docker_fm.list_files(container_id)
    return jsonify(files)

import tarfile
import io
@app.route('/files/<container_id>/<path:file_path>', methods=['POST'])
@token_required
def write_file(container_id, file_path):
    try:
        data = request.get_json()  # Récupérer les données JSON
        if data is None:
            return "Invalid data: JSON required", 400
        
        content = data.get('content')
        if content is None:
            return "Invalid data: 'content' is required", 400
        
        directory = os.path.dirname(file_path)
        if not directory:
            return "Path cannot be empty", 400
        
        # Supposons que docker_fm.write_file est une fonction définie ailleurs
        if docker_fm.write_file(container_id, file_path, content):
            return f"Successfully wrote new content to {file_path}\n", 201
        else:
            return "Failed to write content\n", 500
    except Exception as e:
        return str(e), 500
@app.route('/create_server', methods=['GET'])
@token_required
def create_server():
    image_name = request.args.get('image', default='nginx', type=str)
    port = request.args.get('port', type=int)
    intport = request.args.get('intport', type=int,default=80)

    host_ip = request.args.get('host_ip', default='0.0.0.0', type=str)  # Ajout du paramètre host_ip
    try:
        # Create and start the container
        container = client.containers.run(
            image_name,
            detach=True,
            ports={f'{intport}/tcp': (host_ip, port)},
            environment={'PHP_FPM_LISTEN': '9000'}  # Configuration spécifique à PHP-FPM

           
        )

    
        db.runsqlaction("INSERT INTO server (port, image, uuid, status) VALUES (?, ?, ?, ?)", (port, image_name, container.id, get_container_status(container.id)))
        
        return jsonify({
            'message': 'Server created successfully',
            'container_id': container.id,
            'image': image_name,
            'port': port,
            'host_ip': host_ip
            
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Error creating server',
            'error': str(e)
        }), 500
    

@app.route('/server/<uuid>/start', methods=['GET'])
@token_required
def start_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.start()
        return jsonify({'message': 'Container started successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)

@app.route('/server/<uuid>/restart', methods=['GET'])
@token_required
def restart_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.restart()
        return jsonify({'message': 'Container restarted successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)

@app.route('/server/<uuid>/kill', methods=['GET'])
@token_required
def kill_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.kill()
        return jsonify({'message': 'Container killed successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)
    


@app.route('/server/<uuid>/stop', methods=['GET'])
@token_required
def stop_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.stop()
        return jsonify({'message': 'Container stoped successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)
@app.route('/servers', methods=['GET'])
@token_required
def list_server():
    server_list = db.runsqlaction("SELECT port, image, uuid, status FROM server")
    servers = [{'port': row[0], 'image': row[1], 'uuid': row[2], 'status': row[3]} for row in server_list]
    
    # Update status of each server
    for server in servers:
        try:
            server['status'] = get_container_status(server['uuid'])
        except:
            server['status'] = "N/A"
    return jsonify(servers)




@app.route('/server/<uuid>', methods=['GET'])
@token_required
def server_details(uuid):
    try:
        container = client.containers.get(uuid)
        disk_usage = get_disk_usage(container)
        details = {
            'id': container.id,
            'status': container.status,
            'image': container.image.tags[0] if container.image.tags else 'N/A',
            'name': container.name,
            'ports': container.attrs['HostConfig']['PortBindings'],
            'created': container.attrs['Created'],
            'network_mode': container.attrs['HostConfig']['NetworkMode'],
            'disk_usage': disk_usage
        }
        return jsonify(details)
    except Exception as e:
        return handle_docker_error(e)

def get_disk_usage(container):
    try:
        result = container.exec_run("df -h /")
        if result.exit_code == 0:
            output_lines = result.output.decode().split('\n')
            if len(output_lines) > 1:
                disk_usage = output_lines[1].split()[3]  # Assuming the output is in the standard format
                return disk_usage
        return 'N/A'
    except Exception:
        return 'N/A'


    

@app.route('/node/status', methods=['GET'])
@token_required
def nodestatus():
    return jsonify({
        'etat':'running',
        'version': '0.0.8',
    })

def run(debug=True,port=5000):
    app.run(debug=debug,host='0.0.0.0',port=port)
