# Backend Docker Build Troubleshooting

## ✅ I've Updated Your Dockerfile

The improved Dockerfile now:
- ✅ Upgrades pip before installing packages
- ✅ Installs build tools for compiled dependencies
- ✅ Sets a longer timeout for slow connections
- ✅ Uses Flask's module runner (more reliable)
- ✅ Sets `PYTHONUNBUFFERED` for real-time logs

---

## 🔨 Build Commands

### Step 1: Build the Image (with verbose output)

Run from your **backend** folder:

```bash
cd backend

# Build with verbose output to see progress
docker build -t middleground-backend:v1 --progress=plain .
```

This will show you each step and help identify where it gets stuck.

---

## 🐛 Troubleshooting Guide

### If you see: `Collecting groq...` hanging for >30 seconds

**Solution**: Your internet or pip cache might be slow.

```bash
# Try building with explicit index URL
docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple/ -t middleground-backend:v1 .
```

### If you see: `error: Microsoft Visual C++ 14.0 is required`

**Solution**: Already fixed in the updated Dockerfile (added build-essential)

### If you see: `No such file or directory: requirements.txt`

**Solution**: Make sure you're running the build command from the **backend** folder

```bash
cd c:\Users\kushp\Downloads\CS4784-Group-2\backend
docker build -t middleground-backend:v1 .
```

### If Docker daemon isn't running

**Solution**: 
- Windows: Open Docker Desktop application
- Verify it's running: `docker ps`

---

## ✅ Verify the Build Succeeded

After the build completes:

```bash
# Check if image exists
docker images | grep middleground-backend

# Should show something like:
# middleground-backend   v1        abc123xyz   2 minutes ago   500MB
```

---

## 🧪 Test the Image Locally

Before pushing to CS Launch, test it locally:

```bash
# Run the backend container
docker run -e GROQ_API_KEY=test-key-12345 -p 5000:5000 middleground-backend:v1

# In another terminal, test the API
curl http://localhost:5000/api/state

# Should return JSON with debate state
```

---

## 📊 Expected Build Output

Your build should look something like this:

```
[+] Building 45.2s (13/13) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 32B
 => [internal] load .dockerignore
 => => transferring context: 2B
 => [1/11] FROM python:3.11-slim
 => => resolve docker.io/library/python:3.11-slim
 => => sha256:abc123... Pull complete
 => [2/11] WORKDIR /app
 => [3/11] RUN apt-get update && apt-get install...
 => [4/11] RUN pip install --upgrade pip setuptools wheel
 => [5/11] COPY requirements.txt .
 => [6/11] RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt
    => # THIS STEP MAY TAKE 30-60 SECONDS - WAIT FOR IT
 => [7/11] COPY . .
 => [8/11] EXPOSE 5000
 => [9/11] ENV PYTHONUNBUFFERED=1
 => [10/11] ENV FLASK_APP=app.py
 => [11/11] CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
 => => naming to docker.io/library/middleground-backend:v1
```

---

## 🚀 Next After Successful Build

Once the image builds successfully:

```bash
# Tag for CS Launch registry
docker tag middleground-backend:v1 container.cs.vt.edu/<username>/middleground-backend:v1

# Push to registry
docker push container.cs.vt.edu/<username>/middleground-backend:v1
```

---

## ⚡ Common Tips

- **Don't stop the build mid-way**: `pip install` can take 30-60 seconds for groq
- **Ensure Docker Desktop is running** (Windows/Mac)
- **Check disk space**: Docker images need ~500MB
- **Restart Docker if stuck**: `docker system prune` and restart Docker Desktop

---

## 📝 If Still Having Issues

Please run this and share the output:

```bash
cd backend
docker build -t middleground-backend:v1 --progress=plain . 2>&1 | head -100
```

This will show us the first 100 lines of the build output where the error likely is.

---

## ✅ Files Updated

- ✅ `backend/Dockerfile` - Optimized for better builds
- ✅ `backend/app.py` - Already configured correctly
- ✅ `backend/requirements.txt` - All dependencies listed

**Ready to build?** Let me know if you hit any errors! 🚀
