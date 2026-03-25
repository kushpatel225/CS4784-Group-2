# Quick Start: Deploy to Azure in 5 Steps

## 🎯 Goal
Get your MiddleGround app live on the cloud in the fastest way possible.

---

## Step 1: Prepare Your Azure Account
```bash
# Install Azure CLI
# Windows: Download from https://aka.ms/installazurecliwindows
# or use: choco install azure-cli (if using Chocolatey)

# Login to Azure
az login

# Verify subscription
az account show
# Note: you need subscriptionId from output
```

**⏱️ Time: ~5 minutes**

---

## Step 2: Create Dockerfiles (Copy & Paste)

### Backend Dockerfile
Create file: `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENV FLASK_APP=app.py
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
```

### Frontend Dockerfile  
Create file: `frontend/Middle_Ground/Dockerfile`

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
CMD ["serve", "-s", "dist", "-l", "3000"]
```

**⏱️ Time: ~2 minutes**

---

## Step 3: Update Backend File

Open `backend/app.py` and ensure the last line is:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

**⏱️ Time: ~1 minute**

---

## Step 4: Deploy to Azure

Run this command from your project root:

```bash
# Get your subscription ID (from Step 1)
SUBSCRIPTION_ID="your-subscription-id"

# Create resource group
az group create --name cs4784-rg --location eastus

# Create App Service Plan (backend)
az appservice plan create \
  --name cs4784-backend-plan \
  --resource-group cs4784-rg \
  --sku B1 \
  --is-linux

# Create Flask App Service
az webapp create \
  --resource-group cs4784-rg \
  --plan cs4784-backend-plan \
  --name cs4784-backend-app \
  --runtime "PYTHON|3.11"

# Set environment variable for Groq API key
az webapp config appsettings set \
  --resource-group cs4784-rg \
  --name cs4784-backend-app \
  --settings GROQ_API_KEY="your_groq_key_here"

# Deploy backend from local files
cd backend
az webapp deployment method list
cd ..
```

**⏱️ Time: ~10-15 minutes**

---

## Step 5: Get Your Public URL

```bash
# Check the backend URL
az webapp show \
  --resource-group cs4784-rg \
  --name cs4784-backend-app \
  --query "defaultHostName" --output tsv

# Check the frontend URL  
az webapp show \
  --resource-group cs4784-rg \
  --name cs4784-frontend-app \
  --query "defaultHostName" --output tsv
```

Your app will be accessible at: `https://<app-name>.azurewebsites.net`

**⏱️ Time: ~1 minute**

---

## 🎉 Done!

Your app is now live! You can:
- ✅ Share the link with anyone
- ✅ Access from any device  
- ✅ Run 24/7 without your computer
- ✅ Use custom domain (optional)

---

## 📍 Troubleshooting

### App not starting?
```bash
# Check logs
az webapp log tail \
  --resource-group cs4784-rg \
  --name cs4784-backend-app
```

### Need to update code?
```bash
# Make changes, commit, and push
git add .
git commit -m "Update app"
git push

# Redeploy
az webapp up --resource-group cs4784-rg --name cs4784-backend-app
```

### API key not working?
```bash
# Update API key
az webapp config appsettings set \
  --resource-group cs4784-rg \
  --name cs4784-backend-app \
  --settings GROQ_API_KEY="new_key_here"
```

---

## 💰 Costs

**Azure free tier** includes:
- ✅ 750 hours/month of B1 App Service
- ✅ 1 GB storage
- ✅ Perfect for testing/development

**Beyond free tier:**
- B1 plan: ~$15/month per App Service
- Total for 2 apps: ~$30/month

---

## ⚡ Next Steps

1. **Automate Deployment**: Set up GitHub Actions for automatic deployment when you push code
2. **Add Custom Domain**: Use your own domain name
3. **Scale Up**: Upgrade to higher tier if needed
4. **Add Monitoring**: Set up Application Insights for performance tracking

Need help? Ask me anytime! 🚀
