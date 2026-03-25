# Deploy MiddleGround to CS Launch

## Overview

CS Launch is Virginia Tech's Kubernetes platform for CS department projects. It provides:
- ✅ Free hosting for CS members
- ✅ Automatic HTTPS (TLS certificates)
- ✅ Public URLs like `myapp.discovery.cs.vt.edu`
- ✅ No credit card needed (unlike cloud providers)

---

## Prerequisites

1. **CS Account** - You have a Virginia Tech CS account
2. **Access to a Cluster** - You need to be granted access to either:
   - **Discovery** (General teaching projects - recommended for students)
   - **Endeavour** (Long-term projects with GPU support - Faculty/Staff only)
3. **Docker Images** - Your app must be containerized (Dockerfiles created)
4. **Container Registry Access** - Access to `container.cs.vt.edu`

---

## System Architecture for CS Launch

```
┌──────────────────────────────────────────┐
│  Frontend Ingress                        │
│  myapp.discovery.cs.vt.edu               │
└───────────────┬──────────────────────────┘
                │ HTTPS (automatic TLS)
                ▼
┌──────────────────────────────────────────┐
│  Frontend Deployment (Node.js)           │
│  React app built with Vite               │
│  Port: 3000                              │
└──────────────┬──────────────────────────┘
               │ HTTP Internal
               ▼
┌──────────────────────────────────────────┐
│  Backend Ingress (optional)              │
│  api-myapp.discovery.cs.vt.edu           │
└───────────────┬──────────────────────────┘
                │ HTTPS (automatic TLS)
                ▼
┌──────────────────────────────────────────┐
│  Backend Deployment (Python Flask)       │
│  API endpoints                           │
│  Port: 5000                              │
└──────────────┬──────────────────────────┘
               │ Uses Secret
               ▼
┌──────────────────────────────────────────┐
│  Secret: groq-api-key                    │
│  Stores GROQ_API_KEY securely            │
└──────────────────────────────────────────┘
```

---

## Step 1: Create Dockerfiles

### Backend Dockerfile
Create: `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
```

### Frontend Dockerfile
Create: `frontend/Middle_Ground/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/dist ./dist
RUN npm install -g serve

EXPOSE 3000

ENV NODE_ENV=production

CMD ["serve", "-s", "dist", "-l", "3000"]
```

---

## Step 2: Verify Backend Configuration

Update `backend/app.py` - ensure the last lines are:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

---

## Step 3: Build Docker Images

From your project root:

```bash
# Build backend
cd backend
docker build -t container.cs.vt.edu/<username>/middleground-backend:v1 .

# Build frontend  
cd ../frontend/Middle_Ground
docker build -t container.cs.vt.edu/<username>/middleground-frontend:v1 .
```

> Replace `<username>` with your CS username

---

## Step 4: Push Images to Container Registry

```bash
# Login to registry (you need credentials - ask CS techstaff if needed)
docker login container.cs.vt.edu

# Push images
docker push container.cs.vt.edu/<username>/middleground-backend:v1
docker push container.cs.vt.edu/<username>/middleground-frontend:v1
```

---

## Step 5: Create Project & Namespace on CS Launch

### Via Web UI:

1. Go to https://launch.cs.vt.edu/
2. Login with your CS username/password
3. Click on **Discovery** cluster (or Endeavour if you have access)
4. Click **Projects/Namespaces** → **Create Project**
5. Name it: `middleground-project`
6. Click **Create Project**
7. Click **Create Namespace** 
8. Name it: `middleground`
9. Click **Create**

---

## Step 6: Create Secret for GROQ API Key

### Via Web UI:

1. Go to Cluster Dashboard
2. Click **Storage** → **Secrets** → **Create**
3. Select **Opaque** tile
4. **Name**: `groq-secret`
5. **Key**: `GROQ_API_KEY`
6. **Value**: `your_groq_key_here` (paste your actual key)
7. Click **Create**

---

## Step 7: Deploy Backend Service

### Via Web UI:

1. Click **Workloads** → **Create** → Select **Deployment**
2. **Namespace**: `middleground`
3. Click **pod** tab
4. **Pod Name**: `backend-pod`
5. Click **container-0** tab
6. **Name**: `backend`
7. **Container Image**: `container.cs.vt.edu/<username>/middleground-backend:v1`
8. Click **Add Port or Service**
   - **Service Type**: ClusterIP
   - **Name**: `backend-port`
   - **Private Container Port**: `5000`
   - **Container Port**: `5000`
