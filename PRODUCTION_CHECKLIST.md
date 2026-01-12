# Production Deployment Checklist

## 🔐 Authentication & Security

✅ **Completed:**
- User authentication system (login/register/logout)
- All API endpoints protected with `IsAuthenticated`
- User data isolation (users can only see their own data)
- Security headers configured for production
- CSRF protection enabled
- Secure session cookies
- CORS properly configured

## 📋 Pre-Deployment Steps

### 1. Environment Variables (Railway)

Add these in Railway dashboard → Variables:

```
SECRET_KEY=<generate-strong-key>
DEBUG=False
ALLOWED_HOSTS=your-app-name.up.railway.app,*.railway.app
OPENAI_API_KEY=your-key
DEEPSEEK_API_KEY=your-key
LLM_PROVIDER=deepseek
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. Database

- Railway will auto-create PostgreSQL if you add it
- Migrations run automatically via `Procfile` release command
- Or run manually: `railway run python manage.py migrate`

### 3. Static Files

- Automatically collected during build (included in Procfile)
- Served via WhiteNoise in production

### 4. Create Superuser (Optional)

For Django admin access:
```bash
railway run python manage.py createsuperuser
```

## 🚨 Important Security Notes

1. **First User**: Users must register/login before using the app
2. **Data Isolation**: Each user only sees their own:
   - Profiles
   - Uploaded PDFs/URLs
   - Generated posts
   - Sample posts

3. **No Public Access**: All endpoints require authentication
4. **Session Security**: Sessions expire after 7 days of inactivity

## ✅ Testing Checklist

Before going live, test:

- [ ] User registration works
- [ ] User login works
- [ ] User logout works
- [ ] Cannot access API without login (401 error)
- [ ] Users can only see their own data
- [ ] PDF upload works (authenticated)
- [ ] URL submission works (authenticated)
- [ ] Post generation works (authenticated)
- [ ] Static files load correctly
- [ ] HTTPS is enforced (automatic on Railway)

## 🔧 Troubleshooting

### Issue: 401 Unauthorized errors
**Solution**: User needs to login. Frontend should redirect automatically.

### Issue: Users can see other users' data
**Solution**: Check that views filter by `user=request.user`

### Issue: Static files not loading
**Solution**: Ensure `collectstatic` runs during build

### Issue: CSRF errors
**Solution**: Ensure cookies are being sent (check `credentials: 'include'` in fetch)

## 📊 Monitoring Recommendations

- Monitor failed login attempts
- Track API usage per user
- Monitor file upload sizes
- Watch for unusual patterns

## 🎉 Ready to Deploy!

Your application is now:
- ✅ Secure with authentication
- ✅ User data isolated
- ✅ Production-ready settings
- ✅ Protected against common attacks

Deploy to Railway and you're good to go!

