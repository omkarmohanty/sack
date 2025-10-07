from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def get_theme(request):
    profile = getattr(request.user, 'profile', None)
    theme = profile.theme if profile else 'light'
    return JsonResponse({'theme': theme})


@login_required
@require_POST
def set_theme(request):
    theme = request.POST.get('theme', 'light')
    if theme not in ('light', 'dark'):
        return JsonResponse({'success': False, 'message': 'Invalid theme'})
    profile = getattr(request.user, 'profile', None)
    if profile:
        profile.theme = theme
        profile.save()
    else:
        # create quickly
        from .models import UserProfile
        UserProfile.objects.create(user=request.user, theme=theme)
    return JsonResponse({'success': True, 'theme': theme})
