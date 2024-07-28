import docker

client = docker.from_env()

def list_files_in_container(container_id, path='/'):
    try:
        container = client.containers.get(container_id)
        command = f'ls -l {path}'
        result = container.exec_run(command)
        if result.exit_code == 0:
            return result.output.decode('utf-8')
        else:
            return None
    except docker.errors.NotFound:
        return "Container not found"
    except docker.errors.APIError as e:
        return f"Docker API error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
