from django import forms
from .models import Warehouse, StockIn, StockOut, Inventory

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['warehouse_code', 'warehouse_name', 'location', 'manager', 'contact_phone', 'status']
        widgets = {
            'warehouse_code': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse_name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_warehouse_code(self):
        warehouse_code = self.cleaned_data['warehouse_code']
        if self.instance.pk is None:  # 新建
            if Warehouse.objects.filter(warehouse_code=warehouse_code).exists():
                raise forms.ValidationError('仓库编码已存在')
        else:  # 编辑
            if Warehouse.objects.filter(warehouse_code=warehouse_code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('仓库编码已存在')
        return warehouse_code

class StockInForm(forms.ModelForm):
    class Meta:
        model = StockIn
        fields = ['stock_in_code', 'warehouse', 'sku', 'stock_in_type', 'quantity', 'source_order', 'remark']
        widgets = {
            'stock_in_code': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.Select(attrs={'class': 'form-select'}),
            'stock_in_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'source_order': forms.TextInput(attrs={'class': 'form-control'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def clean_stock_in_code(self):
        stock_in_code = self.cleaned_data['stock_in_code']
        if StockIn.objects.filter(stock_in_code=stock_in_code).exists():
            raise forms.ValidationError('入库单号已存在')
        return stock_in_code

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError('入库数量必须大于0')
        return quantity

class StockOutForm(forms.ModelForm):
    class Meta:
        model = StockOut
        fields = ['stock_out_code', 'warehouse', 'sku', 'inventory', 'stock_out_type', 'quantity', 'related_order', 'remark']
        widgets = {
            'stock_out_code': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.Select(attrs={'class': 'form-select'}),
            'inventory': forms.Select(attrs={'class': 'form-select'}),
            'stock_out_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'related_order': forms.TextInput(attrs={'class': 'form-control'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 只显示有库存的批次
        if 'warehouse' in self.data and 'sku' in self.data:
            self.fields['inventory'].queryset = Inventory.objects.filter(
                warehouse_id=self.data['warehouse'],
                sku_id=self.data['sku'],
                quantity__gt=0
            )
        else:
            self.fields['inventory'].queryset = Inventory.objects.none()

    def clean_stock_out_code(self):
        stock_out_code = self.cleaned_data['stock_out_code']
        if StockOut.objects.filter(stock_out_code=stock_out_code).exists():
            raise forms.ValidationError('出库单号已存在')
        return stock_out_code

    def clean(self):
        cleaned_data = super().clean()
        inventory = cleaned_data.get('inventory')
        quantity = cleaned_data.get('quantity')
        
        if inventory and quantity:
            if quantity <= 0:
                raise forms.ValidationError('出库数量必须大于0')
            if quantity > inventory.quantity:
                raise forms.ValidationError('出库数量不能大于库存数量')
        
        return cleaned_data 