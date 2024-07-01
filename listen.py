from flask import Flask, request, jsonify
import docker
import db
import logging
import re

app = Flask(__name__)
client = docker.from_env()
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
def get_container_status(container_id):
    container = client.containers.get(container_id)
    return container.status



def handle_docker_error(e):
    if isinstance(e, docker.errors.NotFound):
        return jsonify({'message': 'Container not found'}), 404
    elif isinstance(e, docker.errors.APIError):
        return jsonify({'message': 'Docker API error', 'error': str(e)}), 500
    else:
        return jsonify({'message': 'Error', 'error': str(e)}), 500
@app.route('/create_server', methods=['GET'])
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

        # Use parameterized query to prevent SQL injection
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
    

@app.route('/server/<uuid>/start', methods=['POST'])
def start_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.start()
        return jsonify({'message': 'Container started successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)

@app.route('/server/<uuid>/restart', methods=['POST'])
def restart_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.restart()
        return jsonify({'message': 'Container restarted successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)

@app.route('/server/<uuid>/kill', methods=['POST'])
def kill_server(uuid):
    try:
        container = client.containers.get(uuid)
        container.kill()
        return jsonify({'message': 'Container killed successfully'}), 200
    except Exception as e:
        return handle_docker_error(e)
@app.route('/servers', methods=['GET'])
def list_server():
    server_list = db.runsqlaction("SELECT port, image, uuid, status FROM server")
    servers = [{'port': row[0], 'image': row[1], 'uuid': row[2], 'status': row[3]} for row in server_list]
    
    # Update status of each server
    for server in servers:
        server['status'] = get_container_status(server['uuid'])

    return jsonify(servers)


@app.route('/server/<uuid>/files', methods=['GET'])
def list_files(uuid):
    try:
        path = request.args.get('path', '/')  # Get the 'path' query parameter from URL, default to root '/'
        

        
        # Retrieve the container by UUID
        container = client.containers.get(uuid)
        
        # Execute a command to list files in the specified path
        command = f'ls -lah {path}'
        result = container.exec_run(command)
        
        if result.exit_code != 0:
            return jsonify({'message': 'Error executing command', 'error': result.output.decode('utf-8')}), 500
        
        files = result.output.decode('utf-8')

        # Parse the ls -l output into a list of dictionaries
        file_list = parse_ls_output(files)
        
        return jsonify({
            'message': 'Files listed successfully',
            'files': file_list
        }), 200
    except docker.errors.NotFound:
        return jsonify({'message': 'Container not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'message': 'Docker API error', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Error listing files', 'error': str(e)}), 500

def parse_ls_output(output):
    lines = output.strip().split('\n')
    files = []
    for line in lines[1:]:  # Skip the first line which is typically the 'total' line
        parts = re.split(r'\s+', line, maxsplit=8)
        if len(parts) == 9:
            file_type = 'file'
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
    return files


@app.route('/server/<uuid>', methods=['GET'])
def server_details(uuid):
    try:
        container = client.containers.get(uuid)
        details = {
            'id': container.id,
            'status': container.status,
            'image': container.image.tags[0] if container.image.tags else 'N/A',
            'name': container.name,
            'ports': container.attrs['HostConfig']['PortBindings'],
            'created': container.attrs['Created'],
            'network_mode': container.attrs['HostConfig']['NetworkMode'],
        }
        return details
    except Exception as e:
        return handle_docker_error(e)

def run(debug=True):
    app.run(debug=debug,host='0.0.0.0')
