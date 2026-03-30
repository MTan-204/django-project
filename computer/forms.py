from django import forms
from django.forms import inlineformset_factory
from .models import ImportReceipt, ImportReceiptDetail, SaleInvoice, SaleInvoiceDetail, Customer

class ImportReceiptForm(forms.ModelForm):
    class Meta:
        model = ImportReceipt
        fields = ['supplier']


ImportReceiptDetailFormSet = inlineformset_factory(
    ImportReceipt,
    ImportReceiptDetail,
    fields=('product_variant', 'quantity', 'price'),
    extra=3,   # hiển thị 3 dòng nhập sản phẩm
    can_delete=True
)


class SaleInvoiceForm(forms.ModelForm):
    class Meta:
        model = SaleInvoice
        fields = ['customer', 'discount_type', 'discount_value', 'note']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1', 'value': '0'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        active_customers = Customer.objects.filter(is_active=True).order_by('name')

        if self.instance and self.instance.pk and self.instance.customer_id:
            self.fields['customer'].queryset = (
                Customer.objects.filter(is_active=True) |
                Customer.objects.filter(pk=self.instance.customer_id)
            ).order_by('name').distinct()
        else:
            self.fields['customer'].queryset = active_customers

        self.fields['customer'].required = False
        self.fields['customer'].empty_label = '-- Khách lẻ --'

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value') or 0

        if discount_value < 0:
            raise forms.ValidationError("Giá trị giảm giá không được âm.")

        if discount_type == 'none':
            cleaned_data['discount_value'] = 0

        if discount_type == 'percent' and discount_value > 100:
            raise forms.ValidationError("Giảm giá theo phần trăm không được vượt quá 100%.")

        return cleaned_data

    

SaleInvoiceDetailFormSet = inlineformset_factory(
    SaleInvoice,
    SaleInvoiceDetail,
    fields=('product_variant', 'quantity', 'price'),
    extra=3,
    can_delete=True,
    widgets={
        'product_variant': forms.Select(attrs={'class': 'form-control'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
    }
)