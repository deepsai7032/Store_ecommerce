
from django.urls import path
from . import views

urlpatterns = [
    path("accounts/register/", views.register_view),
    path("accounts/login/", views.login_view),
    path("accounts/logout/", views.logout_view),
    path("cart/add/<int:product_id>/", views.add_to_cart_view),
    path("cart/", views.view_cart),
    path("cart/remove/<int:item_id>/", views.remove_cart_item),
    path("cart/update/<int:item_id>/", views.update_cart_quantity),
    path("cart/checkout/", views.checkout),
    path("store/", views.store_view),
    path("store/other/",views.store_view),
    path("store/<int:category_id>/", views.store_view),
    path('history/',views.purchase_history),
]