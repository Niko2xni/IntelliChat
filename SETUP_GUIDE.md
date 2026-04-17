# Quick Start Guide for IntelliChat Admin Dashboard

## Step-by-Step Setup Instructions

### 1. Navigate to the admin-intellichat folder
```bash
cd c:\Users\gerry\admin-intellichat
```

### 2. Create and activate a virtual environment (recommended)
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run database migrations
```bash
python manage.py migrate
```

### 5. Create a superuser (optional - for Django admin access)
```bash
python manage.py createsuperuser
```
Follow the prompts to create an admin account.

### 6. Load initial data (optional)
```bash
python manage.py populate_initial_data
```
This will populate the dashboard with sample metrics and data.

### 7. Start the development server
```bash
python manage.py runserver
```

### 8. Access the dashboard
Open your browser and go to:
- **Dashboard**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/ (if you created a superuser)

## Project Features Included

✓ Django Project Structure
✓ Dashboard App with Models
✓ Responsive HTML/CSS Frontend
✓ Real-time Metrics Display
✓ Chart.js Integration for Analytics
✓ RESTful API Endpoints
✓ Django Admin Configuration
✓ Mobile-Responsive Design
✓ Professional Styling (Orange & Gold theme)
✓ Sample Data Management Command

## Key Files

### Backend
- `admin_intellichat/settings.py` - Django configuration
- `admin_intellichat/urls.py` - Main URL routing
- `dashboard/models.py` - Database models
- `dashboard/views.py` - View logic and API endpoints

### Frontend
- `templates/dashboard/index.html` - Main dashboard page
- `templates/dashboard/base.html` - Base template
- `static/css/style.css` - Complete styling
- `static/js/dashboard.js` - Dashboard functionality

## Testing the Dashboard

1. Start the server: `python manage.py runserver`
2. Visit: http://127.0.0.1:8000/
3. You should see the admin dashboard with:
   - Four metric cards (Total Chats, Active Users, Response Time, Satisfaction)
   - Two charts (Common Inquiries bar chart, Response Times line chart)
   - Common inquiries list

## API Examples

### Get Chart Data
```bash
curl http://127.0.0.1:8000/api/chart-data/
```

### Update Metrics
```bash
curl -X POST http://127.0.0.1:8000/api/update-metrics/ \
  -H "Content-Type: application/json" \
  -d '{"total_chats": 1500, "active_users": 400, "avg_response_time": 2.0, "satisfaction_rate": 95.0}'
```

## Troubleshooting

### Port 8000 is already in use
```bash
python manage.py runserver 8001
```

### Database errors
```bash
python manage.py flush
python manage.py migrate
```

### Static files not loading
```bash
python manage.py collectstatic --noinput
```

## Environment Variables

Create a `.env` file in the project root for sensitive data and deployment settings:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=your-database-url
ALLOWED_HOSTS=127.0.0.1,localhost

# Cloudinary media storage (profile pictures and uploaded documents)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret

# Production security toggles (recommended when DEBUG=False)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

Notes:
- Cloudinary storage is required at runtime for profile pictures and dashboard document uploads.
- During automated test runs, cloud storage is disabled by default to keep tests local and deterministic.

Optional one-time migration for existing local uploads:
```bash
python manage.py migrate_media_to_cloudinary --dry-run --skip-missing
python manage.py migrate_media_to_cloudinary --skip-missing
```

If some legacy files are malformed and rejected by Cloudinary, retry with:
```bash
python manage.py migrate_media_to_cloudinary --skip-upload-errors --skip-missing
```

To clean broken media references in the database before retrying migration:
```bash
python manage.py cleanup_media_references --dry-run
python manage.py cleanup_media_references
```

## Customization

### Change Colors
Edit `static/css/style.css` and update the CSS variables:
```css
:root {
    --primary-color: #FFA500;  /* Change orange color */
    --secondary-color: #FFD700; /* Change gold color */
    /* ... other colors ... */
}
```

### Add More Metrics
1. Add fields to `DashboardMetrics` model in `dashboard/models.py`
2. Run migration: `python manage.py makemigrations`
3. Update template in `templates/dashboard/index.html`

### Modify Charts
Edit the chart configuration in `templates/dashboard/index.html` where Chart.js is initialized.

## Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Set a strong `SECRET_KEY` in `.env`
3. Update `ALLOWED_HOSTS` with your domain
4. Keep secure cookie/HTTPS settings enabled (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
5. Use HTTPS in front of Django (reverse proxy/load balancer)
6. Use `python manage.py collectstatic` for static files
7. Set up a production database (PostgreSQL recommended)
8. Use a production WSGI server (Gunicorn, uWSGI, etc.)

See README.md for more information.

For Render-specific deployment steps, see [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md).
