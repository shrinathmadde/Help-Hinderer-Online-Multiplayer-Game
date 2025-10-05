# Help-Hinderer-Online-Multiplayer-Game

Game is running here http://ec2-56-228-14-31.eu-north-1.compute.amazonaws.com/




Perfect ✅ — here’s a clean, complete **deployment guide** you can use as your personal reference or include in your repository as `DEPLOYMENT_GUIDE.md`.

It covers **every step** from EC2 setup, CI/CD configuration, to Nginx + Gunicorn deployment.

---

# 🚀 **Flask-Socket.IO Game Deployment Guide (AWS EC2 + CI/CD)**

## 🧩 **Overview**

This guide documents the full process used to deploy the
**Help-Hinderer-Online-Multiplayer-Game** Flask Socket.IO web app to an **AWS EC2 Ubuntu instance**,
integrated with **GitHub Actions** for automated deployment (CI/CD).

---

## 🖥️ **1. Create and Configure EC2 Instance**

### ✅ Steps:

1. Launch an **Ubuntu 22.04** EC2 instance (t2.micro — Free Tier eligible).
2. Create and download a **.pem key pair** for SSH access.
3. Open **security group inbound rules**:

   * `22` → SSH (Your IP)
   * `80` → HTTP (0.0.0.0/0)
   * `443` → HTTPS (0.0.0.0/0)
4. Connect to the instance:

   ```bash
   ssh -i ~/path/to/key.pem ubuntu@<ec2-public-dns>
   ```

---

## ⚙️ **2. Server Setup (First-time Configuration)**

