from django import forms
import json

class GuestOrderForm(forms.Form):
    """访客下单表单"""
    name = forms.CharField(
        label='收货人姓名',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        label='联系电话',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        label='收货地址',
        max_length=200,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    items_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    remark = forms.CharField(
        label='备注',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def clean_items_json(self):
        try:
            items = json.loads(self.cleaned_data['items_json'])
            if not items:
                raise forms.ValidationError('请至少添加一个商品')
            for item in items:
                if not isinstance(item.get('sku_code'), str) or not item.get('sku_code').strip():
                    raise forms.ValidationError('商品编码不能为空')
                if not isinstance(item.get('quantity'), int) or item.get('quantity') < 1:
                    raise forms.ValidationError('商品数量必须大于0')
            return items
        except json.JSONDecodeError:
            raise forms.ValidationError('商品数据格式错误')

class GuestOrderQueryForm(forms.Form):
    """访客订单查询表单"""
    phone = forms.CharField(
        label='手机号码',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入下单时使用的手机号码'
        })
    ) 