9. Click **Environment Variables** → **Add Variable**
   - **Variable Name**: `GROQ_API_KEY`
   - **Value from Secret**: Select `groq-secret` and key `GROQ_API_KEY`
10. Click **Create**

---

## Step 8: Create Ingress for Backend (Optional)

For direct API access, create an ingress:

1. Click **Service Discovery** → **Ingresses** → **Create**
2. **Namespace**: `middleground`
3. **Name**: `backend-ingress`
4. **Request Host**: `api-middleground.discovery.cs.vt.edu` (or `api-middleground.endeavour.cs.vt.edu`)
5. **Path**: `/` (Prefix)
6. **Target Service**: Select your backend deployment
7. **Port**: `5000`
8. Click **Create**

---

## Step 9: Deploy Frontend Service

### Via Web UI:

1. Click **Workloads** → **Create** → Select **Deployment**
2. **Namespace**: `middleground`
3. Click **pod** tab
4. **Pod Name**: `frontend-pod`
5. Click **container-0** tab
6. **Name**: `frontend`
7. **Container Image**: `container.cs.vt.edu/<username>/middleground-frontend:v1`
8. Click **Add Port or Service**
   - **Service Type**: ClusterIP
   - **Name**: `frontend-port`
   - **Private Container Port**: `3000`
   - **Container Port**: `3000`
9. Click **Create**

---

## Step 10: Create Public Ingress for Frontend

1. Click **Service Discovery** → **Ingresses** → **Create**
2. **Namespace**: `middleground`
3. **Name**: `frontend-ingress`
4. **Request Host**: `middleground.discovery.cs.vt.edu` (or use `middleground.endeavour.cs.vt.edu`)
5. **Path**: `/` (Prefix)
6. **Target Service**: Select your frontend deployment
7. **Port**: `3000`
8. Click **Create**

---

## Step 11: Update Frontend API Endpoints

Your frontend needs to know where the backend API is:

### For React Components

Update any API calls from:
```javascript
// OLD (localhost)
const response = await fetch('http://localhost:5000/api/...');
```

To:
```javascript
// NEW (CS Launch)
const response = await fetch('https://api-middleground.discovery.cs.vt.edu/api/...');
```

Or use an environment variable approach:
```javascript
const API_URL = process.env.REACT_APP_API_URL || 'https://api-middleground.discovery.cs.vt.edu';
const response = await fetch(`${API_URL}/api/...`);
```

---

## 🎉 Done!

Your app will be accessible at:
- **Frontend**: `https://middleground.discovery.cs.vt.edu`
- **Backend API**: `https://api-middleground.discovery.cs.vt.edu` (if you created the backend ingress)

---

## ✅ Verification Checklist

- [ ] Project created on CS Launch
- [ ] Namespace created
- [ ] Dockerfiles created and tested locally
- [ ] Images built and pushed to container registry
- [ ] GROQ_API_KEY secret created
- [ ] Backend deployment running
- [ ] Frontend deployment running
- [ ] Frontend ingress created and accessible
- [ ] Backend ingress created (optional)
- [ ] Frontend API endpoints updated to point to backend
- [ ] Application tests from public URL

---

## 📝 Troubleshooting

### Deployment won't start?
- Check Workloads → Deployments → View logs
- Verify container image path is correct
- Ensure registry credentials are set if using private registry

### API calls failing?
- Verify ingress URLs in frontend code match created ingresses
- Check backend logs for errors
- Ensure GROQ_API_KEY is correctly set

### GROQ_API_KEY not working?
- Re-create secret with correct value
- Restart deployment pods after updating secret

### Can't push images to registry?
- Contact CS Techstaff for registry access
- Ensure you're logged in: `docker login container.cs.vt.edu`

---

## 🔗 Useful Links

- **CS Launch**: https://launch.cs.vt.edu/
- **CS Launch Docs**: https://wiki.cs.vt.edu/index.php/HowTo:CS_Launch
- **CS Launch Ingress**: https://wiki.cs.vt.edu/index.php/CS_Launch_Ingress
- **Docker Guide**: https://wiki.cs.vt.edu/index.php/HowTo:Docker
- **Contact Techstaff**: https://wiki.cs.vt.edu/index.php/Contact_Techstaff

---

## Next Steps

1. ✅ Create the Dockerfiles (from Step 1)
2. ✅ Build and test locally with Step 3
3. ✅ Push images to registry (Step 4)
4. ✅ Create project and namespace (Step 5)
5. ✅ Deploy to CS Launch (Steps 6-10)

Would you like me to help automate any of these steps?
