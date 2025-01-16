from django import forms
from .models import DemandRequest, DemandTracking, ProductionOrder

class DemandRequestForm(forms.ModelForm):
    class Meta:
        model = DemandRequest
        fields = [
            'title', 'request_type', 'priority',
            'description', 'expected_completion_date', 'attachments', 'remark'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '需求标题'
            }),
            'request_type': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': '选择需求类型'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': '选择优先级'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '需求描述'
            }),
            'expected_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '预期完成日期'
            }),
            'remark': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '备注'
            }),
            'attachments': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('attachments'):
            self.initial['attachments'] = []

class DemandTrackingForm(forms.ModelForm):
    class Meta:
        model = DemandTracking
        fields = ['tracking_type', 'content', 'attachments']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
            'attachments': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        if not self.initial.get('attachments'):
            self.initial['attachments'] = []

class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = [
            'sku', 'quantity', 'production_start_date', 'production_end_date',
            'materials', 'quality_requirements', 'production_instructions', 'remark'
        ]
        widgets = {
            'production_start_date': forms.DateInput(attrs={'type': 'date'}),
            'production_end_date': forms.DateInput(attrs={'type': 'date'}),
            'quality_requirements': forms.Textarea(attrs={'rows': 3}),
            'production_instructions': forms.Textarea(attrs={'rows': 3}),
            'remark': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        self.fields['sku'].queryset = self.fields['sku'].queryset.order_by('sku_code')

class ProductionUpdateForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = [
            'completed_quantity', 'defective_quantity', 'status',
            'actual_start_date', 'actual_end_date', 'remark'
        ]
        widgets = {
            'actual_start_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_end_date': forms.DateInput(attrs={'type': 'date'}),
            'remark': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'}) 