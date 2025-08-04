from functools import wraps
from django.http import JsonResponse
from rest_framework import status


def is_logged_in(view_func):
    """
    Simple decorator to check if user is authenticated.
    Returns JSON error response if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'You must be logged in to access this resource'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return view_func(request, *args, **kwargs)
    return wrapper


def is_admin_user(view_func):
    """
    Simple decorator to check if user is authenticated and is an admin.
    Returns JSON error response if not authenticated or not admin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'You must be logged in to access this resource'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not request.user.is_admin:
            return JsonResponse({
                'error': 'Permission denied',
                'message': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)

        return view_func(request, *args, **kwargs)
    return wrapper