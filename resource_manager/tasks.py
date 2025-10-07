"""Celery tasks for background processing"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import ResourceUsage, ResourceQueue, Resource, SystemLog
from datetime import timedelta

@shared_task
def cleanup_expired_sessions():
    """Clean up expired resource sessions"""
    expired_count = 0

    expired_usages = ResourceUsage.objects.filter(
        end_time__isnull=True,
        is_active=True
    )

    for usage in expired_usages:
        if usage.is_expired():
            with transaction.atomic():
                # Mark as expired
                usage.end_time = timezone.now()
                usage.auto_released = True
                usage.is_active = False
                usage.actual_duration = usage.end_time - usage.start_time
                usage.save()

                # Handle queue
                resource = usage.resource
                next_in_queue = ResourceQueue.objects.filter(
                    resource=resource,
                    is_active=True
                ).order_by('joined_at').first()

                if next_in_queue:
                    # Auto-assign to next user
                    ResourceUsage.objects.create(
                        resource=resource,
                        user=next_in_queue.user,
                        planned_duration=timedelta(hours=1)
                    )
                    next_in_queue.is_active = False
                    next_in_queue.save()

                    SystemLog.objects.create(
                        log_type='SYSTEM',
                        user=next_in_queue.user,
                        resource=resource,
                        message=f'Auto-assigned {resource.pc_name} from queue'
                    )
                else:
                    # Make available
                    resource.status = 'Available'
                    resource.save()

                SystemLog.objects.create(
                    log_type='SYSTEM',
                    user=usage.user,
                    resource=resource,
                    message=f'Auto-expired session for {resource.pc_name}'
                )

                expired_count += 1

    if expired_count > 0:
        SystemLog.objects.create(
            log_type='SYSTEM',
            message=f'Cleaned up {expired_count} expired sessions'
        )

    return f"Cleaned up {expired_count} expired sessions"