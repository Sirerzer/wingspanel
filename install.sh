#!/bin/bash

SERVICE_NAME="wingspanel"
SCRIPT_NAME="main.py"
INSTALL_DIR="/opt/"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WRAPPER_SCRIPT="/usr/local/bin/${SERVICE_NAME}"
CONFIG_FILE="/etc/webpanel/config.yml"
PYTHON_EXEC="/usr/bin/python3"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

echo "Installing dependencies..."
apt-get update
apt-get install -y docker.io python3 python3-pip

systemctl start docker
systemctl enable docker

echo "Creating installation directory..."
mkdir -p $INSTALL_DIR

echo "Copying wingspanel.py to installation directory..."
cd $INSTALL_DIR
git clone https://github.com/Sirerzer/wingspanel.git

pip3 install docker pyyaml pytest pytest-cov flask flask-cors 


echo "Creating systemd service file..."
cat <<EOF > $SERVICE_FILE
[Unit]
Description=WingsPanel Service
After=docker.service
Requires=docker.service

[Service]
ExecStart=${PYTHON_EXEC} ${INSTALL_DIR}/${SCRIPT_NAME}
WorkingDirectory=${CONFIG_FILE}
Environment="PATH=/usr/bin:/usr/local/bin"
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

echo "Creating wrapper script..."
cat <<EOF > $WRAPPER_SCRIPT
#!/bin/bash
${PYTHON_EXEC} ${INSTALL_DIR}/wingspanel/${SCRIPT_NAME} "\$@"
EOF
chmod +x $WRAPPER_SCRIPT

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling and starting the service..."
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

echo "Installation complete. You can manage the service using 'systemctl' and run the script using '${SERVICE_NAME}'."
