from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin
        )


class IsRegularUser(permissions.BasePermission):
    """
    Custom permission for regular users (non-admin).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            not request.user.is_admin
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admin users to access it.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated
        )
    
    def has_object_permission(self, request, view, obj):
        # Admin users can access everything
        if request.user.is_admin:
            return True
        
        # Object owner can access their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If object is the user themselves
        if obj == request.user:
            return True
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to all users,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin
        )