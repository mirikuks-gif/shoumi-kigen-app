from django.urls import path
from .views import ManualRecipeSearchView
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('home/', views.home, name='home'),
    path('', views.home, name='home'),
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('item/update_quantity/<int:pk>/', views.update_ingredient_quantity, name='item_quantity_update'),
    path('item/add/', views.IngredientCreateView.as_view(), name='item_add'),
    path('item/edit/<int:pk>/', views.IngredientUpdateView.as_view(), name='item_edit'),
    path('item/delete/<int:pk>/', views.IngredientDeleteView.as_view(), name='item_delete'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('item/quick_add/<int:fixed_pk>/', views.quick_add_ingredient, name='item_quick_add'),
    path('item/quick_add_list/', views.QuickAddListView.as_view(), name='item_quick_add_list'),
    path('history/', views.UsageHistoryListView.as_view(), name='usage_history'),
    path('update/<int:pk>/', views.update_ingredient_quantity, name='update_quantity'),
    path('item/bulk_operation/', views.item_bulk_operation, name='item_bulk_operation'),
    path('recipes/search/', views.RecipeSearchView.as_view(), name='recipe_search'),
    path('recipes/manual_search/', ManualRecipeSearchView.as_view(), name='manual_recipe_search'),
]
