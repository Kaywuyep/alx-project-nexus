from django.urls import path
from . import views
from . import product_views  # Import function-based views


urlpatterns = [
    # Category endpoints
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:id>/', views.CategoryDetailView.as_view(), name='category-detail'),

    # Product endpoints (Class-based views)
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('productsp/<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:product_id>/images/', views.ProductImageUploadView.as_view(), name='product-image-upload'),

    # Wishlist endpoints
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:id>/', views.WishlistDetailView.as_view(), name='wishlist-detail'),

    # Admin endpoints
    path('admin/stats/', views.AdminProductStatsView.as_view(), name='admin-product-stats'),
    path('admin/low-stock/', views.AdminLowStockView.as_view(), name='admin-low-stock'),

    # Function-based views
    # path('products/', product_views.get_products_function, name='products-list'),
    # path('product/<int:product_id>/', product_views.get_product_detail_function, name='product-detail'),
    # path('product/create/', product_views.create_product_function, name='create-product'),
    # path('product/wishlist/', product_views.user_wishlist_function, name='wishlist'),
]
