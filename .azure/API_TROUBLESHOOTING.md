# API Communication Troubleshooting

## 🔍 First: Check Your Browser Console

1. Open your frontend at `https://middleground.discovery.cs.vt.edu` (or wherever it's hosted)
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Look for any red error messages
5. Share those errors with me

Common errors and what they mean:
- **"Failed to fetch"** - Network error, backend not accessible
- **"CORS error"** - Backend blocking requests from frontend
- **"404 Not Found"** - Wrong API endpoint URL

---

## 🔴 Issue 1: Backend Not Deployed Yet

If you see errors trying to reach `https://arbiter.discovery.cs.vt.edu`, it means the backend isn't deployed.

**Steps to deploy backend to CS Launch:**

1. Go to https://launch.cs.vt.edu/
2. Click **Discovery** cluster
3. Click **Workloads** → **Create** → **Deployment**
4. Fill in:
   - **Namespace**: `middleground`
   - **Name**: `backend-deployment`
   - **Container Image**: `container.cs.vt.edu/kushpatel225/debater:backend1`
   - Click **Add Port or Service**:
     - **Service Type**: ClusterIP
     - **Name**: `http`
     - **Private Container Port**: `5000`
5. Click **Environment Variables** → **Add Variable**:
   - **Variable Name**: `GROQ_API_KEY`
   - Paste your actual GROQ API key
6. Click **Create**

Then create an ingress for the backend:
1. Click **Service Discovery** → **Ingresses** → **Create**
2. Fill in:
   - **Namespace**: `middleground`
   - **Name**: `backend-ingress`
   - **Request Host**: `arbiter.discovery.cs.vt.edu`
   - **Path**: `/`
   - **Target Service**: `backend-deployment`
   - **Port**: `5000`
3. Click **Create**

Wait 2-3 minutes for it to deploy and get a public IP.

---

## 🔴 Issue 2: CORS Problem

If you see **CORS errors** in console, the backend is blocking requests from the frontend domain.

**Fix: Update CORS in backend**

Edit `backend/app.py` and change the CORS configuration:

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow specific frontend domain
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://middleground.discovery.cs.vt.edu"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

Then rebuild and push the image:

```bash
# Rebuild backend
cd backend
docker build -t container.cs.vt.edu/kushpatel225/debater:backend2 .

# Push
docker push container.cs.vt.edu/kushpatel225/debater:backend2

# In CS Launch, update the deployment to use :backend2 tag
```

---

## 🔴 Issue 3: Wrong API URL in Frontend

If frontend is running locally (not on CS Launch), it might still be pointing to `https://arbiter.discovery.cs.vt.edu`, which doesn't exist yet.

**For local testing:**

Temporarily update the frontend to point to `http://localhost:5000`:

Edit `frontend/Middle_Ground/src/pages/PersonScreen.jsx`:

```javascript
const API_BASE = 'http://localhost:5000'  // For local testing
```

Then run backend locally:
```bash
cd backend
python -m flask run
```

And frontend locally:
```bash
cd frontend/Middle_Ground
npm run dev
```

Visit `http://localhost:5173/` and test.

Once CS Launch deployment is working, change it back to:
```javascript
const API_BASE = 'https://arbiter.discovery.cs.vt.edu'
```

---

## ✅ Debug Checklist

- [ ] Opened browser console (F12)
- [ ] Checked console for error messages
- [ ] Backend deployed to CS Launch and ingress created
- [ ] Backend ingress URL is `https://arbiter.discovery.cs.vt.edu`
- [ ] Frontend ingress URL is `https://middleground.discovery.cs.vt.edu`
- [ ] GROQ_API_KEY environment variable is set in backend deployment
- [ ] Can ping backend: `curl https://arbiter.discovery.cs.vt.edu/api/state`

---

## 🧪 Quick Test

If both frontend and backend are running (local or cloud), test the API directly:

```bash
# Test backend is responding
curl -X GET https://arbiter.discovery.cs.vt.edu/api/state

# Test sending a message
curl -X POST https://arbiter.discovery.cs.vt.edu/api/chat/a \
  -H "Content-Type: application/json" \
  -d '{"message":"My argument is..."}'
```

If these work, the backend is fine and it's a frontend issue.

---

## 📋 What I Need From You

Please share:
1. **Browser console errors** (screenshot or copy-paste)
2. **Frontend URL** where you're testing
3. **Backend URL** where backend is deployed
4. **Result of**: `curl https://arbiter.discovery.cs.vt.edu/api/state`

With this info, I can pinpoint the exact issue! 🚀
