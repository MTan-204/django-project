from django.urls import path, include
from django.views.generic import RedirectView
from . import views

urlpatterns = [    

    path('', RedirectView.as_view(pattern_name='product_list', permanent=False)),
    
    path('accounts/', include('django.contrib.auth.urls')),
    path('login/', views.SiteLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('products/', views.product_list, name='product_list'),
    path('product/manage/', views.product_manage, name='product_manage'),
    path('product/update/<int:id>', views.product_update, name='product_update'),
    path('product/delete/<int:id>', views.product_delete, name='product_delete'),
    path('get-stock/', views.get_product_stock, name='get_stock'),

    path('category/add/', views.add_category, name='add_category'),
    path('category/delete/<int:id>/', views.delete_category, name='delete_category'),  

    path('unit/add/', views.add_unit, name='add_unit'),
    path('unit/delete/<int:id>/', views.delete_unit, name='delete_unit'),

    path('supplier/', views.supplier_manage, name='supplier'),
    path('supplier/delete/<int:id>/', views.delete_supplier, name='delete_supplier'),
    path('supplier/update/<int:id>/', views.update_supplier, name='update_supplier'),

    path('import-receipt/',views.import_receipt_list,name='import_receipt_list'),
    path('import_receipt/create/', views.import_receipt_create, name='import_receipt_create'),
    path('import-receipt/<int:pk>/confirm/', views.confirm_receipt, name='confirm_receipt'),
    path('import-receipt/<int:receipt_id>/payment/',views.payment_create,name='payment_create'),
    path('import_receipt_detail/<int:pk>/',views.import_receipt_detail,name='import_receipt_detail'),
    path('supplier/debt/',views.supplier_debt,name='supplier_debt'),
    path('import-receipt/<int:pk>/delete/', views.delete_import_receipt, name='delete_import_receipt'),
    
    path('customer/', views.customer_list, name='customer_list'),
    path('customer/create/', views.customer_create, name='customer_create'),
    path('customer/update/<int:id>/', views.customer_update, name='customer_update'),

    path('sale-invoice/create/', views.sale_invoice_create, name='sale_invoice_create'),
    path('sale-invoice/', views.sale_invoice_list, name='sale_invoice_list'),
    path('sale-invoice/<int:pk>/', views.sale_invoice_detail, name='sale_invoice_detail'),
    path('sale-invoice/<int:pk>/confirm/', views.confirm_sale_invoice, name='confirm_sale_invoice'),
    path('sale-invoice/<int:pk>/update/', views.sale_invoice_update, name='sale_invoice_update'),
    path('sale-invoice/<int:pk>/delete/', views.delete_sale_invoice, name='delete_sale_invoice'),
    path('sale-invoice/<int:invoice_id>/payment/', views.sale_payment_create, name='sale_payment_create'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('customer/debt/', views.customer_debt_list, name='customer_debt_list'),
    path('customer/debt/<int:customer_id>/', views.customer_debt_detail, name='customer_debt_detail'),
    path('statistics/sales/', views.sales_statistics, name='sales_statistics'),
    path('sale-invoice/<int:pk>/print/', views.sale_invoice_print, name='sale_invoice_print'),
    path('import-receipt/<int:pk>/print/', views.import_receipt_print, name='import_receipt_print'),

    path('pos/', views.pos_view, name='pos'),
    path('pos/add/', views.pos_add_to_cart, name='pos_add_to_cart'),
    path('pos/update/<int:variant_id>/', views.pos_update_cart, name='pos_update_cart'),
    path('pos/remove/<int:variant_id>/', views.pos_remove_from_cart, name='pos_remove_from_cart'),
    path('pos/clear/', views.pos_clear_cart, name='pos_clear_cart'),
    path('pos/checkout/', views.pos_checkout, name='pos_checkout'),
    path('pos/customer/create/', views.pos_customer_create, name='pos_customer_create'),

    path('accounts-manager/', views.account_list, name='account_list'),
    path('accounts-manager/create/', views.account_create, name='account_create'),
    path('accounts-manager/<int:user_id>/toggle-active/', views.account_toggle_active, name='account_toggle_active'),
    path('accounts-manager/<int:user_id>/update/', views.account_update, name='account_update'),
    path('accounts-manager/<int:user_id>/reset-password/', views.account_reset_password, name='account_reset_password'),
    
]
