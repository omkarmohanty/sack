"""Admin configuration for SACK Resource Management Tool"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils import timezone
from .models import Resource, ResourceUsage, ResourceQueue, UserSession, SystemLog

# Customize the admin site header and title
admin.site.site_header = "SACK Tool Administration"
admin.site.site_title = "SACK Tool Admin"
admin.site.index_title = "Resource Management System"

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = [
        'pc_name', 'ip_address', 'resource_type', 'status_display', 
        'current_user_display', 'queue_count_display', 'is_active', 'updated_at'
    ]
    list_filter = ['resource_type', 'status', 'is_active', 'created_at']
    search_fields = ['pc_name', 'ip_address']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('pc_name', 'ip_address', 'resource_type')
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        colors = {
            'Available': 'green',
            'Occupied': 'red',
            'Maintenance': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">⬤ {}</span>',
            color, obj.status
        )
    status_display.short_description = 'Status'

    def current_user_display(self, obj):
        usage = obj.get_current_usage()
        if usage:
            return format_html(
                '<span style="color: blue;">👤 {}</span>',
                usage.user.username
            )
        return format_html('<span style="color: gray">-</span>')
    current_user_display.short_description = 'Current User'

    def queue_count_display(self, obj):
        count = obj.get_queue_count()
        if count > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">👥 {}</span>',
                count
            )
        return format_html('<span style="color: gray">-</span>')
    queue_count_display.short_description = 'Queue'

@admin.register(ResourceUsage)
class ResourceUsageAdmin(admin.ModelAdmin):
    list_display = [
        'resource', 'user', 'start_time', 'end_time', 'planned_duration_display',
        'remaining_time_display', 'status_display', 'auto_released'
    ]
    list_filter = ['is_active', 'auto_released', 'resource__resource_type', 'start_time']
    search_fields = ['resource__pc_name', 'user__username']
    readonly_fields = ['start_time', 'actual_duration']
    date_hierarchy = 'start_time'

    fieldsets = (
        ('Session Information', {
            'fields': ('resource', 'user', 'start_time', 'end_time')
        }),
        ('Duration Settings', {
            'fields': ('planned_duration', 'extended_time', 'actual_duration')
        }),
        ('Status', {
            'fields': ('is_active', 'auto_released')
        }),
    )

    def planned_duration_display(self, obj):
        total_seconds = obj.planned_duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    planned_duration_display.short_description = 'Planned Duration'

    def remaining_time_display(self, obj):
        if obj.end_time:
            return format_html('<span style="color: gray">Ended</span>')
        remaining = obj.get_remaining_time()
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            return format_html(
                '<span style="color: blue">{}m {}s</span>',
                minutes, seconds
            )
        else:
            return format_html('<span style="color: red">Expired</span>')
    remaining_time_display.short_description = 'Remaining'

    def status_display(self, obj):
        if obj.end_time:
            color = 'gray'
            status = 'Ended'
        elif obj.is_active:
            if obj.get_remaining_time() > 0:
                color = 'green'
                status = 'Active'
            else:
                color = 'red'
                status = 'Expired'
        else:
            color = 'gray'
            status = 'Inactive'

        return format_html(
            '<span style="color: {}; font-weight: bold;">⬤ {}</span>',
            color, status
        )
    status_display.short_description = 'Status'

@admin.register(ResourceQueue)
class ResourceQueueAdmin(admin.ModelAdmin):
    list_display = [
        'resource', 'user', 'position_display', 'joined_at', 
        'estimated_wait_display', 'is_active'
    ]
    list_filter = ['is_active', 'resource__resource_type', 'joined_at']
    search_fields = ['resource__pc_name', 'user__username']
    readonly_fields = ['joined_at', 'position']

    def position_display(self, obj):
        if obj.is_active:
            position = obj.get_position()
            return format_html(
                '<span style="color: orange; font-weight: bold;">#{}</span>',
                position
            )
        return format_html('<span style="color: gray">Inactive</span>')
    position_display.short_description = 'Position'

    def estimated_wait_display(self, obj):
        if obj.estimated_wait_time:
            total_seconds = obj.estimated_wait_time.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return '-'
    estimated_wait_display.short_description = 'Est. Wait'

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'last_activity', 'notification_enabled', 
        'browser_notifications', 'active_sessions_count'
    ]
    list_filter = ['notification_enabled', 'browser_notifications', 'last_activity']
    search_fields = ['user__username']
    readonly_fields = ['last_activity']

    def active_sessions_count(self, obj):
        count = ResourceUsage.objects.filter(
            user=obj.user,
            end_time__isnull=True
        ).count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">🔴 {}</span>',
                count
            )
        return format_html('<span style="color: gray">-</span>')
    active_sessions_count.short_description = 'Active Sessions'

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'log_type', 'user', 'resource', 'message_short', 'details_display'
    ]
    list_filter = ['log_type', 'timestamp', 'resource__resource_type']
    search_fields = ['message', 'user__username', 'resource__pc_name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Log Information', {
            'fields': ('log_type', 'timestamp', 'message')
        }),
        ('Related Objects', {
            'fields': ('user', 'resource')
        }),
        ('Additional Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )

    def message_short(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_short.short_description = 'Message'

    def details_display(self, obj):
        if obj.details:
            return format_html(
                '<span style="color: blue">📋 {} keys</span>',
                len(obj.details)
            )
        return format_html('<span style="color: gray">-</span>')
    details_display.short_description = 'Details'

# Extend User Admin to show resource-related information
class UserAdminExtended(BaseUserAdmin):
    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        if obj:
            # Add custom inlines for resource usage
            pass
        return inline_instances

# Unregister the original User admin and register the extended one
admin.site.unregister(User)
admin.site.register(User, UserAdminExtended)

# Custom admin actions
def release_expired_sessions(modeladmin, request, queryset):
    """Admin action to release expired sessions"""
    count = 0
    for usage in queryset.filter(end_time__isnull=True):
        if usage.is_expired():
            usage.end_time = timezone.now()
            usage.auto_released = True
            usage.is_active = False
            usage.save()

            # Update resource status
            resource = usage.resource
            if not resource.usages.filter(end_time__isnull=True).exists():
                resource.status = 'Available'
                resource.save()

            count += 1

    modeladmin.message_user(request, f"Released {count} expired sessions.")

release_expired_sessions.short_description = "Release expired sessions"

# Add the action to ResourceUsage admin
ResourceUsageAdmin.actions = [release_expired_sessions]