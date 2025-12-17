from django.contrib import admin
from .models import Location, Ingredient,Category, FixedIngredient
admin.site.register(Location)
admin.site.register(Ingredient)
admin.site.register(Category)
admin.site.register(FixedIngredient)