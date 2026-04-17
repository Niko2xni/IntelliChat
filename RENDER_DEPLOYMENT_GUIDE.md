# Render Deployment Guide

This guide deploys IntelliChat to Render as a Python Web Service.

## 1) Pre-deployment checklist

- Push the latest project code to GitHub.
- Ensure Cloudinary credentials are ready:
  - CLOUDINARY_CLOUD_NAME
  - CLOUDINARY_API_KEY
  - CLOUDINARY_API_SECRET
- Ensure your production database URL is ready (Neon or Render PostgreSQL):
  - DATABASE_URL
- Ensure required API/email secrets are ready if you use those features:
  - GEMINI_API_KEY
  - EMAIL_USER
  - EMAIL_PASS
  - BREVO_API_KEY (optional)

## 2) Recommended deploy method (Blueprint)

This repository includes a Render blueprint file at [render.yaml](render.yaml).

Steps:

1. In Render, choose New + and then Blueprint.
2. Connect your GitHub repository.
3. Render will detect [render.yaml](render.yaml).
4. Review service name and plan, then create the service.
5. Set all env vars marked sync: false in Render dashboard.
6. Trigger deploy.

The blueprint already configures:

- Build command:
  - pip install -r requirements.txt
  - python manage.py collectstatic --noinput
- Pre-deploy command:
  - python manage.py migrate
- Start command:
  - gunicorn intellichat.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --log-file -
- HTTPS/secure cookie defaults via env vars
- ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS defaults for onrender.com

## 3) Manual deploy method (if you do not use Blueprint)

1. Create a new Web Service on Render.
2. Select the same GitHub repo/branch.
3. Set Runtime to Python.
4. Build command:
   - pip install -r requirements.txt && python manage.py collectstatic --noinput
5. Pre-deploy command:
   - python manage.py migrate
6. Start command:
   - gunicorn intellichat.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --log-file -

## 4) Environment variables for Render

Set these in Render service settings:

Required:

- DEBUG=False
- SECRET_KEY=<strong random value>
- DATABASE_URL=<postgres connection string>
- CLOUDINARY_CLOUD_NAME=<cloudinary cloud name>
- CLOUDINARY_API_KEY=<cloudinary api key>
- CLOUDINARY_API_SECRET=<cloudinary api secret>

Recommended:

- ALLOWED_HOSTS=.onrender.com,<your-custom-domain>
- CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://<your-custom-domain>
- SECURE_SSL_REDIRECT=True
- SESSION_COOKIE_SECURE=True
- CSRF_COOKIE_SECURE=True
- SECURE_HSTS_SECONDS=31536000
- SECURE_HSTS_INCLUDE_SUBDOMAINS=True
- SECURE_HSTS_PRELOAD=True

App features:

- GEMINI_API_KEY=<gemini api key>
- EMAIL_USER=<smtp sender>
- EMAIL_PASS=<smtp password>
- BREVO_API_KEY=<optional>
- BREVO_SENDER_EMAIL=<optional>
- BREVO_SENDER_NAME=IntelliChat

## 4.1) Checklist from your current `.env`

These are the local keys currently present in your project. Recreate the values on Render where applicable:

- [ ] `DATABASE_URL` - use your production database connection string.
- [ ] `SECRET_KEY` - set a new strong production secret.
- [ ] `GEMINI_API_KEY` - required for chatbot responses.
- [ ] `EMAIL_USER` - required if you want password/OTP emails to send.
- [ ] `EMAIL_PASS` - required with `EMAIL_USER`.
- [ ] `CLOUDINARY_CLOUD_NAME` - required for media uploads.
- [ ] `CLOUDINARY_API_KEY` - required for media uploads.
- [ ] `CLOUDINARY_API_SECRET` - required for media uploads.
- [ ] `DEBUG=False` - required in production.
- [ ] `ALLOWED_HOSTS` - keep `.onrender.com` and add any custom domain.
- [ ] `CSRF_TRUSTED_ORIGINS` - include `https://*.onrender.com` and any custom domain.

Not needed on Render:

- `USE_CLOUDINARY_STORAGE` - the app enables Cloudinary automatically outside tests.

Only if you use Brevo on Render:

- [ ] `BREVO_API_KEY`
- [ ] `BREVO_SENDER_EMAIL`
- [ ] `BREVO_SENDER_NAME`

## 5) Verify after deployment

1. Open deployed URL and log in.
2. Confirm static assets load (CSS/JS visible).
3. Upload a profile picture.
4. Upload a document in dashboard.
5. Confirm uploaded URLs use res.cloudinary.com.
6. Test chatbot response endpoint and notifications.

## 6) Common issues and fixes

### Build fails at collectstatic

- Check for missing dependencies in [requirements.txt](requirements.txt).
- Confirm no syntax errors by running locally:
  - python manage.py check

### App fails at startup with Cloudinary error

- Ensure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET are set.
- This project requires Cloudinary at runtime.

### 400 Bad Request (CSRF/host issues)

- Add your Render/custom domain to ALLOWED_HOSTS.
- Add https URLs to CSRF_TRUSTED_ORIGINS.

### Database connection failures

- Verify DATABASE_URL is correct and reachable.
- If using external DB, ensure SSL requirements are met in the URL.

## 7) Optional: one-time local media migration

Only needed if you still have legacy local files to migrate:

- python manage.py migrate_media_to_cloudinary --dry-run --skip-missing
- python manage.py migrate_media_to_cloudinary --skip-missing

If invalid legacy files are present:

- python manage.py cleanup_media_references --dry-run
- python manage.py cleanup_media_references
