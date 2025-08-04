from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, ShippingAddress


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'fullname')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'fullname', 'is_admin', 'has_shipping_address')


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    can_delete = True


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = (
        'email', 'fullname', 'is_admin', 'has_shipping_address', 
        'is_active', 'date_joined'
    )
    list_filter = (
        'is_admin', 'has_shipping_address', 'is_active', 
        'is_staff', 'date_joined'
    )
    search_fields = ('email', 'fullname')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('fullname',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('E-commerce', {'fields': ('has_shipping_address',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'fullname', 'password1', 'password2'),
        }),
    )
    
    inlines = [ShippingAddressInline]


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'first_name', 'last_name', 'city', 
        'country', 'created_at'
    )
    list_filter = ('country', 'province', 'created_at')
    search_fields = (
        'user__email', 'first_name', 'last_name', 
        'city', 'country'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'postal_code', 'province', 'country')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
