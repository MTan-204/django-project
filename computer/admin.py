from django.contrib import admin
from .models import Product, Category, ProductVariant, Unit, Supplier, ImportReceipt, ImportReceiptDetail, Payment, Customer, SaleInvoice,SaleInvoiceDetail,SalePayment

admin.site.register(Product)
admin.site.register(Category)
admin.site.register(ProductVariant)
admin.site.register(Unit)
admin.site.register(Supplier)
admin.site.register(ImportReceipt)
admin.site.register(ImportReceiptDetail)
admin.site.register(Payment)
admin.site.register(Customer)
admin.site.register(SaleInvoice)
admin.site.register(SaleInvoiceDetail)
admin.site.register(SalePayment)