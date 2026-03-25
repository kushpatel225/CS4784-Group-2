# Docker Build Network Error - Solutions

## ❌ The Problem

Docker can't reach `docker.io` to download the Python base image. This could be:
- Docker daemon not running properly
- Network/VPN blocking Docker Hub
- University firewall restrictions
- DNS issues

---

## ✅ Solution 1: Restart Docker Desktop (Quickest Fix)

### For Windows:
1. Open **Docker Desktop** application
2. Click the whale icon in system tray
3. Click **Restart**
4. Wait 30 seconds
5. Try building again:

```bash
cd backend
docker build -t middleground-backend:v1 .
```

---

## ✅ Solution 2: Check Docker Can Reach Internet

Run these commands to diagnose:

```bash
# Check if Docker daemon is running
docker ps

# Try to ping Docker Hub
docker run hello-world

# Check Docker system info
docker system info

# Check DNS resolution
docker run alpine nslookup docker.io
```

If any of these fail, Docker daemon isn't working properly.

---

## ✅ Solution 3: You're Behind a Firewall/VPN

If you're on Virginia Tech campus network or VPN:

### Option A: Use HTTP instead of HTTPS
```bash
docker build --build-arg HTTP_PROXY=http://proxy:8080 -t middleground-backend:v1 .
```

### Option B: Configure Docker daemon

Edit Docker daemon settings (Docker Desktop):
1. Open Docker Desktop
2. Settings → Docker Engine
3. Add this configuration:

```json
{
  "registry-mirrors": [
    "https://mirror.gcr.io",
    "https://daocloud.io/mirror"
  ],
  "insecure-registries": []
}
```

4. Click **Apply & Restart**
5. Wait for restart
6. Try building again

---

## ✅ Solution 4: Use Alternative Base Image

If you're still having issues, use a different Python image source:

Edit `backend/Dockerfile` and change line 1 from:

```dockerfile
FROM python:3.11-slim
```

To one of these alternatives:

```dockerfile
# Option A: Alpine Linux (smallest, fastest)
FROM python:3.11-alpine

# Option B: Full Debian image
FROM python:3.11-bullseye

# Option C: Use a mirror
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim
```

Then try building:
```bash
docker build -t middleground-backend:v1 .
```

---

## ✅ Solution 5: Clear Docker Cache & Try Again

Sometimes Docker cache gets corrupted:

```bash
# Clear everything
docker system prune -a

# Try building again (it will download fresh)
docker build -t middleground-backend:v1 .
```

---

## ✅ Solution 6: Build Without Docker Desktop

If Docker Desktop keeps failing, use **Docker CLI only**:

### For Windows with WSL2:
```bash
# Open PowerShell and enable WSL2
wsl --update

# Then build from WSL terminal
docker build -t middleground-backend:v1 .
```

---

## 🔍 Specific to Virginia Tech

Since you're using CS Launch (Virginia Tech), check:

1. **Are you on campus or VPN?** 
   - Try disconnecting VPN and building
   - University firewalls sometimes block Docker Hub

2. **Ask CS Techstaff** if there's a proxy you need to configure

3. **Use CS Stash instead** (Virginia Tech's local storage)

---

## 📋 Step-by-Step Fix Guide

### Try in this order:

1. **Restart Docker Desktop** (60 second wait)
   ```bash
   docker ps
   ```

2. **If that fails: Clear cache**
   ```bash
   docker system prune -a
   docker build -t middleground-backend:v1 .
   ```

3. **If still failing: Change base image**
   - Edit `backend/Dockerfile` line 1
   - Use `FROM python:3.11-alpine` instead
   - Try building again

4. **If dockers keeps failing: Use Python from scratch**
   - Contact CS Techstaff
   - Ask about using pre-built Python containers in CS registry

---

## 🆘 If Nothing Works

Download a **pre-built Python image** from your local CS registry:

Ask CS Techstaff if they have pre-cached Python images at:
```
container.cs.vt.edu/library/python:3.11-slim
```

Then change your Dockerfile line 1 to:
```dockerfile
FROM container.cs.vt.edu/library/python:3.11-slim
```

---

## ✅ Quick Test

Once Docker is working, verify with:

```bash
# Should run without errors
docker pull python:3.11-slim

# Should output "Hello from Docker!"
docker run hello-world
```

---

## 📞 Next Steps

1. **Try Solution 1** (restart Docker Desktop) - 5 minutes
2. **If fails, try Solution 3** (check if on campus/VPN) - 2 minutes  
3. **If fails, try Solution 4** (use alpine image) - 1 minute to edit
4. **If still failing, contact CS Techstaff** with screenshot of error

---

Let me know which solution works or if you hit another error! 🚀
