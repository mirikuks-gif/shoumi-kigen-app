# items/forms.py
from django import forms
from .models import Ingredient, Location, Category

class IngredientForm(forms.ModelForm):

    other_location = forms.CharField(
        max_length=100,
        required=False,
        label='新しい保存場所',
        widget=forms.TextInput(attrs={'placeholder': '例: ベランダ、ガレージ'}),
    )

    class Meta:
        model = Ingredient
        fields = ('name', 'category', 'location', 'expiry_date', 'quantity','price','store_name')
        widgets = {
            # ★★★ nameフィールドに autocomplete="off" を追加 ★★★
            'name': forms.TextInput(attrs={'autocomplete': 'off'}),
            
            # ★★★ categoryフィールドにも autocomplete="off" を追加 ★★★
            'category': forms.Select(attrs={'autocomplete': 'off'}),

            # 既存の expiry_date の設定はそのまま維持
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            
            # price, store_nameなども必要であれば設定
            # 'price': forms.NumberInput(attrs={'autocomplete': 'off'}),
        }