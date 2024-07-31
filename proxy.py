import db
import os
import subprocess

def generate_nginx_config(server_name, upstream_url):
    if not upstream_url:
        return ""
    
    upstream_url = f"http://localhost:{upstream_url}"

    nginx_config = f"""
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
    try:
        # Retrieve server data from the database
        server_data = db.runsqlaction("SELECT * FROM server")
        
        for server in server_data:
            server_name = server[4]
            upstream_url = server[0]
            
            if not server_name:
                continue
            
            # Generate Nginx configuration
            config = generate_nginx_config(server_name, upstream_url)
            
            if not config:
                print(f"No configuration generated for server: {server_name}")
                continue
            
            nginx_config_file = f"/etc/nginx/sites-enabled/{server_name}"
            
            # Write the configuration to the file
            try:
                with open(nginx_config_file, "w") as f:
                    f.write(config)
                print(f"Configuration written to {nginx_config_file}")
            except IOError as e:
                print(f"Failed to write configuration to {nginx_config_file}: {e}")
                continue
            
            # Reload Nginx
            try:
                subprocess.run(["systemctl", "reload", "nginx"], check=True)
                print("Nginx reloaded successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to reload Nginx: {e}")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    reload()
