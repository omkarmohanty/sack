"""Resource Management Models for SACK Tool"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

class Resource(models.Model):
    """Model representing a system resource (like Windows/Ubuntu machines)"""
    RESOURCE_TYPES = [
        ('Windows', 'Windows'),
        ('Ubuntu', 'Ubuntu'),
        ('Linux', 'Linux'),
        ('MacOS', 'MacOS'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Maintenance', 'Maintenance'),
    ]

    pc_name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(unique=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pc_name']
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'

    def __str__(self):
        return f"{self.pc_name} ({self.ip_address})"

    def get_current_usage(self):
        """Get current usage session if resource is occupied"""
        # Return the most recent active usage if any
        return self.usages.filter(end_time__isnull=True).order_by('-start_time').first()

    def is_available(self):
        """Check if resource is available for use"""
        return self.status == 'Available' and self.is_active

    def get_queue_count(self):
        """Get number of users in queue for this resource"""
        return self.queue_entries.filter(is_active=True).count()

class ResourceUsage(models.Model):
    """Model to track resource usage sessions"""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_usages')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    planned_duration = models.DurationField(default=timedelta(hours=1))
    actual_duration = models.DurationField(null=True, blank=True)
    extended_time = models.DurationField(default=timedelta(0))
    is_active = models.BooleanField(default=True)
    auto_released = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Resource Usage'
        verbose_name_plural = 'Resource Usages'

    def __str__(self):
        return f"{self.user.username} - {self.resource.pc_name} ({self.start_time})"

    def get_remaining_time(self):
        """Calculate remaining time in seconds"""
        if self.end_time:
            return 0

        total_duration = self.planned_duration + self.extended_time
        elapsed = timezone.now() - self.start_time
        remaining = total_duration - elapsed

        return max(0, int(remaining.total_seconds()))

    def is_expired(self):
        """Check if the usage session has expired"""
        return self.get_remaining_time() <= 0

    def get_end_time(self):
        """Get calculated end time based on start time and durations"""
        total_duration = self.planned_duration + self.extended_time
        return self.start_time + total_duration

    def extend_time(self, extension_minutes=15):
        """Extend the usage time"""
        extension = timedelta(minutes=extension_minutes)
        self.extended_time += extension
        self.save()

        # Also extend time for all users in queue
        queue_entries = ResourceQueue.objects.filter(
            resource=self.resource,
            is_active=True
        ).order_by('joined_at')

        for entry in queue_entries:
            entry.estimated_wait_time += extension
            entry.save()

class ResourceQueue(models.Model):
    """Model to manage resource waiting queue"""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='queue_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='queue_entries')
    joined_at = models.DateTimeField(auto_now_add=True)
    estimated_wait_time = models.DurationField(default=timedelta(0))
    is_active = models.BooleanField(default=True)
    # How much time (in minutes) the user requests when joining queue
    requested_minutes = models.PositiveIntegerField(default=60)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['joined_at']
        unique_together = ['resource', 'user', 'is_active']
        verbose_name = 'Resource Queue'
        verbose_name_plural = 'Resource Queues'

    def __str__(self):
        return f"{self.user.username} queued for {self.resource.pc_name}"

    def get_position(self):
        """Get current position in queue"""
        return ResourceQueue.objects.filter(
            resource=self.resource,
            is_active=True,
            joined_at__lt=self.joined_at
        ).count() + 1

    def update_estimated_wait_time(self):
        """Update estimated wait time based on current usage and queue position"""
        current_usage = self.resource.get_current_usage()
        if current_usage:
            remaining_time = current_usage.get_remaining_time()
            # Sum requested minutes of users ahead in queue
            ahead = ResourceQueue.objects.filter(
                resource=self.resource,
                is_active=True,
                joined_at__lt=self.joined_at
            )
            ahead_minutes = sum([q.requested_minutes for q in ahead])
            # estimated_time is remaining_time plus minutes requested by users ahead
            estimated_seconds = remaining_time + (ahead_minutes * 60)
            self.estimated_wait_time = timedelta(seconds=estimated_seconds)
            self.save()

    def requested_display(self):
        """Return a human-friendly string for requested_minutes, e.g. '1h 30m' or '45m'"""
        h = self.requested_minutes // 60
        m = self.requested_minutes % 60
        if h > 0 and m > 0:
            return f"{h}h {m}m"
        if h > 0:
            return f"{h}h"
        return f"{m}m"

class UserSession(models.Model):
    """Model to track user sessions and notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='session_data')
    last_activity = models.DateTimeField(auto_now=True)
    notification_enabled = models.BooleanField(default=True)
    browser_notifications = models.BooleanField(default=False)
    first_warning_shown = models.JSONField(default=dict)  # {resource_id: datetime}
    second_warning_shown = models.JSONField(default=dict)  # {resource_id: datetime}

    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"{self.user.username} session data"


class UserProfile(models.Model):
    """Per-user preferences stored server-side"""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class SystemLog(models.Model):
    """Model to log system events and actions"""
    LOG_TYPES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('RESOURCE', 'Resource Action'),
        ('USER', 'User Action'),
        ('SYSTEM', 'System Event'),
    ]

    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resource = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'

    def __str__(self):
        return f"{self.log_type} - {self.message[:50]}..."