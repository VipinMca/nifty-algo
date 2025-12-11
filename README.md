# Dashboard Backend (Railway Deployment)

This service hosts the backend API for your algo dashboard.

## Deploy to Railway
1. Push this folder to a GitHub repository.
2. Go to https://railway.app → New Project → Deploy from GitHub.
3. Select this repository.
4. Railway will automatically install dependencies and deploy.

After deployment, your backend API URL will look like:
https://your-backend.up.railway.app

Use the `/api/update` endpoint for the algo to send live data.
Use the `/api/status` endpoint for dashboard.html to fetch live status.
