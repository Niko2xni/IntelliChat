"""
Dashboard configuration and utilities
"""

# Dashboard configuration constants
DASHBOARD_CONFIG = {
    'REFRESH_INTERVAL': 5 * 60 * 1000,  # 5 minutes in milliseconds
    'CHART_UPDATE_FREQUENCY': 10 * 60,  # 10 minutes in seconds
    'DEFAULT_METRIC_PRECISION': 2,  # Decimal places for metrics
}

# Color scheme configuration
COLOR_SCHEME = {
    'PRIMARY': '#FFA500',
    'PRIMARY_DARK': '#FF9500',
    'PRIMARY_LIGHT': '#FFB84D',
    'SECONDARY': '#FFD700',
    'SUCCESS': '#4CAF50',
    'DANGER': '#F44336',
    'WARNING': '#FF9800',
    'INFO': '#2196F3',
}

# Chart defaults
CHART_CONFIG = {
    'BAR': {
        'TYPE': 'bar',
        'ANIMATION_DURATION': 400,
    },
    'LINE': {
        'TYPE': 'line',
        'ANIMATION_DURATION': 500,
        'TENSION': 0.4,
    },
}

# API endpoints
API_ENDPOINTS = {
    'CHART_DATA': '/api/chart-data/',
    'INQUIRIES_DATA': '/api/inquiries-data/',
    'UPDATE_METRICS': '/api/update-metrics/',
}
