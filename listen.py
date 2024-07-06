from flask import Flask, request, jsonify
import docker
import db
import logging
import re
import os
from flask_cors import CORS
import io
import tarfile
from functools import wraps
import yml


app = Flask(__name__)
client = docker.from_env()
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
def get_container_status(container_id):
    container = client.containers.get(container_id)
    return container.status
ACCESS_TOKEN = yml.ACCESS_TOKEN

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
    


@app.route('/create_server', methods=['GET'])
@token_required
def create_server():
    image_name = request.args.get('image', default='nginx', type=str)
    port = request.args.get('port', default=80, type=int)
    host_ip = request.args.get('host_ip', default='0.0.0.0', type=str)  # Ajout du paramètre host_ip
    
    try:
        # Create and start the container
        container = client.containers.run(
            image_name, 
            detach=True, 
            ports={f'{port}/tcp': (host_ip, port)},  # Utilisation de host_ip dans les ports
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


def parse_ls_output(output):
    
    """
    Parses the output of `ls -l` command into a list of dictionaries.
    Each dictionary represents a file or directory.
    """
    lines = output.strip().split('\n')
    files = []
    file_type = 'file'  # Default to directory unless a file is found
    for line in lines[1:]:  # Skip the first line which is typically the 'total' line
        parts = re.split(r'\s+', line, maxsplit=8)
        if len(parts) == 9:
            if parts[0].startswith('d'):
                file_type = 'directory'
            
           
            files.append({
                'type': file_type,
                'permissions': parts[0],
                'links': parts[1],
                'owner': parts[2],
                'group': parts[3],
                'size': parts[4],
                'month': parts[5],
                'day': parts[6],
                'time_or_year': parts[7],
                'name': parts[8],
            })
    return files, file_type
@app.route('/server/<uuid>/delete_file', methods=['POST'])
@token_required
def delete_file(uuid):
    try:
        # Récupère le chemin du fichier à supprimer depuis les données de formulaire
        file_path = request.form.get('file_path')

        # Récupère le conteneur par UUID
        container = client.containers.get(uuid)

        # Supprime le fichier dans le conteneur
        command = f'rm -f {file_path}'
        result = container.exec_run(command)

        if result.exit_code != 0:
            return jsonify({'message': 'Erreur lors de la suppression du fichier', 'error': result.output.decode('utf-8')}), 500

        return jsonify({'message': 'Fichier supprimé avec succès'}), 200

    except docker.errors.NotFound:
        return jsonify({'message': 'Conteneur non trouvé'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Erreur de l\'API Docker', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la suppression du fichier', 'error': str(e)}), 500
    


@app.route('/server/<uuid>/archive', methods=['POST'])
@token_required
def archive_files(uuid):
    try:
        # Récupère les chemins des fichiers à archiver depuis les données de formulaire
        file_paths = request.form.getlist('file_paths[]')

        # Récupère le conteneur par UUID
        container = client.containers.get(uuid)

        # Crée une archive tar des fichiers spécifiés
        archive_name = 'files.tar'
        command = f'tar -cvf {archive_name} {" ".join(file_paths)}'
        result = container.exec_run(command)

        if result.exit_code != 0:
            return jsonify({'message': 'Erreur lors de la création de l\'archive', 'error': result.output.decode('utf-8')}), 500

        # Télécharge l'archive depuis le conteneur
        stream, _ = container.get_archive(archive_name)
        with open(archive_name, 'wb') as f:
            for chunk in stream:
                f.write(chunk)

        return jsonify({'message': 'Archive créée et téléchargée avec succès'}), 200

    except docker.errors.NotFound:
        return jsonify({'message': 'Conteneur non trouvé'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Erreur de l\'API Docker', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la création de l\'archive', 'error': str(e)}), 500
    

@app.route('/server/<uuid>/create_directory', methods=['POST'])
@token_required
def create_directory(uuid):
    try:
        # Récupère le chemin du répertoire à créer depuis les données de formulaire
        directory_path = request.form.get('directory_path')

        # Récupère le conteneur par UUID
        container = client.containers.get(uuid)

        # Crée le répertoire dans le conteneur
        command = f'mkdir -p {directory_path}'
        result = container.exec_run(command)

        if result.exit_code != 0:
            return jsonify({'message': 'Erreur lors de la création du répertoire', 'error': result.output.decode('utf-8')}), 500

        return jsonify({'message': 'Répertoire créé avec succès'}), 200

    except docker.errors.NotFound:
        return jsonify({'message': 'Conteneur non trouvé'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Erreur de l\'API Docker', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la création du répertoire', 'error': str(e)}), 500

@app.route('/server/<uuid>/files', methods=['GET'])
@token_required
def list_files(uuid):
    try:
        path = request.args.get('path', '/')  # Récupère le paramètre 'path' depuis l'URL, par défaut à la racine '/'

        # Récupère le conteneur par UUID
        container = client.containers.get(uuid)

        # Exécute la commande pour lister les fichiers dans le chemin spécifié
        command = f'ls -lah {path}'
        result = container.exec_run(command)

        if result.exit_code != 0:
            return jsonify({'message': 'Erreur lors de l\'exécution de la commande', 'error': result.output.decode('utf-8')}), 500

        files_output = result.output.decode('utf-8')

        # Parse la sortie de ls -l en une liste de dictionnaires
        file_list, file_type = parse_ls_output(files_output)

        if file_type == 'directory':
            return jsonify({
                'message': 'Liste des fichiers réussie',
                'files': file_list
            }), 200

        # Si file_type est un fichier, obtient le contenu du fichier
        command = f'cat {path}'
        result = container.exec_run(command)

        if result.exit_code != 0:
            return jsonify({'message': 'Erreur lors de la lecture du contenu du fichier', 'error': result.output.decode('utf-8')}), 500

        file_content = result.output.decode('utf-8')

        return jsonify({
            'message': 'Contenu du fichier récupéré avec succès',
            'file_content': file_content
        }), 200

    except docker.errors.NotFound:
        return jsonify({'message': 'Conteneur non trouvé'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Erreur de l\'API Docker', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la liste ou de la lecture des fichiers', 'error': str(e)}), 500


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

@app.route('/server/<uuid>/upload', methods=['POST'])
@token_required
def upload_file(uuid):
    try:
        # Get the container by UUID
        container = client.containers.get(uuid)
       
        # Check if files are present in the request
        if 'files[]' not in request.files:
            return jsonify({'message': 'No file part in the request'}), 400

        # Retrieve the files from the request
        files = request.files.getlist('files[]')  # Use getlist() to get all files

        upload_path = request.form.get('upload_path', '/')  # Get the upload path from the form data

        for file in files:
            # Create a temporary tar archive from the uploaded file
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name=file.filename)
                tarinfo.size = len(file.read())
                file.seek(0)
                tar.addfile(tarinfo, file)
            tar_stream.seek(0)

            # Upload the tar archive to the Docker container
            container.put_archive(upload_path, tar_stream.getvalue())

            # Extract the tar archive within the Docker container
            extract_command = f'tar -xvf "{upload_path}/{file.filename}" "{upload_path}"'
            exec_result = container.exec_run(extract_command)
            if exec_result.exit_code != 0:
                return jsonify({
                    'message': 'Error extracting file in container',
                    'error': exec_result.output.decode('utf-8')
                }), 500

        return jsonify({
            'message': 'Files uploaded and extracted successfully',
            'upload_path': upload_path
        }), 200

    except docker.errors.NotFound:
        return jsonify({'message': 'Container not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Docker API error', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Error handling file upload', 'error': str(e)}), 500
    

@app.route('/node/status', methods=['GET'])
@token_required
def nodestatus():
    return jsonify({
        'etat':'running',
        'version': '0.0.4',
    })

def run(debug=True,port=5000):
    app.run(debug=debug,host='0.0.0.0',port=port)
