# 🚀 Quick Deployment Steps

## Option 1: Railway (Easiest - 5 minutes)

1. **Push to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push
   ```

2. **Go to Railway**: https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Add Environment Variables** (in Railway dashboard):
   ```
   SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
   DEBUG=False
   ALLOWED_HOSTS=*.railway.app
   OPENAI_API_KEY=your-key
   DEEPSEEK_API_KEY=your-key
   LLM_PROVIDER=deepseek
   ```

4. **Add PostgreSQL** (optional but recommended):
   - Click "+ New" → "Database" → "Add PostgreSQL"
   - Railway auto-configures DATABASE_URL

5. **Deploy!** Railway does the rest automatically.

---

## Option 2: Render (Alternative)

1. **Go to Render**: https://render.com
   - Sign up with GitHub
   - Click "New +" → "Web Service"
   - Connect your repo

2. **Configure**:
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start: `gunicorn linkedinposter.wsgi:application`

3. **Add Environment Variables** (same as Railway above)

4. **Add PostgreSQL**:
   - "New +" → "PostgreSQL"
   - Copy Internal Database URL to `DATABASE_URL` env var

5. **Deploy!**

---

## Generate SECRET_KEY

Run this command:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and use it as your `SECRET_KEY` environment variable.

---

## That's it! 🎉

Your app will be live in a few minutes. Check the deployment logs if you encounter any issues.


