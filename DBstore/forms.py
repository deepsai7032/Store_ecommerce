from django import forms
from .models import Product,Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

class UpdateQuantityForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["quantity",'price','category']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]