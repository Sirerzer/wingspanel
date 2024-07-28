import socket

def check_port_in_use(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex((host, port))
        if result == 0:
            return False
        else:
            return True

# Vérifier si le port 500 est utilisé