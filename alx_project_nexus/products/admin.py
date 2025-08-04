from django.contrib import admin
from django.utils.html import format_html
from reviews.admin import ReviewInline
from .models import Category, Product, ProductImage, Wishlist


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Preview"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'products_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "Products Count"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'brand', 'category', 'price', 'qty_left', 
        'total_sold', 'average_rating', 'is_in_stock', 
        'created_at'
    )
    list_filter = (
        'category', 'brand', 'created_at', 'sizes'
    )
    search_fields = ('name', 'description', 'brand')
    ordering = ('-created_at',)
    readonly_fields = (
        'qty_left', 'total_reviews', 'average_rating', 
        'is_in_stock', 'is_low_stock', 'created_at', 'updated_at'
    )
    filter_horizontal = ()

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'brand', 'category', 'user')
        }),
        ('Product Details', {
            'fields': ('sizes', 'price')
        }),
        ('Inventory', {
            'fields': ('total_qty', 'total_sold', 'qty_left')
        }),
        ('Status', {
            'fields': ('is_in_stock', 'is_low_stock'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_reviews', 'average_rating'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProductImageInline, ReviewInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'user'
        ).prefetch_related('images', 'reviews')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new product
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'image_preview', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    ordering = ('-created_at',)
    readonly_fields = ('image_preview', 'created_at')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Preview"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__fullname', 'user__email', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')
