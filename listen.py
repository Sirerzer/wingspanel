from flask import Flask, request, jsonify
import docker
import db
import logging
import re
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask import Flask, flash, request, redirect, url_for
import uuid
import io
import tarfile
from functools import wraps
from yml import token
import proxy

class DockerFileManager:
    def __init__(self):
        self.clienta = docker.from_env()

    def list_files(self, container_id, file_path="."):
        container = self.clienta.containers.get(container_id)
        cmd = f"ls -a {file_path}"
        files = container.exec_run(cmd).output.decode().split()
        return files
    def create_file(self, container_id, file_path,filename):
        container = self.clienta.containers.get(container_id)
        cmd = f"touch {file_path}/{filename}"
        files = container.exec_run(cmd).output.decode().split()
        return files
    
    def mkdir(self, container_id, file_path,repertoriename):
        container = self.clienta.containers.get(container_id)
        cmd = f"mkdir {file_path}/{repertoriename}"
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
    def upload_file(self, container_id, file_path, file_stream):
        container = self.clienta.containers.get(container_id)

        # Create an in-memory tar archive with the uploaded file
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=os.path.basename(file_path))
            tarinfo.size = len(file_stream.getbuffer())
            tar.addfile(tarinfo, file_stream)

        tar_stream.seek(0)

        try:
            # Ensure the directory exists
            container.exec_run(f"mkdir -p {os.path.dirname(file_path)}")
            # Put the archive in the container
            container.put_archive(os.path.dirname(file_path), tar_stream)
            return True
        except Exception as e:
            print(f"Error while uploading file: {e}")
            return False
app = Flask(__name__)
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','tar','gz'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'MOMOGHGFIqhqduihguiuiFGIUGHUIZETZGIUZEIUHYDFQUIHUIDSDHFUIDSHFIUHDQSIUHFUIHFIUHGVUIHBUIFHIUODHFIUDQHFIUDHFIUHDFIUDHGUIFDHIUDQUIGQSDIUQG'
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload/<container_id>/<path:file_path>', methods=['GET', 'POST'])
def uploada_file(container_id,file_path):
    file_uuid = uuid.uuid4()
    file_uuid = str(file_uuid)
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            try:
                container = client.containers.get(container_id)
                source_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.system(f'tar -cvf {file_uuid} {source_file}')
                destination_path = f"/{filename}"
                
                with open(file_uuid, 'rb') as file_data:
                    container.put_archive(f'/var/www/html/{file_path}', file_data.read())
                container.exec_run(f"cp /var/www/html/tmp/* /var/www/html/{file_path}")
                container.exec_run(f"rm /var/www/html/tmp/*")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')

                return 'File uploaded successfully', 200
            
            except docker.errors.NotFound as e:
                print(f"Container '{container_id}' not found")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')
                return redirect(request.url)
            
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')
                return redirect(request.url)
    
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''
@app.route('/upload/<container_id>/', methods=['GET', 'POST'])
def upload_file_root(container_id):
    file_uuid = uuid.uuid4()
    file_uuid = str(file_uuid)
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            try:
                container = client.containers.get(container_id)
                source_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.system(f'tar -cvf {file_uuid} {source_file}')
                destination_path = f"/{filename}"
                
                with open(file_uuid, 'rb') as file_data:
                    container.put_archive('/var/www/html/', file_data.read())
                container.exec_run(f"cp -rf /var/www/html/tmp/* /var/www/html/")
                container.exec_run(f"rm -rf /var/www/html/tmp/*")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')

                return 'File uploaded successfully', 200
            
            except docker.errors.NotFound as e:
                print(f"Container '{container_id}' not found")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')
                return redirect(request.url)
            
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                os.system(f'rm -rf {source_file}')
                os.system(f'rm -rf {file_uuid}')
                return redirect(request.url)
    
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''



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



# Modifier la fonction upload_file
import docker

@app.route('/files/upload/<container_id>/<path:file_path>', methods=['POST'])
@token_required
def upload_file(container_id, file_path):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected for uploading'}), 400

    if file:
        try:
            # Create a Docker client
            client = docker.from_env()

            # Get the container by its UUID
            container = client.containers.get(container_id)

            # Create a temporary file to store the uploaded file
            tmp_file = tempfile.NamedTemporaryFile()
            file.save(tmp_file)

            # Copy the file to the container
            container.put_archive(file_path, tmp_file.read())

            # Remove the temporary file
            tmp_file.close()

            return jsonify({'message': f'File successfully uploaded to {file_path}'}), 201
        except docker.errors.NotFound:
            return jsonify({'message': 'Container not found'}), 404
        except docker.errors.APIError as e:
            return jsonify({'message': 'Error uploading file', 'error': str(e)}), 500
        except Exception as e:
            return jsonify({'message': 'Error uploading file', 'error': str(e)}), 500

@app.route('/files/<container_id>/<path:file_path>', methods=['POST'])

def mkdir(container_id, file_path):
    
    try:
        
        # Check if the content indicates that the file is not a regular file
        data = request.get_json()  # Récupérer les données JSON
        if data is None:
            return "Invalid data: JSON required", 400
        
        reponse = data.get('content')
        if reponse is None:
            return "Invalid data: 'content' is required", 400
        content = docker_fm.mkdir(container_id, file_path,reponse)
        # If content is None or it's a regular file, return the content
        return 200
    
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
    ndd = request.args.get('ndd',type=str,default=None)
    host_ip = request.args.get('host_ip', default='0.0.0.0', type=str)  # Ajout du paramètre host_ip
    try:
        # Create and start the container
        container = client.containers.run(
            image_name,
            detach=True,
            ports={f'{intport}/tcp': (host_ip, port)},
            environment={'PHP_FPM_LISTEN': '9000'}  # Configuration spécifique à PHP-FPM

           
        )

    
        db.runsqlaction("INSERT INTO server (port, image, uuid, status,ndd) VALUES (?, ?, ?, ?,?)", (port, image_name, container.id, get_container_status(container.id),ndd))
        
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