### Install dependencies:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-venv python3-dev build-essential redis-server nginx git -y
```

### Enable Redis:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Clone your GitHub repo:

```bash
git clone https://github.com/shrinathmadde/Help-Hinderer-Online-Multiplayer-Game.git
cd Help-Hinderer-Online-Multiplayer-Game
```

---

## 🧰 **3. Set Up Python Environment**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install specific working versions:

```bash
pip install "eventlet==0.33.3" "gunicorn==20.1.0"
```

---

## ⚙️ **4. Run App Manually (Test)**

To confirm the app runs correctly:

```bash
python app.py
```

Or test with Gunicorn:

```bash
gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 app:app
```

Then visit in your browser:

```
http://<your-ec2-public-dns>/
```

If you see the homepage, the backend works fine.

---

## 🌐 **5. Configure Nginx Reverse Proxy**

### Edit Nginx site config:

```bash
sudo nano /etc/nginx/sites-available/flaskgame
```

Paste:

```nginx
server {
    listen 80;
    server_name ec2-XX-XXX-XXX-XX.eu-north-1.compute.amazonaws.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/static/;
    }
}
```

### Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/flaskgame /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🧱 **6. Fix Static File Permission Issue**

If JS/CSS files return 403 Forbidden:

```bash
sudo chmod 755 /home
sudo chmod 755 /home/ubuntu
sudo chmod 755 /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game
sudo chmod -R 755 /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/static
sudo chown -R ubuntu:www-data /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/static
sudo systemctl reload nginx
```

Verify:

```bash
curl -I http://<ec2-dns>/static/js/pages/indexPage.js
# Should return 200 OK
```

---

## 🧩 **7. Create Systemd Service**

### Create file:

```bash
sudo nano /etc/systemd/system/flaskgame.service
```

Paste:

```ini
[Unit]
Description=Flask Socket.IO Game
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game
Environment="PATH=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/venv/bin"
ExecStart=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Enable and run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flaskgame
sudo systemctl start flaskgame
sudo systemctl status flaskgame
```

---

## 🔍 **8. Monitoring and Logs**

View logs:

```bash
sudo journalctl -u flaskgame -n 50 --no-pager
sudo journalctl -u nginx -n 50 --no-pager
```

Restart services:

```bash
sudo systemctl restart flaskgame
sudo systemctl reload nginx
```

---

## 🔄 **9. CI/CD with GitHub Actions**

### 🔹 Step 1: Generate SSH deploy key

On your local machine:

```bash
ssh-keygen -t rsa -b 4096 -C "github-deploy-key" -f ~/.ssh/github-deploy-key
```

Add the **public key** to EC2:

```bash
cat ~/.ssh/github-deploy-key.pub >> ~/.ssh/authorized_keys
```

Add the **private key** to GitHub repository:

* Go to **Settings → Secrets and variables → Actions**
* Add secret:
  `EC2_SSH_KEY` → contents of `~/.ssh/github-deploy-key`

Add another secret:

* `EC2_HOST` → your EC2 public DNS
* `EC2_USER` → `ubuntu`

---

### 🔹 Step 2: Create `.github/workflows/deploy.yml`

```yaml
name: Deploy to EC2

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Copy files to EC2
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          source: "."
          target: "/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game"

      - name: Restart Flask App
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart flaskgame
```

✅ After this, every push to `main` automatically redeploys the app.

---

## 🧠 **10. Troubleshooting Quick Reference**

| Issue                    | Cause                           | Fix                                 |
| ------------------------ | ------------------------------- | ----------------------------------- |
| 502 Bad Gateway          | Gunicorn not running            | `sudo systemctl restart flaskgame`  |
| 403 on static files      | Nginx permission issue          | `chmod +x` parent dirs              |
| Page loads but no JS     | Wrong MIME type                 | Check `/static` permissions & alias |
| Socket.IO not connecting | Proxy missing `Upgrade` headers | Check Nginx config                  |
| No Redis connection      | Redis not running               | `sudo systemctl start redis-server` |

---

## ✅ **Final Verification Checklist**

* [x] Nginx proxy passes correctly to port 8000
* [x] Static files load with `200 OK`
* [x] Gunicorn service running under systemd
* [x] Redis server active
* [x] GitHub CI/CD deploys automatically
* [x] Browser console shows active socket connection

---

Would you like me to **generate this as a Markdown file (`DEPLOYMENT_GUIDE.md`)** that you can directly add to your GitHub repo?


---

# 🧾 **Deployment Notes — Flask Socket.IO Game on AWS EC2**

## ⚙️ Overview

This project is a **Flask + Socket.IO + Redis** real-time multiplayer web app.
It was deployed on an **AWS EC2 (Ubuntu 22.04)** instance with **Nginx + Gunicorn + Eventlet** for production.

---

## 🧱 **1. Environment Setup Issues**

### 🔹 Problem

Initial EC2 instance setup required all dependencies for Flask-SocketIO and Gunicorn (with async workers).
Missing system packages and Redis setup caused install or runtime errors.

### 🧩 Fix

Installed all necessary dependencies:

```bash
sudo apt update
sudo apt install python3-venv python3-dev build-essential redis-server nginx git -y
```

Then created a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🧩 **2. Eventlet / Gunicorn Worker Errors**

### 🔹 Problem

`gunicorn -k eventlet` crashed with:

```
ImportError: cannot import name 'ALREADY_HANDLED' from 'eventlet.wsgi'
```

### 🔹 Cause

Incompatible Eventlet + Gunicorn versions.

### 🧩 Fix

Pinned working versions:

```bash
pip install "eventlet==0.33.3" "gunicorn==20.1.0"
```

and ran the server with:

```bash
gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 app:app
```

---

## 🧾 **3. Permission Denied (Port Binding)**

### 🔹 Problem

Systemd log showed:

```
PermissionError: [Errno 13] Permission denied
```

when binding to port `80` or another restricted port.

### 🧩 Fix

Run Gunicorn on a **non-privileged port (8000)**,
and let **Nginx reverse proxy** handle port 80 requests:

```nginx
proxy_pass http://127.0.0.1:8000;
```

---

## 🧱 **4. Nginx 502 Bad Gateway**

### 🔹 Problem

Browser and curl returned:

```
502 Bad Gateway
```

### 🔹 Cause

Gunicorn wasn’t running or failed due to worker issues.

### 🧩 Fix

Checked status:

```bash
sudo systemctl status flaskgame
sudo journalctl -u flaskgame -n 40
```

Then fixed Gunicorn config and ensured it listened on `127.0.0.1:8000`.

---

## 📁 **5. Static Files 403 Forbidden**

### 🔹 Problem

Browser console:

```
Blocked because of a disallowed MIME type (“text/html”)
```

and:

```
HTTP/1.1 403 Forbidden
```

### 🔹 Cause

Nginx didn’t have permission to read `/home/ubuntu/.../static` files.

### 🧩 Fix

Granted read/execute access to all parent directories:

```bash
sudo chmod 755 /home
sudo chmod 755 /home/ubuntu
sudo chmod 755 /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game
sudo chmod -R 755 /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/static
sudo chown -R ubuntu:www-data /home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/static
```

Then reloaded Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

✅ Now `curl -I /static/...` returned `200 OK`.

---

## 🔁 **6. Systemd Service Setup**

### 🔹 File: `/etc/systemd/system/flaskgame.service`

```ini
[Unit]
Description=Flask Socket.IO Game
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game
Environment="PATH=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/venv/bin"
ExecStart=/home/ubuntu/Help-Hinderer-Online-Multiplayer-Game/venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Reloaded and enabled:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flaskgame
sudo systemctl start flaskgame
sudo systemctl status flaskgame
```

---

## ✅ **Final State**

* `http://ec2-XX-XXX-XXX-XX.compute.amazonaws.com/` loads correctly
* Nginx serves static files and proxies API + Socket.IO traffic
* Flask app runs under Gunicorn with Eventlet worker
* Redis handles shared state
* CI/CD connected via GitHub Actions and SSH key

---

## 🧠 **Key Lessons**

1. Always match **Eventlet and Gunicorn versions**.
2. Use **Nginx proxy** for ports <1024 — don’t bind Flask directly.
3. Give **Nginx read + execute permissions** to all parent dirs of `/static`.
4. Use `journalctl -u <service>` for debugging systemd apps.
5. Test with `curl -I` for static file or route accessibility.
6. Verify `socketio` and static assets from browser console (`Network` tab).

---

Would you like me to format this into a Markdown `.md` file you can keep in your repo (e.g. `DEPLOYMENT_NOTES.md`)?

