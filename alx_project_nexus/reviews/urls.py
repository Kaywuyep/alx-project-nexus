from django.urls import path
from . import views


urlpatterns = [
    # Review endpoints
    path(
        '<int:product_id>/reviews/',
        views.ProductReviewView.as_view(), name='product-reviews'),
    path(
        'product/<int:product_id>/reviews/',
        views.add_product_review_function, name='add-review'),
]