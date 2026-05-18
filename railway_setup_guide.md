# AquaSol API V2 — Railway Cloud Production Deployment Guide

**Railway** is an exceptional choice for hosting the AquaSol backend. Unlike Render's free tier, **Railway does not have server sleep cycles (cold starts)** on its standard tiers, which makes it perfect for instant IoT telemetry and rapid Flutter app interactions.

Best of all, **Railway does not require your code to be pushed to GitHub!** You can deploy directly from your local computer using the **Railway CLI**.

---

## 🛠️ Step 1: Install the Railway CLI

Run the following command in a local Windows PowerShell terminal to install the Railway CLI on your computer:

```powershell
# Run this inside a Windows PowerShell terminal (not Command Prompt):
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iwr -useb https://railway.app/install.ps1 | iex
```

> [!NOTE]
> Ensure you open **PowerShell** (search "PowerShell" in Windows Start) rather than Command Prompt (`cmd.exe`). If the installation finishes, close and reopen your PowerShell window to refresh your paths before running `railway` commands.

---

## 🔑 Step 2: Authenticate with Railway

1. Sign up/log in to your account at **[railway.app](https://railway.app)**.
2. In your local terminal, run the following command to log in:
   ```bash
   railway login
   ```
   *This will open a secure browser window to authorize your CLI session.*

---

## 📂 Step 3: Initialize Your Project

1. Open your terminal in the root of the backend workspace (`e:\Irrigation_api_V2`):
   ```bash
   cd e:\Irrigation_api_V2
   ```
2. Initialize a new Railway project:
   ```bash
   railway init
   ```
   - Select **"Empty Project"**.
   - Give it a name (e.g., `aquasol-backend`).

---

## 🔒 Step 4: Configure Environment Variables

Railway automatically builds your container using the root `Dockerfile`, but it needs your `.env` variables to connect to the Neon database and run services.

1. Go to your **[Railway Dashboard](https://railway.app/dashboard)** and select your newly initialized project.
2. Click on your service, then navigate to the **Variables** tab.
3. Click **"Raw Editor"** or bulk-add the key-value pairs from your local `.env` file:
   ```env
   PROJECT_NAME="Irrigation_API_2"
   DATABASE_URL="postgresql://neondb_owner:npg_Lbf9rKJHMSW3@ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
   SECRET_KEY="c8e1a39012bc1c65fb2e8d17d3da39160c153bd5afeff7d63a0383556ac04be4"
   GROQ_API_KEY="your_groq_api_key_here"
   WEATHER_API_KEY="48eae0af422bef1f2c57529d8e1beddf"
   UI_API_KEY="your_ui_api_key_here"
   ```

---

## 🚀 Step 5: Deploy the Code

Run this single command in your terminal from `e:\Irrigation_api_V2` to upload, build, and deploy the application:

```bash
railway up
```

### 🔍 What happens under the hood?
1. Railway packages your code directory (automatically respecting `.dockerignore` so it doesn't upload your local virtual environment `venv/` or massive Flutter files).
2. It uploads the directory securely to Railway's cloud builder.
3. It detects the root `Dockerfile`, compiles your dependencies (FastAPI, PyTorch, XGBoost, etc.), and builds the Docker container.
4. It boots the container and links it to their edge router.

---

## 🌐 Step 6: Expose a Public HTTPS URL

Once deployment completes, generate a permanent public domain for your API:

1. In your **[Railway Dashboard](https://railway.app/dashboard)**, click on your backend service.
2. Go to the **Settings** tab.
3. Under the **Public Networking** section, click **"Generate Domain"**.
4. Railway will immediately issue a secure, free SSL public URL (e.g. `https://aquasol-production.up.railway.app`).

### 📱 Connect your Flutter app:
Simply open [api_service.dart](file:///e:/Irrigation_api_V2/aquasol_app/lib/core/services/api_service.dart#L7-L10) and update the `baseUrl` to use this new Railway production URL:
```dart
  static String get baseUrl {
    return 'https://your-railway-domain.up.railway.app/api/v1/';
  }
```

---

## 🛠️ Handy Commands

| Command | Action |
|---------|--------|
| `railway up` | Push code changes and trigger a fresh deployment. |
| `railway logs` | Live stream server runtime logs to your console. |
| `railway status` | Check the current status of your cloud services. |
| `railway open` | Instantly open your Railway project page in your browser. |
