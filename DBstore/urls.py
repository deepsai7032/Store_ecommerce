from django.urls import include,path
from . import views

urlpatterns=[
             path("products/view/", views.MAinview),
             path("products/add/", views.add_product),
             path("products/delete/<int:product_id>/", views.delete_product),
             path("products/update/", views.update_quantity),
             path("products/manage/", views.manage_products),
             path("products/manage/other/", views.manage_products, {"category_id": "other"}),
            path("products/manage/<int:category_id>/", views.manage_products),
             path("categories/add/", views.add_category),
             path("categories/delete/<int:category_id>/", views.delete_category),
             path("dashboard/", views.dashboard),
             path("trash/", views.trash_view),
            path("trash/restore-product/<int:product_id>/", views.restore_product),
            path("trash/restore-category/<int:category_id>/", views.restore_category),
            path("trash/delete-product/<int:product_id>/", views.permanently_delete_product),
            path("trash/delete-category/<int:category_id>/", views.permanently_delete_category),
             ]