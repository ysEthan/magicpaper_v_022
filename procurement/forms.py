from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, PurchaseOrder, PurchaseOrderItem


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'contact_phone', 'address', 'email', 'status', 'remark']
        widgets = {
            'remark': forms.Textarea(attrs={'rows': 3}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['order_number', 'supplier', 'expected_delivery_date', 'remark']
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'remark': forms.Textarea(attrs={'rows': 3}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['sku', 'quantity', 'unit_price', 'remark']
        widgets = {
            'remark': forms.Textarea(attrs={'rows': 2}),
        }


# 创建采购订单明细的内联表单集
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
) 