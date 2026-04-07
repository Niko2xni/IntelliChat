// Notification System JavaScript
class NotificationSystem {
    constructor() {
        this.notificationUrl = '/dashboard/api/notifications/';
        this.countUrl = '/dashboard/api/notifications/count/';
        this.markReadUrl = '/dashboard/api/notifications/{id}/read/';
        this.markAllReadUrl = '/dashboard/api/notifications/mark-all-read/';
        this.unreadCount = 0;
        this.notifications = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadNotificationCount();
        this.startPolling();
    }

    setupEventListeners() {
        // Notification button click
        const notificationBtn = document.querySelector('.notification-btn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleNotificationDropdown();
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('notificationDropdown');
            if (dropdown && !dropdown.contains(e.target) && !e.target.closest('.notification-btn')) {
                this.hideNotificationDropdown();
            }
        });

        // Mark all as read button
        const markAllReadBtn = document.getElementById('markAllReadBtn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
    }

    async loadNotificationCount() {
        try {
            const response = await fetch(this.countUrl);
            const data = await response.json();
            this.updateBadge(data.unread_count);
            this.unreadCount = data.unread_count;
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch(this.notificationUrl);
            const data = await response.json();
            this.notifications = data.notifications;
            this.unreadCount = data.unread_count;
            this.updateBadge(this.unreadCount);
            this.renderNotifications();
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    updateBadge(count) {
        const badges = document.querySelectorAll('.badge, .notif-badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });
    }

    renderNotifications() {
        const dropdown = document.getElementById('notificationDropdown');
        if (!dropdown) return;

        const notificationList = dropdown.querySelector('.notification-list');
        if (!notificationList) return;

        if (this.notifications.length === 0) {
            notificationList.innerHTML = `
                <div class="notification-item empty">
                    <p>No new notifications</p>
                </div>
            `;
        } else {
            notificationList.innerHTML = this.notifications.map(notif => this.renderNotificationItem(notif)).join('');
            
            // Add click listeners to notification items
            notificationList.querySelectorAll('.notification-item').forEach(item => {
                item.addEventListener('click', () => {
                    const notifId = item.dataset.notificationId;
                    this.markAsRead(notifId);
                });
            });

            // Enhance admin notifications with response buttons
            if (window.location.pathname.includes('/dashboard/')) {
                this.enhanceAdminNotifications();
            }
        }
    }

    renderNotificationItem(notif) {
        const typeClass = `notification-${notif.type}`;
        const timeAgo = this.getTimeAgo(notif.created_at);
        
        return `
            <div class="notification-item ${typeClass}" data-notification-id="${notif.id}">
                <div class="notification-content">
                    <h4>${notif.title}</h4>
                    <p>${notif.message}</p>
                    <span class="notification-time">${timeAgo}</span>
                </div>
                <div class="notification-actions">
                    ${notif.action_url ? `<a href="${notif.action_url}" class="notification-action">View</a>` : ''}
                </div>
            </div>
        `;
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const notifTime = new Date(timestamp);
        const diffMs = now - notifTime;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return notifTime.toLocaleDateString();
    }

    async markAsRead(notificationId) {
        try {
            const url = this.markReadUrl.replace('{id}', notificationId);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                // Remove notification from list
                this.notifications = this.notifications.filter(n => n.id != notificationId);
                this.unreadCount--;
                this.updateBadge(this.unreadCount);
                this.renderNotifications();
                
                // Navigate to action URL if provided
                const notif = this.notifications.find(n => n.id == notificationId);
                if (notif && notif.action_url) {
                    window.location.href = notif.action_url;
                }
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    async markAllAsRead() {
        try {
            const response = await fetch(this.markAllReadUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.notifications = [];
                this.unreadCount = 0;
                this.updateBadge(0);
                this.renderNotifications();
                this.hideNotificationDropdown();
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    }

    toggleNotificationDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (!dropdown) return;

        if (dropdown.style.display === 'block') {
            this.hideNotificationDropdown();
        } else {
            this.showNotificationDropdown();
        }
    }

    showNotificationDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (!dropdown) return;

        dropdown.style.display = 'block';
        this.loadNotifications();
    }

    hideNotificationDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    startPolling() {
        // Poll for new notifications every 30 seconds
        setInterval(() => {
            this.loadNotificationCount();
        }, 30000);
    }

    // Static method to create notifications (for testing/demo)
    static createSampleNotifications() {
        // This would typically be called from backend when events occur
        const sampleNotifications = [
            { title: 'New User Registration', message: 'A new user has registered on the platform', type: 'info' },
            { title: 'Document Uploaded', message: 'New document has been uploaded to knowledge base', type: 'success' },
            { title: 'System Maintenance', message: 'Scheduled maintenance will occur tonight at 11 PM', type: 'warning' }
        ];
        
        console.log('Sample notifications (for testing):', sampleNotifications);
    }

    // Method to submit user requests to admin
    async submitUserRequest(requestType, details = '') {
        try {
            const response = await fetch('/dashboard/api/notifications/submit-request/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: requestType,
                    details: details
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showAlert('Request submitted successfully!', 'success');
                this.loadNotificationCount(); // Refresh count
            } else {
                this.showAlert(result.error || 'Failed to submit request', 'error');
            }
        } catch (error) {
            console.error('Error submitting request:', error);
            this.showAlert('An error occurred while submitting request', 'error');
        }
    }

    // Method for admin to respond to user requests
    async respondToUserRequest(notificationId, responseType, details = '') {
        try {
            const response = await fetch(`/dashboard/api/notifications/${notificationId}/respond/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    response_type: responseType,
                    details: details
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showAlert(result.message, 'success');
                this.loadNotifications(); // Refresh the list
            } else {
                this.showAlert(result.error || 'Failed to send response', 'error');
            }
        } catch (error) {
            console.error('Error responding to request:', error);
            this.showAlert('An error occurred while sending response', 'error');
        }
    }

    // Show alert messages
    showAlert(message, type = 'info') {
        // Create a simple alert (could be enhanced with a toast notification)
        alert(message);
    }

    // Add response buttons to admin notifications
    enhanceAdminNotifications() {
        const notificationItems = document.querySelectorAll('.notification-item[data-notification-id]');
        notificationItems.forEach(item => {
            const notificationId = item.dataset.notificationId;
            const actionsDiv = item.querySelector('.notification-actions');
            
            if (actionsDiv && !actionsDiv.querySelector('.response-btn')) {
                // Add response buttons for admin-only notifications
                const responseBtn = document.createElement('div');
                responseBtn.className = 'response-buttons';
                responseBtn.innerHTML = `
                    <button class="response-btn approve-btn" onclick="notificationSystem.respondToUserRequest(${notificationId}, 'approved')">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="response-btn reject-btn" onclick="notificationSystem.respondToUserRequest(${notificationId}, 'rejected')">
                        <i class="fas fa-times"></i> Reject
                    </button>
                `;
                actionsDiv.appendChild(responseBtn);
            }
        });
    }
}

// Initialize notification system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationSystem = new NotificationSystem();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}
