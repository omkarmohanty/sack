"""Views for SACK Resource Management Tool"""
import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User

from .models import Resource, ResourceUsage, ResourceQueue, SystemLog, UserSession
from .forms import LoginForm, UsageTimeForm

def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # Create or update user session data
                session_data, created = UserSession.objects.get_or_create(user=user)
                session_data.save()

                SystemLog.objects.create(
                    log_type='USER',
                    user=user,
                    message=f'User {username} logged in',
                    details={'ip_address': request.META.get('REMOTE_ADDR')}
                )
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()

    return render(request, 'resource_manager/login.html', {'form': form})

def logout_view(request):
    """Handle user logout"""
    if request.user.is_authenticated:
        SystemLog.objects.create(
            log_type='USER',
            user=request.user,
            message=f'User {request.user.username} logged out'
        )
        logout(request)
        messages.success(request, 'Successfully logged out')
    return redirect('login')

@login_required
def dashboard(request):
    """Main dashboard view showing all resources"""
    resources = Resource.objects.filter(is_active=True).prefetch_related('usages', 'queue_entries')

    # Update expired sessions
    update_expired_sessions()

    resource_data = []
    for resource in resources:
        current_usage = resource.get_current_usage()
        queue_count = resource.get_queue_count()

        user_in_queue = ResourceQueue.objects.filter(
            resource=resource,
            user=request.user,
            is_active=True
        ).exists()

        resource_info = {
            'resource': resource,
            'current_usage': current_usage,
            'queue_count': queue_count,
            'user_in_queue': user_in_queue,
            'remaining_time': current_usage.get_remaining_time() if current_usage else 0,
            'is_current_user': current_usage.user == request.user if current_usage else False,
        }
        resource_data.append(resource_info)

    # Compute summary counts to avoid template concatenation issues
    total_resources = len(resource_data)
    available_count = sum(1 for d in resource_data if d['resource'].status == 'Available')
    occupied_count = sum(1 for d in resource_data if d['resource'].status == 'Occupied')
    queue_total = sum(d['queue_count'] for d in resource_data)

    return render(request, 'resource_manager/dashboard.html', {
        'resource_data': resource_data,
        'user': request.user,
        'total_resources': total_resources,
        'available_count': available_count,
        'occupied_count': occupied_count,
        'queue_total': queue_total,
    })

