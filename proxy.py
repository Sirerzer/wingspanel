import db
import docker
import os
# Initialisation du client Docker
client = docker.from_env()
def insert_server_data():
    sql = "INSERT INTO server (port, image, uuid, status, ndd) VALUES (?, ?, ?, ?, ?)"
    values = ("21447", "richarvey/nginx-php-fpm", "1d7d9dff29d99a79b80bc3a5d6293ef9b7fd5f06d4974e94c41ed08fdbcd251c", "running", "proxy.atersir.fr")
    db.runsqlaction(sql, values)
def generate_nginx_config(server_name,upstream_url):
    nginx_config = ""
    upstream_url = f"http://localhost:{upstream_url}"

     # Assuming upstream URL is in the third column
    # Generating Nginx configuration block for each server
    nginx_config += f"""
    server {{
        listen 80;
        server_name {server_name};
        
        location / {{
            proxy_pass {upstream_url};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}
    """
    return nginx_config
def reload():
    # Retrieving server data from the database
    server_data = db.runsqlaction("SELECT * FROM server")
    
    # Processing retrieved server data
    for server in server_data:
        
        if server[4] == None:
            pass
        else:
            config = generate_nginx_config(server[4],server[0])
            nginx_config_file = f"/etc/nginx/sites-enabled/{server[4]}"  # Adjust path as needed
            with open(nginx_config_file, "w") as f:
                f.write(config)
            os.system("systemctl reload nginx")