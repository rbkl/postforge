# Deployment Guide - LinkedIn Poster

This guide will help you deploy your LinkedIn Poster application to the cloud. We'll use **Railway** (easiest option) or **Render** (alternative).

## 🚀 Quick Start: Deploy to Railway (Recommended - Easiest)

Railway is the easiest option - it handles most configuration automatically.

### Step 1: Prepare Your Code

1. **Update requirements.txt** (already done - includes all dependencies)

2. **Create a `.gitignore` file** (if you don't have one):
```bash
# Add to .gitignore
.env
*.pyc
__pycache__/
db.sqlite3
media/
venv/
*.log
```

### Step 2: Sign Up for Railway

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (easiest)
3. Click "New Project"
4. Select "Deploy from GitHub repo"

### Step 3: Connect Your Repository

1. Authorize Railway to access your GitHub
2. Select your `linkedinposter` repository
3. Railway will automatically detect it's a Python/Django app

### Step 4: Configure Environment Variables

In Railway dashboard, go to your project → Variables tab, and add:

```
SECRET_KEY=your-secret-key-here-generate-a-random-one
DEBUG=False
ALLOWED_HOSTS=your-app-name.up.railway.app,*.railway.app
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
LLM_PROVIDER=deepseek
```

**To generate a SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 5: Add PostgreSQL Database (Optional but Recommended)

1. In Railway dashboard, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically set `DATABASE_URL` environment variable
4. The app will automatically use it (settings.py is already configured)

### Step 6: Deploy!

1. Railway will automatically build and deploy
2. Wait for deployment to complete (usually 2-3 minutes)
3. Your app will be live at `https://your-app-name.up.railway.app`

### Step 7: Run Migrations

In Railway dashboard:
1. Go to your service
2. Click "Deployments" tab
3. Click on the latest deployment
4. Click "View Logs"
5. Or use Railway CLI:
```bash
railway run python manage.py migrate
```

### Step 8: Collect Static Files

Railway will automatically run the build command which includes collecting static files.

---

## 🌐 Alternative: Deploy to Render

### Step 1: Sign Up

1. Go to [render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Create New Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select your `linkedinposter` repo

### Step 3: Configure Build Settings

- **Name**: linkedinposter (or your choice)
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command**: `gunicorn linkedinposter.wsgi:application`

### Step 4: Add Environment Variables

In the "Environment" section, add:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
LLM_PROVIDER=deepseek
```

### Step 5: Add PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Create database
3. Copy the "Internal Database URL"
4. Add to environment variables as `DATABASE_URL`

### Step 6: Deploy

Click "Create Web Service" and wait for deployment.

---

## 📋 Pre-Deployment Checklist

- [ ] Update `requirements.txt` (includes gunicorn, whitenoise)
- [ ] Update `settings.py` for production (see below)
- [ ] Set `DEBUG=False` in production
- [ ] Generate and set `SECRET_KEY`
- [ ] Add all API keys to environment variables
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up database (PostgreSQL recommended)
- [ ] Run migrations
- [ ] Collect static files

---

## 🔧 Required Code Changes

The deployment files have been created for you. You just need to:

1. **Update settings.py** - Already configured to work with Railway/Render
2. **Add gunicorn to requirements.txt** - Already added
3. **Create Procfile** - Already created

---

## 🗄️ Database Migration (SQLite → PostgreSQL)

If you're using PostgreSQL (recommended for production):

1. Railway/Render will automatically set `DATABASE_URL`
2. The app will automatically use PostgreSQL if `DATABASE_URL` is set
3. Run migrations: `python manage.py migrate`

---

## 📁 Static Files & Media

- **Static files**: Automatically collected and served via WhiteNoise
- **Media files**: For production, consider using:
  - AWS S3
  - Cloudinary
  - Railway's volume storage (for Railway)

---

## 🔐 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` set
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] API keys stored as environment variables (never in code)
- [ ] HTTPS enabled (automatic on Railway/Render)

---

## 🐛 Troubleshooting

### Issue: Static files not loading
**Solution**: Make sure `collectstatic` runs during build. It's included in the Procfile.

### Issue: Database errors
**Solution**: Make sure migrations run. Use Railway CLI or Render shell to run `python manage.py migrate`

### Issue: 500 errors
**Solution**: Check logs in Railway/Render dashboard. Usually it's missing environment variables.

### Issue: Media files not saving
**Solution**: For production, use cloud storage (S3, Cloudinary) instead of local filesystem.

---

## 📞 Need Help?

- Railway Docs: https://docs.railway.app
- Render Docs: https://render.com/docs
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/

---

## 🎉 You're Done!

Once deployed, your app will be live and accessible from anywhere. Share the URL with users!


