# CS Launch Deployment - Quick Command Reference

> **Replace `<username>` with your CS username throughout these commands**

---

## 🐳 Build Docker Images

```bash
# Build backend image
cd backend
docker build -t container.cs.vt.edu/<username>/middleground-backend:v1 .

# Build frontend image
cd ../frontend/Middle_Ground
docker build -t container.cs.vt.edu/<username>/middleground-frontend:v1 .
```

---

## 🚀 Push Images to Registry

```bash
# Login first (ask CS techstaff for credentials if needed)
docker login container.cs.vt.edu

# Push backend
docker push container.cs.vt.edu/<username>/middleground-backend:v1

# Push frontend
docker push container.cs.vt.edu/<username>/middleground-frontend:v1
```

---

## 📋 Web UI Steps (Simplified)

### 1. Create Project & Namespace
```
launch.cs.vt.edu 
→ Login 
→ Discovery cluster 
→ Projects/Namespaces 
→ Create Project (name: middleground-project)
→ Create Namespace (name: middleground)
```

### 2. Create Secret
```
Storage 
→ Secrets 
→ Create 
→ Opaque 
→ Name: groq-secret
→ Key: GROQ_API_KEY
→ Value: <your_groq_key>
```

### 3. Deploy Backend
```
Workloads 
→ Create 
→ Deployment
→ Namespace: middleground
→ Name: backend-deployment
→ Container Image: container.cs.vt.edu/<username>/middleground-backend:v1
→ Service Type: ClusterIP
→ Port: 5000
→ Add Environment Variable from Secret: GROQ_API_KEY
```

### 4. Create Backend Ingress (Optional)
```
Service Discovery 
→ Ingresses 
→ Create
→ Name: backend-ingress
→ Host: api-middleground.discovery.cs.vt.edu
→ Path: /
→ Target: backend-deployment
→ Port: 5000
```

### 5. Deploy Frontend
```
Workloads 
→ Create 
→ Deployment
→ Namespace: middleground
→ Name: frontend-deployment
→ Container Image: container.cs.vt.edu/<username>/middleground-frontend:v1
→ Service Type: ClusterIP
→ Port: 3000
```

### 6. Create Frontend Ingress
```
Service Discovery 
→ Ingresses 
→ Create
→ Name: frontend-ingress
→ Host: middleground.discovery.cs.vt.edu
→ Path: /
→ Target: frontend-deployment
→ Port: 3000
```

---

## 🔧 Update Frontend API Endpoint

In your React components, change API calls:

**Before (localhost):**
```javascript
fetch('http://localhost:5000/api/debate')
```

**After (CS Launch):**
```javascript
fetch('https://api-middleground.discovery.cs.vt.edu/api/debate')
```

Or using environment variables:
```javascript
const API = process.env.REACT_APP_API_URL || 'https://api-middleground.discovery.cs.vt.edu';
fetch(`${API}/api/debate`)
```

---

## 🎯 Your Public URLs

Once deployed:
- **Frontend**: `https://middleground.discovery.cs.vt.edu`
- **Backend API**: `https://api-middleground.discovery.cs.vt.edu` (if ingress created)

---

## 🐛 Check Logs

```
Workloads 
→ Deployments 
→ Select deployment
→ View logs
```

---

## 📝 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Pod won't start | Check image path is correct in deployment |
| 404 on ingress | Verify ingress target service matches deployment name |
| API not accessible | Make sure backend ingress is created |
| GROQ_API_KEY not working | Re-create secret, restart pod |
| Can't push images | Run `docker login container.cs.vt.edu` |

---

## ⏱️ Timeline

- **Step 1-2**: ~5 min (build & push images)
- **Step 3-6**: ~10 min (web UI configuration)
- **Step 7**: ~5 min (update frontend code)
- **Total**: ~20 minutes from start to public URL

---

## 🆘 Need Help?

- **CS Techstaff**: https://wiki.cs.vt.edu/index.php/Contact_Techstaff
- **Wiki**: https://wiki.cs.vt.edu/index.php/HowTo:CS_Launch
- **Questions**: Ask in class or Discord

---

## ✅ Step-by-Step Checklist

- [ ] Docker installed locally
- [ ] Dockerfiles created
- [ ] Images built successfully
- [ ] Registry credentials obtained
- [ ] Images pushed to container registry
- [ ] Project created on CS Launch
- [ ] Namespace created
- [ ] Secret created (GROQ_API_KEY)
- [ ] Backend deployment created
- [ ] Backend ingress created (optional)
- [ ] Frontend deployment created
- [ ] Frontend ingress created
- [ ] Frontend API endpoint updated
- [ ] Test at https://middleground.discovery.cs.vt.edu ✨
