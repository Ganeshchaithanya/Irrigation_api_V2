# AquaSol API V2 — VPS Production Setup Guide

This guide provides step-by-step instructions for hosting and running the **AquaSol FastAPI Backend** on a Linux VPS (Ubuntu/Debian) using **Docker & Docker Compose**, complete with an **Nginx Reverse Proxy** and **Free Let's Encrypt SSL (Certbot)**.

---

## 🛠️ Step 1: Install Docker & Docker Compose on the VPS

Run the following commands on your VPS terminal to update package repositories and install the modern Docker engine:

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install pre-requisites
sudo apt install -y curl apt-transport-https ca-certificates gnupg lsb-release

# 3. Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. Set up the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Install Docker Engine and Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. Verify installations
docker --version
docker compose version
```

---

## 📂 Step 2: Upload Your Code to the VPS

Since your codebase is not pushed to GitHub, you can upload the codebase directory directly from your local machine to your VPS using `scp` (Secure Copy) or `rsync`.

Run this command **on your local machine** from the directory containing `Irrigation_api_V2`:

```bash
# Replace 'username' with your VPS user (e.g., ubuntu/root) and 'vps_ip' with your server IP
scp -r e:\Irrigation_api_V2 username@vps_ip:/home/username/aquasol
```

*Alternatively*, zip the folder locally, upload it, and extract it on the VPS:
```bash
# Local (Windows PowerShell)
Compress-Archive -Path e:\Irrigation_api_V2\* -DestinationPath e:\aquasol.zip
scp e:\aquasol.zip username@vps_ip:/home/username/

# On the VPS
sudo apt install unzip
unzip aquasol.zip -d /home/username/aquasol
```

---

## 🔑 Step 3: Configure Environment Variables

1. Log into your VPS via SSH:
   ```bash
   ssh username@vps_ip
   cd /home/username/aquasol
   ```
2. Create or copy your `.env` file on the VPS:
   ```bash
   nano .env
   ```
3. Ensure the production environment variables are properly defined:
   ```env
   PROJECT_NAME="Irrigation_API_2"
   DATABASE_URL="postgresql://neondb_owner:npg_Lbf9rKJHMSW3@ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
   SECRET_KEY="c8e1a39012bc1c65fb2e8d17d3da39160c153bd5afeff7d63a0383556ac04be4"
   GROQ_API_KEY="your_groq_api_key_here"
   WEATHER_API_KEY="48eae0af422bef1f2c57529d8e1beddf"
   UI_API_KEY="your_ui_api_key_here"
   ```
   *Press `CTRL + O`, then `Enter` to save, and `CTRL + X` to exit.*

---

## 🚀 Step 4: Build & Run the Container

Build the optimized Docker image and spin up the backend container in **detached (background) mode** using Docker Compose:

```bash
# Build the image and start the container
sudo docker compose up --build -d

# Verify the container is running and healthy
sudo docker compose ps
```

### 📊 How to Check Container Logs:
To monitor the startup logs or review real-time API requests, run:
```bash
# Follow live container output
sudo docker compose logs -f backend
```

---

## 🔒 Step 5: Configure Nginx & Free SSL (Certbot)

To access your API over secure `https://` with a custom domain (e.g. `api.yourdomain.com`), set up Nginx as a reverse proxy.

### 1. Install Nginx & Certbot
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Configure Nginx Server Block
Create a new configuration block for your domain:
```bash
sudo nano /etc/nginx/sites-available/aquasol
```

Paste the following configuration (replace `api.yourdomain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
*Save and exit (`CTRL + O` -> `Enter` -> `CTRL + X`).*

### 3. Enable Configuration & Restart Nginx
```bash
# Link the site to sites-enabled
sudo ln -s /etc/nginx/sites-available/aquasol /etc/nginx/sites-enabled/

# Test Nginx configuration for syntax errors
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 4. Obtain Let's Encrypt SSL Certificate
Ensure your custom domain's **DNS A Record** points to your VPS IP address, then request the SSL certificate:
```bash
sudo certbot --nginx -d api.yourdomain.com
```
*Follow the interactive prompts. Certbot will automatically issue the certificate, configure Nginx to use SSL, and redirect all HTTP traffic to secure HTTPS.*

---

## 🛠️ Step 6: Ongoing Maintenance Commands

Manage your deployment smoothly using these core commands:

| Command | Action |
|---------|--------|
| `sudo docker compose down` | Stops and removes active containers. |
| `sudo docker compose restart` | Restarts all active containers. |
| `sudo docker compose logs -f` | Follow live runtime logs of all services. |
| `sudo docker compose up --build -d` | Re-builds changed code/dependencies and updates in-place without downtime. |
