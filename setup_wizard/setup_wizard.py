"""
Explanation of the Script

1. Installing dependencies:
    - This step installs Gunicorn, PostgreSQL, Nginx, and Certbot (for SSL).
2. Setting up PostgreSQL:
    - Creates a new database and user, sets encoding, and grants privileges.
3. Setting up Gunicorn:
    - Configures a systemd service to manage Gunicorn for your Django app.
4. Configuring Nginx:
    - Sets up Nginx as a reverse proxy for Gunicorn.
    - Configures static and media file serving.
5. Setting up SSL (Let's Encrypt):
    - Uses Certbot to automatically generate and install SSL certificates for your domain.
6. Setting up the firewall:
    - Configures the firewall to allow HTTP and HTTPS traffic (ports 80 and 443).
"""

import os
import subprocess

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing {command}: {result.stderr}")
        exit(1)
    print(result.stdout)

def install_dependencies():
    print("Installing Gunicorn, PostgreSQL, Nginx, and Certbot...")
    commands = [
        "sudo apt update",
        "sudo apt install -y python3-pip python3-venv gunicorn postgresql postgresql-contrib nginx certbot python3-certbot-nginx",
    ]
    for cmd in commands:
        run_command(cmd)

def setup_postgresql(db_name, db_user, db_password):
    print(f"Setting up PostgreSQL database: {db_name}")
    commands = [
        f"sudo -u postgres psql -c \"CREATE DATABASE {db_name};\"",
        f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\"",
        f"sudo -u postgres psql -c \"ALTER ROLE {db_user} SET client_encoding TO 'utf8';\"",
        f"sudo -u postgres psql -c \"ALTER ROLE {db_user} SET default_transaction_isolation TO 'read committed';\"",
        f"sudo -u postgres psql -c \"ALTER ROLE {db_user} SET timezone TO 'UTC';\"",
        f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\""
    ]
    for cmd in commands:
        run_command(cmd)

def setup_gunicorn(django_project_dir):
    print("Setting up Gunicorn systemd service...")
    service_content = f"""
    [Unit]
    Description=gunicorn daemon for {django_project_dir}
    After=network.target

    [Service]
    User=www-data
    Group=www-data
    WorkingDirectory={django_project_dir}
    ExecStart={django_project_dir}/venv/bin/gunicorn --workers 3 --bind unix:{django_project_dir}/app.sock {django_project_dir}.wsgi:application

    [Install]
    WantedBy=multi-user.target
    """
    service_file = "/etc/systemd/system/gunicorn.service"
    with open(service_file, "w") as f:
        f.write(service_content)

    # Enable and start the service
    run_command("sudo systemctl start gunicorn")
    run_command("sudo systemctl enable gunicorn")
    run_command("sudo systemctl status gunicorn")

def setup_nginx(domain_name, django_project_dir):
    print("Setting up Nginx as a reverse proxy...")
    nginx_config = f"""
    server {{
        listen 80;
        server_name {domain_name};

        location / {{
            proxy_pass http://unix:{django_project_dir}/app.sock;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        location /static/ {{
            alias {django_project_dir}/static/;
        }}

        location /media/ {{
            alias {django_project_dir}/media/;
        }}
    }}
    """
    config_path = f"/etc/nginx/sites-available/{domain_name}"
    with open(config_path, "w") as f:
        f.write(nginx_config)

    run_command(f"sudo ln -s {config_path} /etc/nginx/sites-enabled/")
    run_command("sudo nginx -t")
    run_command("sudo systemctl restart nginx")

def setup_ssl(domain_name):
    print("Setting up SSL certificates...")
    run_command(f"sudo certbot --nginx -d {domain_name}")

def setup_firewall():
    print("Configuring firewall to allow HTTP and HTTPS...")
    run_command("sudo ufw allow 'Nginx Full'")
    run_command("sudo ufw enable")

def main():
    print("Django Deployment Setup Wizard")

    # Get user inputs
    domain_name = input("Enter your domain name: ")
    db_name = input("Enter PostgreSQL database name: ")
    db_user = input("Enter PostgreSQL username: ")
    db_password = input("Enter PostgreSQL password: ")
    django_project_dir = input("Enter the full path to your Django project: ")

    # Run the setup steps
    install_dependencies()
    setup_postgresql(db_name, db_user, db_password)
    setup_gunicorn(django_project_dir)
    setup_nginx(domain_name, django_project_dir)
    setup_ssl(domain_name)
    setup_firewall()

    print("Setup complete! Your Django app is now live with Gunicorn, Nginx, and SSL.")

if __name__ == "__main__":
    main()

