# Containerization Plan

## Goal
Prepare Docker containers for both your backend (Flask) and frontend (React) services to deploy to Azure.

## Services to Containerize

### 1. **Backend Service**
- **Location**: `/backend`
- **Language**: Python 3.x
- **Framework**: Flask
- **Entry Point**: `app.py`
- **Key Dependencies**:
  - Flask with CORS
  - Groq Python client
  - python-dotenv for environment variables
- **Environment Variables**: `GROQ_API_KEY`

### 2. **Frontend Service**  
- **Location**: `/frontend/Middle_Ground`
- **Language**: JavaScript (Node.js)
- **Framework**: React 19 + Vite
- **Build Command**: `npm run build`
- **Entry Point**: `index.html`
- **Dependencies**: React, React DOM

---

## Execution Steps

### Step 1: Install Prerequisites
```bash
# Check if Docker is installed
docker --version

# If not installed, download from https://www.docker.com/products/docker-desktop/
```

### Step 2: Create Dockerfiles

#### Backend Dockerfile
Create `backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Flask default is 5000)
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
```

#### Frontend Dockerfile
Create `frontend/Middle_Ground/Dockerfile`:
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the React app
RUN npm run build

# Production stage - Serve with Node
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Install serve to run the app
RUN npm install -g serve

EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "dist", "-l", "3000"]
```

### Step 3: Update Backend `app.py`

Make sure Flask listens on all interfaces and correct port:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

### Step 4: Build Docker Images Locally

```bash
# Build backend image
cd backend
docker build -t middleground-backend:1.0 .

# Build frontend image  
cd ../frontend/Middle_Ground
docker build -t middleground-frontend:1.0 .
```

### Step 5: Test Images Locally (Optional)

```bash
# Test backend (need GROQ_API_KEY)
docker run -e GROQ_API_KEY=your_key_here -p 5000:5000 middleground-backend:1.0

# Test frontend
docker run -p 3000:3000 middleground-frontend:1.0
```

---

## Configuration Notes

### Backend (Flask)
- **Port**: 5000 (configurable)
- **CORS enabled** for frontend communication
- **Environment Variables**:
  - `GROQ_API_KEY` - Required for LLM functionality
  - Optional: `FLASK_ENV`, `PORT`

### Frontend (React)
- **Port**: 3000
- **Need to update API endpoint** to point to deployed backend URL
- Update in `frontend/Middle_Ground/src/` - look for API calls and change from `localhost:5000` to your Azure backend URL

---

## Security Considerations

✅ **Do NOT hardcode secrets** - Use environment variables  
✅ **Store API keys in Azure Key Vault** - Retrieved at runtime  
✅ **Use HTTPS only** - Azure App Service provides this automatically  
✅ **Enable CORS properly** - Only allow frontend domain  

---

## Deployment Integration

Once Dockerfiles are created, you can either:

1. **Push to Azure Container Registry** and deploy from there
2. **Use App Service direct deployment** with GitHub Actions
3. **Use Azure Container Apps** for containerized deployment

The main deployment plan will handle all of this automatically!

---

## Files to Create/Modify

- [ ] Create `backend/Dockerfile`
- [ ] Create `frontend/Middle_Ground/Dockerfile`
- [ ] Update `backend/app.py` to run on all interfaces
- [ ] Update frontend API endpoints (if hardcoded)
- [ ] Create `.dockerignore` files to exclude unnecessary files

---

## Next: Execute Deployment Plan

Once Dockerfiles are ready, run the Azure deployment to provision resources and deploy your app!
