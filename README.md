# Algo Worker Service (Railway Deployment)

This service runs the NIFTY safe demo algo 24/7 on Railway.

## Before Deploying
Update your backend URL inside `angel_nifty_safe_algo_demo.py`:

BACKEND_URL = "https://your-backend.up.railway.app/api/update"

## Deploy to Railway
1. Push this folder to a GitHub repository.
2. Go to https://railway.app → New Project → Deploy from GitHub.
3. Select this repo.
4. Railway will run the algo automatically as a background worker.

Logs will appear inside Railway → Service Logs.
