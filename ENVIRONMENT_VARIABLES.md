# Environment Variables Guide

This document lists all environment variables needed for the LinkedIn Post Generator application.

## 🔐 Required Environment Variables

### 1. **SECRET_KEY** (REQUIRED - Production)
- **Purpose**: Django's secret key for cryptographic signing
- **Where to get it**: Generate a new one for production
- **How to generate**:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- **Example**: `django-insecure-dev-key-change-in-production-12345` (DO NOT use this in production!)
- **Local Development**: Uses a default insecure key (fine for local only)
- **Production**: MUST be a strong, random key

### 2. **DEBUG** (REQUIRED - Production)
- **Purpose**: Enable/disable Django debug mode
- **Options**: `True` or `False`
- **Local Development**: `True` (default)
- **Production**: MUST be `False`
- **Example**: `DEBUG=False`

### 3. **ALLOWED_HOSTS** (REQUIRED - Production)
- **Purpose**: List of allowed hostnames for the application
- **Format**: Comma-separated list
- **Local Development**: `localhost,127.0.0.1` (default)
- **Production Examples**:
  - Railway: `your-app-name.up.railway.app,*.railway.app`
  - Custom domain: `yourdomain.com,www.yourdomain.com`
- **Example**: `ALLOWED_HOSTS=postforge.up.railway.app,*.railway.app`

### 4. **OPENAI_API_KEY** (REQUIRED if using OpenAI)
- **Purpose**: API key for OpenAI's GPT models
- **Where to get it**: [OpenAI API Keys](https://platform.openai.com/api-keys)
- **Required if**: `LLM_PROVIDER=openai`
- **Example**: `sk-proj-...` (starts with `sk-`)

### 5. **DEEPSEEK_API_KEY** (REQUIRED if using DeepSeek)
- **Purpose**: API key for DeepSeek's models
- **Where to get it**: [DeepSeek API](https://platform.deepseek.com/api_keys)
- **Required if**: `LLM_PROVIDER=deepseek` (default)
- **Example**: `sk-...` (starts with `sk-`)

### 6. **LLM_PROVIDER** (OPTIONAL)
- **Purpose**: Which LLM provider to use
- **Options**: `openai` or `deepseek`
- **Default**: `deepseek`
- **Example**: `LLM_PROVIDER=deepseek`

## 🗄️ Database Variables (Auto-configured on Railway/Render)

### 7. **DATABASE_URL** (AUTO-SET by Railway/Render)
- **Purpose**: PostgreSQL connection string
- **Format**: `postgresql://user:password@host:port/dbname`
- **Local Development**: Not needed (uses SQLite)
- **Production**: Automatically set when you add PostgreSQL service
- **Example**: `postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway`

## 🌐 Optional Environment Variables

### 8. **CORS_ALLOWED_ORIGINS** (OPTIONAL - Production)
- **Purpose**: Restrict CORS to specific origins (for API access from other domains)
- **Format**: Comma-separated list of URLs
- **When needed**: If you want to allow API access from specific frontend domains
- **Example**: `CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com`
- **Note**: If not set, CORS is disabled in production (only same-origin requests allowed)

## 📋 Environment Variables Summary

### For Local Development (.env file)

Create a `.env` file in the project root:

```bash
# Django Settings
SECRET_KEY=django-insecure-dev-key-change-in-production-12345
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# LLM API Keys (choose one provider)
OPENAI_API_KEY=your-openai-key-here
DEEPSEEK_API_KEY=your-deepseek-key-here
LLM_PROVIDER=deepseek

# Database (optional - uses SQLite by default)
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### For Railway Production

In Railway dashboard → Variables tab:

```bash
SECRET_KEY=<generate-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=your-app-name.up.railway.app,*.railway.app
OPENAI_API_KEY=your-openai-key
DEEPSEEK_API_KEY=your-deepseek-key
LLM_PROVIDER=deepseek
# DATABASE_URL is auto-set when you add PostgreSQL
# CORS_ALLOWED_ORIGINS=https://yourdomain.com (optional)
```

### For Render Production

In Render dashboard → Environment tab:

```bash
SECRET_KEY=<generate-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com
OPENAI_API_KEY=your-openai-key
DEEPSEEK_API_KEY=your-deepseek-key
LLM_PROVIDER=deepseek
# DATABASE_URL is auto-set when you add PostgreSQL
```

## 🔒 Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use different SECRET_KEY for production** - Generate a new one
3. **Set DEBUG=False in production** - Critical for security
4. **Rotate API keys periodically** - Especially if exposed
5. **Use Railway/Render secrets** - They're encrypted at rest

## 🧪 Testing Environment Variables

To test if your environment variables are loaded correctly:

```bash
python manage.py shell
>>> import os
>>> from django.conf import settings
>>> print(f"DEBUG: {settings.DEBUG}")
>>> print(f"LLM Provider: {settings.LLM_PROVIDER}")
>>> print(f"Has OpenAI Key: {bool(settings.OPENAI_API_KEY)}")
>>> print(f"Has DeepSeek Key: {bool(settings.DEEPSEEK_API_KEY)}")
```

## 📝 Quick Reference

| Variable | Required | Default | Production |
|----------|----------|---------|------------|
| `SECRET_KEY` | ✅ Yes | Insecure dev key | ✅ Strong random key |
| `DEBUG` | ✅ Yes | `True` | ✅ `False` |
| `ALLOWED_HOSTS` | ✅ Yes | `localhost,127.0.0.1` | ✅ Your domain |
| `OPENAI_API_KEY` | ⚠️ If using OpenAI | - | ✅ Your key |
| `DEEPSEEK_API_KEY` | ⚠️ If using DeepSeek | - | ✅ Your key |
| `LLM_PROVIDER` | ❌ No | `deepseek` | Optional |
| `DATABASE_URL` | ❌ No | SQLite | ✅ Auto-set |
| `CORS_ALLOWED_ORIGINS` | ❌ No | - | Optional |

