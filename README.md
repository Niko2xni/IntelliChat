# IntelliChat Admin Dashboard

A comprehensive Django-based admin dashboard for the IntelliChat system, providing real-time metrics, analytics, and system performance visualization.

## Features

- **Real-time Metrics**: Display total chats, active users, average response time, and satisfaction rates
- **Performance Analytics**: Visual charts showing common inquiries and response time trends
- **Responsive Design**: Fully responsive UI that works on desktop, tablet, and mobile devices
- **Modern UI Components**: Clean, professional interface with metrics cards and interactive charts
- **Data Management**: Django admin interface for managing dashboard data
- **RESTful API**: Built-in API endpoints for fetching and updating metrics

## Project Structure

```
admin-intellichat/
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── db.sqlite3            # SQLite database
├── admin_intellichat/    # Main project settings
│   ├── settings.py       # Django settings
│   ├── urls.py           # URL routing
│   ├── wsgi.py           # WSGI configuration
│   └── asgi.py           # ASGI configuration
├── dashboard/            # Dashboard app
│   ├── models.py         # Database models
│   ├── views.py          # View logic
│   ├── urls.py           # App URL routing
│   ├── admin.py          # Django admin configuration
│   ├── apps.py           # App configuration
│   └── tests.py          # Test cases
├── templates/
│   └── dashboard/
│       ├── base.html            # Base template
│       ├── index.html           # Dashboard main page
│       ├── header.html          # Header component
│       └── sidebar.html         # Sidebar navigation
└── static/
    ├── css/
    │   └── style.css           # Main stylesheet
    └── js/
        └── dashboard.js        # JavaScript functionality
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Cloudinary for Media Uploads

Create a `.env` file in the project root (or update your existing one):

```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret
```

This project now uses Cloudinary as the required runtime storage for profile pictures and uploaded dashboard documents (no local media fallback outside tests).

If you already have files in local `media/`, run this one-time migration command after enabling Cloudinary:

```bash
python manage.py migrate_media_to_cloudinary --dry-run --skip-missing
python manage.py migrate_media_to_cloudinary --skip-missing
```

If Cloudinary rejects malformed files during migration, you can also use:

```bash
python manage.py migrate_media_to_cloudinary --skip-upload-errors --skip-missing
```

To remove stale DB file references (missing files or invalid local PDFs) before retrying migration:

```bash
python manage.py cleanup_media_references --dry-run
python manage.py cleanup_media_references
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

This allows you to access the Django admin panel at `/admin/`

### 5. Load Initial Data (Optional)

Create initial dashboard metrics by accessing the admin panel or using Django shell:

```bash
python manage.py shell
```

```python
from dashboard.models import DashboardMetrics, CommonInquiry

# Create initial metrics
metrics = DashboardMetrics.objects.create(
    total_chats=1247,
    active_users=342,
    avg_response_time=2.1,
    satisfaction_rate=94.0,
    chats_change=12.5,
    users_change=8.2,
    response_time_change=-5.3,
    satisfaction_change=3.1
)

# Create common inquiries
CommonInquiry.objects.bulk_create([
    CommonInquiry(title='Account Help', count=45),
    CommonInquiry(title='Technical Support', count=38),
    CommonInquiry(title='General Info', count=30),
    CommonInquiry(title='Billing', count=25),
    CommonInquiry(title='Other', count=20),
])
```

## Running the Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Available Routes

- `/` - Main dashboard
- `/admin/` - Django admin panel
- `/api/chart-data/` - Chart data API endpoint
- `/api/inquiries-data/` - Inquiries data API endpoint
- `/api/update-metrics/` - Update metrics API endpoint

## API Endpoints

### Get Chart Data
```
GET /api/chart-data/
Response: { dates: [...], times: [...] }
```

### Get Inquiries Data
```
GET /api/inquiries-data/
Response: { labels: [...], data: [...] }
```

### Update Metrics
```
POST /api/update-metrics/
Body: {
    "total_chats": 1300,
    "active_users": 350,
    "avg_response_time": 2.0,
    "satisfaction_rate": 95.0,
    "chats_change": 15.0,
    "users_change": 10.0,
    "response_time_change": -10.0,
    "satisfaction_change": 5.0
}
```

## Database Models

### DashboardMetrics
Stores overall system performance metrics.

```python
- total_chats: Integer
- active_users: Integer
- avg_response_time: Float (seconds)
- satisfaction_rate: Float (percentage)
- chats_change: Float (percentage change)
- users_change: Float (percentage change)
- response_time_change: Float (percentage change)
- satisfaction_change: Float (percentage change)
- last_updated: DateTime
```

### CommonInquiry
Tracks common user inquiries and their frequency.

```python
- title: String
- count: Integer
- percentage: Float
```

### ResponseTimeData
Historical response time data for trending.

```python
- date: Date
- average_response_time: Float
- min_response_time: Float
- max_response_time: Float
```

## Styling

The dashboard features a custom color scheme with:
- **Primary Color**: Orange (#FFA500)
- **Secondary Color**: Gold (#FFD700)
- **Text Colors**: Professional dark and light grays
- **Responsive Grid Layouts**: Auto-adapting component grids

### Color Palette
```css
--primary-color: #FFA500
--primary-dark: #FF9500
--primary-light: #FFB84D
--secondary-color: #FFD700
--text-dark: #2C2C2C
--text-light: #666666
```

## Charts

The dashboard uses Chart.js for data visualization:
- **Common Inquiries**: Bar chart showing distribution
- **Response Times**: Line chart showing trends over time

## Testing

Run tests with:

```bash
python manage.py test dashboard
```

## Render Deployment

For Render-specific deployment steps, use [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md).
The guide also includes a checklist mapped to the keys currently in your local `.env`.

## Static Files

To collect static files for production:

```bash
python manage.py collectstatic
```

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, run:
```bash
python manage.py runserver 8001
```

### Database Errors
Reset the database with:
```bash
python manage.py flush
python manage.py migrate
```

### Static Files Not Loading
Ensure you've run:
```bash
python manage.py collectstatic --noinput
```

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Future Enhancements

- Real-time WebSocket updates for live metrics
- Advanced filtering and date range selection
- Export analytics to CSV/PDF
- User authentication and permissions
- Multiple dashboard views and customization
- Integration with external analytics services

## License

This project is part of the IntelliChat system.

## Support

For issues or questions, contact the development team.
