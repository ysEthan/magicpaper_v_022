from django import forms
from .models import Brand, Category, SPU, SKU

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'description', 'logo_url', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo_url': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name_en', 'category_name_zh', 'description', 'image', 
                 'parent', 'rank_id', 'level', 'is_last_level', 'status']
        widgets = {
            'category_name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'category_name_zh': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'rank_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'is_last_level': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class SPUForm(forms.ModelForm):
    class Meta:
        model = SPU
        fields = ['spu_code', 'spu_name', 'product_type', 'spu_remark', 
                 'sales_channel', 'brand', 'poc', 'category', 'status']
        widgets = {
            'spu_code': forms.TextInput(attrs={'class': 'form-control'}),
            'spu_name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'spu_remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sales_channel': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'poc': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SKUForm(forms.ModelForm):
    class Meta:
        model = SKU
        fields = ['sku_code', 'sku_name', 'spu', 'material', 'color', 
                 'plating_process', 'surface_treatment', 'weight', 'length', 
                 'width', 'height', 'other_dimensions', 'suppliers_list', 
                 'img_url', 'status']
        widgets = {
            'sku_code': forms.TextInput(attrs={'class': 'form-control'}),
            'sku_name': forms.TextInput(attrs={'class': 'form-control'}),
            'spu': forms.Select(attrs={'class': 'form-select'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'plating_process': forms.Select(attrs={'class': 'form-select'}),
            'surface_treatment': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'length': forms.NumberInput(attrs={'class': 'form-control'}),
            'width': forms.NumberInput(attrs={'class': 'form-control'}),
            'height': forms.NumberInput(attrs={'class': 'form-control'}),
            'other_dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'suppliers_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'img_url': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        } 