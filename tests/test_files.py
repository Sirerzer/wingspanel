from flask import Flask, jsonify, request
import docker
import os

app = Flask(__name__)
client = docker.from_env()

class DockerFileManager:
    def __init__(self):
        pass

    def list_files(self, container_id, file_path="."):
        container = client.containers.get(container_id)
        cmd = f"ls -a {file_path}"
        files = container.exec_run(cmd).output.decode().split()
        return files

    def read_file(self, container_id, file_path):
        container = client.containers.get(container_id)
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
        container = client.containers.get(container_id)
        temp_file = f"/tmp/{os.path.basename(file_path)}"
        with open(temp_file, 'w') as f:
            f.write(content)
        container.put_archive(os.path.dirname(file_path), (temp_file,))
        os.remove(temp_file)
        return True

docker_fm = DockerFileManager()

@app.route('/files/<container_id>/<path:file_path>', methods=['GET'])
def navigate_file(container_id, file_path):
    try:
        content = docker_fm.read_file(container_id, file_path)
        
        # Check if the content indicates that the file is not a regular file
        if content and 'not a regular file' in content:
            # If it's not a regular file, list files instead
            return docker_fm.list_files(container_id, file_path=file_path)
        
        # If content is None or it's a regular file, return the content
        return content
    
    except Exception as e:
        # Handle exceptions appropriately (log or return an error response)
        print(f"Error reading file: {e}")
        return f"Error reading file: {e}", 500


@app.route('/files/<container_id>', methods=['GET'])
def list_files(container_id):
    files = docker_fm.list_files(container_id)
    return jsonify(files)

@app.route('/files/<container_id>/<path:file_path>', methods=['POST'])
def write_file(container_id, file_path):
    content = request.data.decode('utf-8')
    if docker_fm.write_file(container_id, file_path, content):
        return f"Successfully wrote new content to {file_path}\n", 201
    else:
        return "Failed to write content\n", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