@login_required
@require_POST
def occupy_resource(request):
    """Occupy an available resource"""
    resource_id = request.POST.get('resource_id')
    minutes = int(request.POST.get('minutes', 60))

    try:
        with transaction.atomic():
            resource = Resource.objects.select_for_update().get(id=resource_id, is_active=True)

            if not resource.is_available():
                return JsonResponse({'success': False, 'message': 'Resource is not available'})

            # Note: allow a single user to occupy multiple resources simultaneously

            # Create new usage session
            # Ensure no other active usage exists for the resource (single occupant)
            if resource.get_current_usage():
                return JsonResponse({'success': False, 'message': 'Resource is already in use'})

            usage = ResourceUsage.objects.create(
                resource=resource,
                user=request.user,
                planned_duration=timedelta(minutes=minutes)
            )

            # Update resource status
            resource.status = 'Occupied'
            resource.save()

            # Log the action
            SystemLog.objects.create(
                log_type='RESOURCE',
                user=request.user,
                resource=resource,
                message=f'Resource {resource.pc_name} occupied for {minutes} minutes',
                details={'duration_minutes': minutes}
            )

            messages.success(request, f'Successfully occupied {resource.pc_name}')
            return JsonResponse({'success': True, 'message': 'Resource occupied successfully'})

    except Resource.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Resource not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def release_resource(request):
    """Release an occupied resource"""
    resource_id = request.POST.get('resource_id')

    try:
        with transaction.atomic():
            resource = Resource.objects.select_for_update().get(id=resource_id)
            current_usage = resource.get_current_usage()

            if not current_usage or current_usage.user != request.user:
                return JsonResponse({'success': False, 'message': 'You do not have access to this resource'})

            # End the usage session
            current_usage.end_time = timezone.now()
            current_usage.actual_duration = current_usage.end_time - current_usage.start_time
            current_usage.is_active = False
            current_usage.save()

            # Check for queued users
            next_in_queue = ResourceQueue.objects.filter(
                resource=resource,
                is_active=True
            ).order_by('joined_at').first()

            if next_in_queue:
                # Auto-assign to next user in queue
                ResourceUsage.objects.create(
                    resource=resource,
                    user=next_in_queue.user,
                    planned_duration=timedelta(hours=1)
                )

                # Remove from queue
                next_in_queue.is_active = False
                next_in_queue.save()

                SystemLog.objects.create(
                    log_type='RESOURCE',
                    user=next_in_queue.user,
                    resource=resource,
                    message=f'Resource {resource.pc_name} auto-assigned from queue'
                )
            else:
                # Make resource available
                resource.status = 'Available'
                resource.save()

            SystemLog.objects.create(
                log_type='RESOURCE',
                user=request.user,
                resource=resource,
                message=f'Resource {resource.pc_name} released'
            )

            messages.success(request, f'Successfully released {resource.pc_name}')
            return JsonResponse({'success': True, 'message': 'Resource released successfully'})

    except Resource.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Resource not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def join_queue(request):
    """Join the queue for a resource"""
    resource_id = request.POST.get('resource_id')
    requested_minutes = int(request.POST.get('minutes', 60))

    try:
        resource = get_object_or_404(Resource, id=resource_id, is_active=True)

        # Attempt to create an active queue entry; be defensive about races
        try:
            # position is optional; compute a simple default
            position = ResourceQueue.objects.filter(resource=resource, is_active=True).count() + 1
            queue_entry, created = ResourceQueue.objects.get_or_create(
                resource=resource,
                user=request.user,
                is_active=True,
                defaults={'position': position, 'requested_minutes': requested_minutes}
            )
        except IntegrityError:
            # A concurrent request likely created the same active tuple — fetch it
            queue_entry = ResourceQueue.objects.filter(
                resource=resource,
                user=request.user,
                is_active=True
            ).first()
            created = False

        if not created and queue_entry:
            return JsonResponse({'success': False, 'message': 'You are already in the queue'})

        # If created is True we have successfully added the user to the queue
        # Ensure estimated wait time is initialized
        # (queue_entry exists here and may be newly created)
        queue_entry.update_estimated_wait_time()

        SystemLog.objects.create(
            log_type='RESOURCE',
            user=request.user,
            resource=resource,
            message=f'User joined queue for {resource.pc_name}'
        )

        messages.success(request, f'Successfully joined queue for {resource.pc_name}')
        return JsonResponse({'success': True, 'message': 'Successfully joined queue'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def leave_queue(request):
    """Leave the queue for a resource"""
    resource_id = request.POST.get('resource_id')

    try:
        resource = get_object_or_404(Resource, id=resource_id)

        with transaction.atomic():
            queue_entry = ResourceQueue.objects.select_for_update().filter(
                resource=resource,
                user=request.user,
                is_active=True
            ).first()

            if not queue_entry:
                return JsonResponse({'success': False, 'message': 'You are not in the queue'})

            # Remove any historical inactive entries for this (resource, user) to
            # avoid violating the unique_together constraint when we flip the flag.
            ResourceQueue.objects.filter(
                resource=resource,
                user=request.user,
                is_active=False
            ).delete()

            queue_entry.is_active = False
            queue_entry.save()

        SystemLog.objects.create(
            log_type='RESOURCE',
            user=request.user,
            resource=resource,
            message=f'User left queue for {resource.pc_name}'
        )

        messages.success(request, f'Successfully left queue for {resource.pc_name}')
        return JsonResponse({'success': True, 'message': 'Successfully left queue'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def extend_time(request):
    """Extend usage time for current resource"""
    resource_id = request.POST.get('resource_id')
    extension_minutes = int(request.POST.get('minutes', 15))

    try:
        resource = get_object_or_404(Resource, id=resource_id)
        current_usage = resource.get_current_usage()

        if not current_usage or current_usage.user != request.user:
            return JsonResponse({'success': False, 'message': 'No active session found'})

        if current_usage.is_expired():
            return JsonResponse({'success': False, 'message': 'Session has already expired'})

        # Extend time
        current_usage.extend_time(extension_minutes)

        SystemLog.objects.create(
            log_type='RESOURCE',
            user=request.user,
            resource=resource,
            message=f'Extended time by {extension_minutes} minutes for {resource.pc_name}',
            details={'extension_minutes': extension_minutes}
        )

        return JsonResponse({
            'success': True, 
            'message': f'Time extended by {extension_minutes} minutes',
            'new_remaining_time': current_usage.get_remaining_time()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def get_status(request):
    """Get current status of resources for AJAX updates"""
    resources = Resource.objects.filter(is_active=True)
    status_data = []
    for resource in resources:
        current_usage = resource.get_current_usage()

        queue_entries = resource.queue_entries.filter(is_active=True).order_by('joined_at')
        queue_list = [{'username': q.user.username, 'minutes': q.requested_minutes} for q in queue_entries]
        user_in_queue = queue_entries.filter(user=request.user).exists()

        resource_status = {
            'id': resource.id,
            'pc_name': resource.pc_name,
            'ip_address': resource.ip_address,
            'resource_type': resource.resource_type,
            'status': resource.status,
            'queue_count': resource.get_queue_count(),
            'queue_list': queue_list,
            'current_user': None,
            'remaining_time': 0,
            'is_current_user': False,
            'is_in_queue': user_in_queue,
            'user_in_queue': user_in_queue,  # legacy key used in some client code
        }

        if current_usage:
            resource_status.update({
                'current_user': current_usage.user.username,
                'start_time': current_usage.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'remaining_time': current_usage.get_remaining_time(),
                'is_current_user': current_usage.user == request.user,
            })

        status_data.append(resource_status)

    return JsonResponse({'resources': status_data})

def update_expired_sessions():
    """Update expired resource sessions"""
    expired_usages = ResourceUsage.objects.filter(
        end_time__isnull=True,
        is_active=True
    )

    for usage in expired_usages:
        if usage.is_expired():
            with transaction.atomic():
                # Mark as expired and auto-released
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
                else:
                    # Make available
                    resource.status = 'Available'
                    resource.save()

                SystemLog.objects.create(
                    log_type='SYSTEM',
                    user=usage.user,
                    resource=resource,
                    message=f'Session auto-expired for {resource.pc_name}'
                )
