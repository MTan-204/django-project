from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models.functions import Coalesce,TruncDate, TruncMonth
from django.utils import timezone
from django.urls import reverse
from .models import Product, ProductVariant, Category, Unit, Supplier, ImportReceiptDetail, ImportReceipt, Payment, Customer, SaleInvoice, SalePayment,SaleInvoiceDetail, UserProfile
from .forms import ImportReceiptForm, ImportReceiptDetailFormSet, SaleInvoiceForm, SaleInvoiceDetailFormSet
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, F,ExpressionWrapper, DecimalField, Value, Count, Q
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, login_not_required
from django.contrib.auth import logout
import json
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from functools import wraps
from django.contrib.auth.models import User
from datetime import datetime, time
class SiteLoginView(LoginView):
     template_name = 'login.html'
     def get_success_url(self):
        return reverse('pos')
     def form_invalid(self, form):
        messages.error(self.request, "Banh rồi !!!")
        return super().form_invalid(form)
def logout_view(request):
    logout(request)
    return redirect('login')

@login_not_required
def product_list(request):
    products = ProductVariant.objects.select_related(
        'product','product__category').order_by('product__name')
    categories = Category.objects.all()
    units = Unit.objects.all()
    context = {
        'products': products,
        'categories': categories,
        'units': units
    }
    return render(request, 'product_list.html', context)

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not request.user.is_superuser:
            messages.error(request, "Bạn không có quyền truy cập chức năng này.")
            return redirect('pos')

        return view_func(request, *args, **kwargs)
    return _wrapped_view
@admin_required
def product_manage(request):
    low_stock_threshold = 10
    stock_filter = request.GET.get('stock')

    products = ProductVariant.objects.select_related(
        'product', 'product__category', 'unit'
    )

    if stock_filter == 'low':
        products = products.filter(stock__lte=low_stock_threshold)

    categories = Category.objects.all()
    units = Unit.objects.all()

    low_stock_count = ProductVariant.objects.filter(
        stock__lte=low_stock_threshold
    ).count()

    if request.method == 'POST':
        name = request.POST['name']
        brand = request.POST['brand']
        category = request.POST['category']
        unit_id = request.POST['unit']
        selling_price = request.POST['selling_price']
        image = request.FILES.get('image')

        product = Product.objects.create(
            name=name,
            category_id=category,
            brand=brand,
            image=image
        )

        ProductVariant.objects.create(
            product=product,
            selling_price=selling_price,
            unit_id=unit_id,
            stock=0
        )

        messages.success(request, 'Thêm sản phẩm thành công!')
        return redirect('product_manage')

    return render(request, 'product_manage.html', {
        'products': products,
        'categories': categories,
        'units': units,
        'low_stock_threshold': low_stock_threshold,
        'low_stock_count': low_stock_count,
        'stock_filter': stock_filter,
    })
@admin_required
def product_update(request, id):
    variant = get_object_or_404(ProductVariant, id=id)

    if request.method == "POST":
        variant.product.name = request.POST.get("name")
        variant.product.brand = request.POST.get("brand")
        variant.product.category_id = request.POST.get("category")

        new_image = request.FILES.get("image")
        if new_image:
            variant.product.image = new_image

        variant.unit_id = request.POST.get("unit")
        variant.stock = request.POST.get("stock")
        variant.selling_price = request.POST.get("price")

        is_active_value = request.POST.get("is_active")
        variant.is_active = True if is_active_value == "True" else False

        variant.product.save()
        variant.save()

        messages.success(request, "Cập nhật thành công")
        return redirect("product_manage")

    categories = Category.objects.all()
    units = Unit.objects.all()

    return render(request, "product_update.html", {
        "products": variant,
        "categories": categories,
        "units": units
    })
@admin_required
def product_delete(request,id):
    variant = get_object_or_404(ProductVariant, id=id)
    variant.is_active = False
    variant.save()
    messages.success(request,'Đã ngừng bán sản phẩm!')
    return redirect('/product/manage')

@admin_required
def add_category(request):
    if request.method == "POST":
        data = json.loads(request.body)

        name = data.get("name")

        if name:
            Category.objects.create(name=name)
            return JsonResponse({"status": "ok"})
@admin_required
def delete_category(request, id):

    category = get_object_or_404(Category, id=id)
    # kiểm tra sản phẩm có dùng category này không
    if Product.objects.filter(category=category).exists():
        messages.error(request, "Không thể xóa danh mục vì đang có sản phẩm sử dụng.")
        return redirect('/product/manage')

    category.delete()

    return redirect('/product/manage')
@admin_required
def add_unit(request):
    if request.method == "POST":
        data = json.loads(request.body)

        name = data.get("name")

        if name:
            Unit.objects.create(name=name)
            return JsonResponse({"status": "ok"})
@admin_required
def delete_unit(request, id):
    unit = get_object_or_404(Unit, id=id)
    if ProductVariant.objects.filter(unit=unit).exists():
        messages.error(request, "Không thể xóa  vì đang có sản phẩm sử dụng.")
        return redirect('/product/manage')
    unit.delete()
    return redirect('/product/manage')
@admin_required
def supplier_manage(request):
    suppliers = Supplier.objects.all()
    if request.method == "POST":
        name = request.POST['name']
        phone = request.POST['phone']
        address = request.POST['address']
        Supplier.objects.create(
        name = name,
        phone = phone,
        address = address,
    )
        messages.success(request,'Thêm nhà cung cấp thành công!')
        
    return render(request,'supplier.html',{
        'suppliers': suppliers
    })
@admin_required
def delete_supplier(request,id):
    supplier = get_object_or_404(Supplier,id=id)
    supplier.is_active = False
    supplier.save()
    messages.success(request,"Nhà cung cấp đã ngừng hoạt động")
    return redirect('/supplier/')
@admin_required
def update_supplier(request, id):
    supplier = Supplier.objects.get(id=id)

    if request.method == "POST":
        supplier.name = request.POST['name']
        supplier.phone = request.POST['phone']
        supplier.address = request.POST['address']
        supplier.is_active = not supplier.is_active
        supplier.save()

        messages.success(request, "Cập nhật nhà cung cấp thành công!")
        return redirect('supplier')

    return render(request, 'supplier_update.html', {
        'supplier': supplier
    })
@admin_required
def import_receipt_create(request):

    if request.method == 'POST':
        form = ImportReceiptForm(request.POST)
        formset = ImportReceiptDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            receipt = form.save(commit=False)
            receipt.created_by = request.user
            receipt.save()

            details = formset.save(commit=False)

            for d in details:
                d.receipt = receipt
                d.save()

            receipt.recalc_total()

            messages.success(request, "Tạo phiếu nhập thành công")

            return redirect('import_receipt_list')

    else:
        form = ImportReceiptForm()
        formset = ImportReceiptDetailFormSet()

    return render(request, 'import_receipt_create.html', {
        'form': form,
        'formset': formset
    })
@admin_required
def import_receipt_print(request, pk):
    receipt = get_object_or_404(
        ImportReceipt.objects.select_related('supplier','created_by'),
        pk=pk
    )
    details = ImportReceiptDetail.objects.select_related(
        'product_variant',
        'product_variant__product',
        'product_variant__unit'
    ).filter(receipt=receipt)

    payments = receipt.payments.all()

    return render(request, 'import_receipt_print.html', {
        'receipt': receipt,
        'details': details,
        'payments': payments
    })
@admin_required
def import_receipt_list(request):
    receipts = ImportReceipt.objects.select_related('supplier').all().order_by('-id')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    def parse_html_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    parsed_date_from = parse_html_date(date_from)
    parsed_date_to = parse_html_date(date_to)

    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        parsed_date_from, parsed_date_to = parsed_date_to, parsed_date_from
        date_from, date_to = date_to, date_from

    def make_start_datetime(date_obj):
        dt = datetime.combine(date_obj, time.min)
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def make_end_datetime(date_obj):
        dt = datetime.combine(date_obj, time.max)
        return timezone.make_aware(dt, timezone.get_current_timezone())

    if parsed_date_from:
        invoices = invoices.filter(created_at__gte=make_start_datetime(parsed_date_from))

    if parsed_date_to:
        invoices = invoices.filter(created_at__lte=make_end_datetime(parsed_date_to))
    summary = receipts.aggregate(
        total_import=Coalesce(
        Sum('total_amount'),
        Value(Decimal('0.00')),
        output_field=DecimalField(max_digits=12, decimal_places=2)
),
        total_paid=Coalesce(
        Sum('paid_amount'),
        Value(Decimal('0.00')),
        output_field=DecimalField(max_digits=12, decimal_places=2)
),
        total_debt=Coalesce(
            Sum(
                ExpressionWrapper(
                    F('total_amount') - F('paid_amount'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            ),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )

    return render(request, 'import_receipt_list.html', {
        'receipts': receipts,
        'total_import': summary['total_import'],
        'total_paid': summary['total_paid'],
        'total_debt': summary['total_debt'],
        'date_from': date_from,
        'date_to': date_to,
        
    })
@admin_required
def import_receipt_detail(request, pk):

    receipt = ImportReceipt.objects.get(pk=pk)

    details = receipt.details.select_related("product_variant__product")

    payments = receipt.payments.all()

    return render(request,"import_receipt_detail.html",{
        "receipt":receipt,
        "details":details,
        "payments":payments
    })
@admin_required
def delete_import_receipt(request, pk):
    receipt = get_object_or_404(ImportReceipt, pk=pk)

    if receipt.status != 'draft':
        messages.error(request, "Chỉ được xóa phiếu nhập ở trạng thái nháp.")
        return redirect('import_receipt_list')

    if receipt.payments.exists():
        messages.error(request, "Không thể xóa phiếu nhập đã phát sinh thanh toán.")
        return redirect('import_receipt_list')

    receipt.delete()
    messages.success(request, f"Đã xóa phiếu nhập #{pk} thành công.")
    return redirect('import_receipt_list')
@admin_required
def get_product_stock(request):

    product_id = request.GET.get('product_id')

    product = ProductVariant.objects.get(id=product_id)

    return JsonResponse({
        'stock': product.stock
    })
@admin_required
def confirm_receipt(request, pk):

    receipt = get_object_or_404(ImportReceipt, pk=pk)

    try:
        receipt.confirm()
        messages.success(request, "Xác nhận phiếu nhập thành công")
    except Exception as e:
        messages.error(request, str(e))

    return redirect('import_receipt_detail', pk=pk)
@admin_required
def payment_create(request, receipt_id):
    receipt = get_object_or_404(ImportReceipt, pk=receipt_id)

    if request.method == "POST":
        amount_raw = request.POST.get("amount", "").strip()
        note = request.POST.get("note", "").strip()

        try:
            amount = Decimal(amount_raw)

            if amount <= 0:
                messages.error(request, "Số tiền thanh toán phải lớn hơn 0.")
                return redirect("import_receipt_detail", pk=receipt_id)

            Payment.objects.create(
                receipt=receipt,
                amount=amount,
                note=note
            )

            messages.success(request, "Thanh toán thành công.")

        except InvalidOperation:
            messages.error(request, "Số tiền không hợp lệ.")
        except ValidationError as e:
            if hasattr(e, "messages") and e.messages:
                messages.error(request, e.messages[0])
            else:
                messages.error(request, "Dữ liệu thanh toán không hợp lệ.")
        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    return redirect("import_receipt_detail", pk=receipt_id)
@admin_required
def supplier_debt(request):

    suppliers = Supplier.objects.annotate(
        total_import=Sum('receipts__total_amount'),
        total_paid=Sum('receipts__paid_amount'),
    )

    for s in suppliers:
        s.total_import = s.total_import or 0
        s.total_paid = s.total_paid or 0
        s.debt = s.total_import - s.total_paid

    return render(request, 'supplier_debt.html', {
        'suppliers': suppliers
    })

from datetime import datetime

from datetime import datetime, time
from django.utils import timezone

def sale_invoice_list(request):
    invoices = SaleInvoice.objects.select_related('customer', 'created_by').all().order_by('-id')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    def parse_html_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    parsed_date_from = parse_html_date(date_from)
    parsed_date_to = parse_html_date(date_to)

    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        parsed_date_from, parsed_date_to = parsed_date_to, parsed_date_from
        date_from, date_to = date_to, date_from

    def make_start_datetime(date_obj):
        dt = datetime.combine(date_obj, time.min)
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def make_end_datetime(date_obj):
        dt = datetime.combine(date_obj, time.max)
        return timezone.make_aware(dt, timezone.get_current_timezone())

    if parsed_date_from:
        invoices = invoices.filter(created_at__gte=make_start_datetime(parsed_date_from))

    if parsed_date_to:
        invoices = invoices.filter(created_at__lte=make_end_datetime(parsed_date_to))

    return render(request, 'sale_invoice_list.html', {
        'invoices': invoices,
        'date_from': date_from,
        'date_to': date_to,
    })

def sale_invoice_print(request, pk):
    invoice = get_object_or_404(
        SaleInvoice.objects.select_related('customer','created_by'),
        pk=pk
    )
    details = invoice.details.select_related(
        'product_variant',
        'product_variant__product',
        'product_variant__unit'
    ).all()
    payments = invoice.payments.all()

    return render(request, 'sale_invoice_print.html', {
        'invoice': invoice,
        'details': details,
        'payments': payments
    })

def sale_invoice_create(request):
    if request.method == 'POST':
        form = SaleInvoiceForm(request.POST)
        formset = SaleInvoiceDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.total_amount = 0
            invoice.created_by= request.user
            invoice.discount_amount = 0
            invoice.final_amount = 0
            invoice.status = 'draft'
            invoice.save()

            details = formset.save(commit=False)

            has_detail = False
            for d in details:
                if d.product_variant and d.quantity and d.price:
                    d.invoice = invoice
                    d.save()
                    has_detail = True

            for obj in formset.deleted_objects:
                if obj.pk:
                    obj.delete()

            if not has_detail:
                invoice.delete()
                messages.error(request, "Hóa đơn bán phải có ít nhất 1 sản phẩm.")
                return render(request, 'sale_invoice_create.html', {
                    'form': form,
                    'formset': formset
                })

            invoice.recalc_total()

            messages.success(request, "Tạo hóa đơn bán thành công.")
            return redirect('sale_invoice_list')

        messages.error(request, "Vui lòng kiểm tra lại dữ liệu hóa đơn bán.")
    else:
        form = SaleInvoiceForm()
        formset = SaleInvoiceDetailFormSet()

    return render(request, 'sale_invoice_create.html', {
        'form': form,
        'formset': formset
    })

def sale_invoice_detail(request, pk):
    invoice = get_object_or_404(
        SaleInvoice.objects.select_related('customer','created_by'),
        pk=pk
    )
    details = invoice.details.select_related('product_variant', 'product_variant__product','product_variant__unit').all()
    payments = invoice.payments.all()

    return render(request, 'sale_invoice_detail.html', {
        'invoice': invoice,
        'details': details,
        'payments': payments
    })

@admin_required
def confirm_sale_invoice(request, pk):
    invoice = get_object_or_404(SaleInvoice, pk=pk)

    try:
        invoice.confirm()
        messages.success(request, f"Đã xác nhận hóa đơn bán #{pk} và cập nhật tồn kho thành công.")
    except ValidationError as e:
        if hasattr(e, 'messages') and e.messages:
            messages.error(request, e.messages[0])
        else:
            messages.error(request, "Không thể xác nhận hóa đơn bán.")
    except Exception as e:
        messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    return redirect('sale_invoice_list')

def customer_list(request):
    customers = Customer.objects.all().order_by('name')
    return render(request, 'customer_list.html', {
        'customers': customers
    })

def delete_sale_invoice(request, pk):
    invoice = get_object_or_404(SaleInvoice, pk=pk)

    if invoice.status != 'draft':
        messages.error(request, "Chỉ được xóa hóa đơn bán ở trạng thái nháp.")
        return redirect('sale_invoice_list')

    invoice.delete()
    messages.success(request, f"Đã xóa hóa đơn bán #{pk} thành công.")
    return redirect('sale_invoice_list')

def sale_invoice_update(request, pk):
    invoice = get_object_or_404(SaleInvoice, pk=pk)

    if invoice.status != 'draft':
        messages.error(request, "Chỉ được sửa hóa đơn bán ở trạng thái nháp.")
        return redirect('sale_invoice_list')

    if request.method == 'POST':
        form = SaleInvoiceForm(request.POST, instance=invoice)
        formset = SaleInvoiceDetailFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.save()

            details = formset.save(commit=False)

            for d in details:
                if d.product_variant and d.quantity and d.price:
                    d.invoice = invoice
                    d.save()

            for obj in formset.deleted_objects:
                if obj.pk:
                    obj.delete()

            if not invoice.details.exists():
                messages.error(request, "Hóa đơn bán phải có ít nhất 1 sản phẩm.")
                return render(request, 'sale_invoice_update.html', {
                    'form': form,
                    'formset': formset,
                    'invoice': invoice
                })

            invoice.recalc_total()

            messages.success(request, f"Cập nhật hóa đơn bán #{pk} thành công.")
            return redirect('sale_invoice_list')

        messages.error(request, "Vui lòng kiểm tra lại dữ liệu hóa đơn bán.")
    else:
        form = SaleInvoiceForm(instance=invoice)
        formset = SaleInvoiceDetailFormSet(instance=invoice)

    return render(request, 'sale_invoice_update.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice
    })

def sale_payment_create(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, pk=invoice_id)

    if request.method == "POST":
        amount_raw = request.POST.get("amount", "").strip()
        note = request.POST.get("note", "").strip()

        try:
            amount = Decimal(amount_raw)

            if invoice.status != 'confirmed':
                messages.error(request, "Chỉ thanh toán khi hóa đơn đã xác nhận.")
                return redirect('sale_invoice_detail', pk=invoice_id)

            if not invoice.customer_id:
                messages.error(request, "Hóa đơn khách lẻ không cần thanh toán công nợ.")
                return redirect('sale_invoice_detail', pk=invoice_id)

            if invoice.payment_status == 'paid':
                messages.error(request, "Hóa đơn này đã thanh toán đủ.")
                return redirect('sale_invoice_detail', pk=invoice_id)

            if amount <= 0:
                messages.error(request, "Số tiền thanh toán phải lớn hơn 0.")
                return redirect('sale_invoice_detail', pk=invoice_id)

            SalePayment.objects.create(
                invoice=invoice,
                amount=amount,
                note=note
            )

            messages.success(request, "Thanh toán hóa đơn bán thành công.")

        except InvalidOperation:
            messages.error(request, "Số tiền không hợp lệ.")
        except ValidationError as e:
            if hasattr(e, "messages") and e.messages:
                messages.error(request, e.messages[0])
            else:
                messages.error(request, "Dữ liệu thanh toán không hợp lệ.")
        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    return redirect('sale_invoice_detail', pk=invoice_id)

def customer_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        if not name:
            messages.error(request, "Tên khách hàng không được để trống.")
            return redirect('customer_create')

        Customer.objects.create(
            name=name,
            phone=phone if phone else None,
            address=address if address else None,
            is_active=True
        )

        messages.success(request, "Thêm khách hàng thành công.")
        return redirect('customer_list')

    return render(request, 'customer_create.html')


def customer_update(request, id):
    customer = get_object_or_404(Customer, id=id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        is_active = request.POST.get('is_active')

        if not name:
            messages.error(request, "Tên khách hàng không được để trống.")
            return redirect('customer_update', id=id)

        customer.name = name
        customer.phone = phone if phone else None
        customer.address = address if address else None
        customer.is_active = True if is_active == 'True' else False
        customer.save()

        messages.success(request, "Cập nhật khách hàng thành công.")
        return redirect('customer_list')

    return render(request, 'customer_update.html', {
        'customer': customer
    })

# DASHBOARD
from .models import (
    ProductVariant, Customer, Supplier,
    ImportReceipt, SaleInvoice
)


@admin_required
def dashboard(request):
    today = timezone.localdate()
    first_day_of_month = today.replace(day=1)

    money_field = DecimalField(max_digits=12, decimal_places=2)
    money_zero = Value(Decimal('0.00'), output_field=money_field)

    confirmed_receipts = ImportReceipt.objects.filter(status='confirmed')
    confirmed_sales = SaleInvoice.objects.filter(status='confirmed')

    total_products = ProductVariant.objects.filter(
        is_active=True,
        product__is_active=True
    ).count()

    total_customers = Customer.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_import_receipts = ImportReceipt.objects.count()
    total_sale_invoices = SaleInvoice.objects.count()

    total_supplier_debt = confirmed_receipts.aggregate(
        total=Coalesce(
            Sum(F('total_amount') - F('paid_amount')),
            money_zero,
            output_field=money_field
        )
    )['total']

    total_customer_debt = confirmed_sales.filter(customer__isnull=False).aggregate(
        total=Coalesce(
            Sum(F('total_amount') - F('paid_amount')),
            money_zero,
            output_field=money_field
        )
    )['total']

    today_revenue = confirmed_sales.filter(created_at__date=today).aggregate(
        total=Coalesce(
            Sum('total_amount'),
            money_zero,
            output_field=money_field
        )
    )['total']

    month_revenue = confirmed_sales.filter(created_at__date__gte=first_day_of_month).aggregate(
        total=Coalesce(
            Sum('total_amount'),
            money_zero,
            output_field=money_field
        )
    )['total']

    low_stock_products = ProductVariant.objects.select_related('product', 'unit').filter(
        is_active=True,
        product__is_active=True,
        stock__lte=10
    ).order_by('stock', 'product__name')[:10]

    recent_sales = SaleInvoice.objects.select_related('customer').order_by('-id')[:5]
    recent_receipts = ImportReceipt.objects.select_related('supplier').order_by('-id')[:5]

    top_selling_products = (
    SaleInvoiceDetail.objects
    .filter(invoice__status='confirmed')
    .values(
        product_name=F('product_variant__product__name'),
        unit_name=F('product_variant__unit__name'),
    )
    .annotate(
        total_sold=Sum('quantity'),
        total_revenue=Coalesce(
            Sum('subtotal'),
            money_zero,
            output_field=money_field
        )
    )
    .order_by('-total_sold', '-total_revenue')[:10]
)
    return render(request, 'dashboard.html', {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'total_import_receipts': total_import_receipts,
        'total_sale_invoices': total_sale_invoices,
        'total_supplier_debt': total_supplier_debt,
        'total_customer_debt': total_customer_debt,
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
        'low_stock_products': low_stock_products,
        'top_selling_products': top_selling_products,
        'recent_sales': recent_sales,
        'recent_receipts': recent_receipts,
    })
@admin_required
def customer_debt_list(request):
    money_field = DecimalField(max_digits=12, decimal_places=2)
    money_zero = Value(Decimal('0.00'), output_field=money_field)

    customer_debts = (
        SaleInvoice.objects
        .filter(status='confirmed', customer__isnull=False)
        .values(
            'customer_id',
            'customer__name',
            'customer__phone',
            'customer__address',
        )
        .annotate(
            invoice_count=Count('id'),
            total_purchase=Coalesce(
                Sum('total_amount'),
                money_zero,
                output_field=money_field
            ),
            total_paid=Coalesce(
                Sum('paid_amount'),
                money_zero,
                output_field=money_field
            ),
            total_debt=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('total_amount') - F('paid_amount'),
                        output_field=money_field
                    )
                ),
                money_zero,
                output_field=money_field
            )
        )
        .order_by('-total_debt', 'customer__name')
    )

    summary = SaleInvoice.objects.filter(status='confirmed', customer__isnull=False).aggregate(
        total_purchase=Coalesce(
            Sum('total_amount'),
            money_zero,
            output_field=money_field
        ),
        total_paid=Coalesce(
            Sum('paid_amount'),
            money_zero,
            output_field=money_field
        ),
        total_debt=Coalesce(
            Sum(
                ExpressionWrapper(
                    F('total_amount') - F('paid_amount'),
                    output_field=money_field
                )
            ),
            money_zero,
            output_field=money_field
        )
    )

    return render(request, 'customer_debt_list.html', {
        'customer_debts': customer_debts,
        'total_purchase': summary['total_purchase'],
        'total_paid': summary['total_paid'],
        'total_debt': summary['total_debt'],
    })


def customer_debt_detail(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)

    invoices = SaleInvoice.objects.filter(
        status='confirmed',
        customer_id=customer_id
    ).order_by('-id')

    money_field = DecimalField(max_digits=12, decimal_places=2)
    money_zero = Value(Decimal('0.00'), output_field=money_field)

    summary = invoices.aggregate(
        total_purchase=Coalesce(
            Sum('total_amount'),
            money_zero,
            output_field=money_field
        ),
        total_paid=Coalesce(
            Sum('paid_amount'),
            money_zero,
            output_field=money_field
        ),
        total_debt=Coalesce(
            Sum(
                ExpressionWrapper(
                    F('total_amount') - F('paid_amount'),
                    output_field=money_field
                )
            ),
            money_zero,
            output_field=money_field
        )
    )

    return render(request, 'customer_debt_detail.html', {
        'customer': customer,
        'invoices': invoices,
        'total_purchase': summary['total_purchase'],
        'total_paid': summary['total_paid'],
        'total_debt': summary['total_debt'],
    })
@admin_required
def sales_statistics(request):
    today = timezone.localdate()
    current_year = today.year

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    month = request.GET.get('month', '').strip()
    year = request.GET.get('year', '').strip()

    def parse_html_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    parsed_date_from = parse_html_date(date_from)
    parsed_date_to = parse_html_date(date_to)

    try:
        month_int = int(month) if month else None
    except ValueError:
        month_int = None

    try:
        year_int = int(year) if year else None
    except ValueError:
        year_int = None

    def make_aware_start(date_obj):
        dt = datetime.combine(date_obj, time.min)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

    def make_aware_end(date_obj):
        dt = datetime.combine(date_obj, time.max)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

    def apply_invoice_filters(queryset):
        # Nếu có chọn khoảng ngày thì ưu tiên lọc theo ngày
        if parsed_date_from or parsed_date_to:
            if parsed_date_from:
                queryset = queryset.filter(created_at__gte=make_aware_start(parsed_date_from))
            if parsed_date_to:
                queryset = queryset.filter(created_at__lte=make_aware_end(parsed_date_to))
        else:
            # Chỉ dùng tháng/năm khi không lọc theo khoảng ngày
            if year_int:
                queryset = queryset.filter(created_at__year=year_int)
            if month_int:
                queryset = queryset.filter(created_at__month=month_int)

        return queryset

    confirmed_sales = SaleInvoice.objects.filter(status='confirmed').select_related('customer')
    confirmed_sales = apply_invoice_filters(confirmed_sales)

    sales = list(confirmed_sales)

    total_revenue = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_debt = Decimal('0.00')
    total_invoices = len(sales)

    revenue_by_day_map = {}
    revenue_by_month_map = {}
    top_customers_map = {}

    for sale in sales:
        final_amount = sale.final_amount or Decimal('0.00')
        paid_amount = sale.paid_amount or Decimal('0.00')
        debt_amount = final_amount - paid_amount

        total_revenue += final_amount
        total_paid += paid_amount
        total_debt += debt_amount

        created_local = timezone.localtime(sale.created_at) if timezone.is_aware(sale.created_at) else sale.created_at
        day_key = created_local.date()
        month_key = day_key.replace(day=1)

        if day_key not in revenue_by_day_map:
            revenue_by_day_map[day_key] = {
                'day': day_key,
                'invoice_count': 0,
                'revenue': Decimal('0.00'),
            }
        revenue_by_day_map[day_key]['invoice_count'] += 1
        revenue_by_day_map[day_key]['revenue'] += final_amount

        if month_key not in revenue_by_month_map:
            revenue_by_month_map[month_key] = {
                'month_value': month_key,
                'invoice_count': 0,
                'revenue': Decimal('0.00'),
            }
        revenue_by_month_map[month_key]['invoice_count'] += 1
        revenue_by_month_map[month_key]['revenue'] += final_amount

        if sale.customer_id:
            customer_key = sale.customer_id
            if customer_key not in top_customers_map:
                top_customers_map[customer_key] = {
                    'customer_id': sale.customer_id,
                    'customer__name': sale.customer.name if sale.customer else 'Khách hàng đã xóa',
                    'customer__phone': sale.customer.phone if sale.customer else '',
                    'invoice_count': 0,
                    'total_purchase': Decimal('0.00'),
                    'total_paid': Decimal('0.00'),
                    'total_debt': Decimal('0.00'),
                }

            top_customers_map[customer_key]['invoice_count'] += 1
            top_customers_map[customer_key]['total_purchase'] += final_amount
            top_customers_map[customer_key]['total_paid'] += paid_amount
            top_customers_map[customer_key]['total_debt'] += debt_amount

    revenue_by_day = sorted(
        revenue_by_day_map.values(),
        key=lambda x: x['day'],
        reverse=True
    )[:15]

    revenue_by_month = sorted(
        revenue_by_month_map.values(),
        key=lambda x: x['month_value'],
        reverse=True
    )

    top_customers = sorted(
        top_customers_map.values(),
        key=lambda x: x['total_purchase'],
        reverse=True
    )[:10]

    detail_qs = SaleInvoiceDetail.objects.filter(invoice__status='confirmed').select_related(
        'product_variant__product',
        'product_variant__unit'
    )

    # Dùng cùng logic lọc cho chi tiết hóa đơn
    if parsed_date_from or parsed_date_to:
        if parsed_date_from:
            detail_qs = detail_qs.filter(invoice__created_at__gte=make_aware_start(parsed_date_from))
        if parsed_date_to:
            detail_qs = detail_qs.filter(invoice__created_at__lte=make_aware_end(parsed_date_to))
    else:
        if year_int:
            detail_qs = detail_qs.filter(invoice__created_at__year=year_int)
        if month_int:
            detail_qs = detail_qs.filter(invoice__created_at__month=month_int)

    product_map = {}
    for detail in detail_qs:
        key = detail.product_variant_id
        if key not in product_map:
            product_map[key] = {
                'product_name': detail.product_variant.product.name,
                'unit_name': detail.product_variant.unit.name,
                'total_sold': 0,
                'total_revenue': Decimal('0.00'),
            }

        product_map[key]['total_sold'] += detail.quantity
        product_map[key]['total_revenue'] += detail.subtotal or Decimal('0.00')

    top_selling_products = sorted(
        product_map.values(),
        key=lambda x: (x['total_sold'], x['total_revenue']),
        reverse=True,
    )[:10]

    display_year = year_int if year_int else current_year
    years = range(current_year - 5, current_year + 1)

    return render(request, 'sales_statistics.html', {
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'total_invoices': total_invoices,
        'revenue_by_day': revenue_by_day,
        'revenue_by_month': revenue_by_month,
        'top_selling_products': top_selling_products,
        'top_customers': top_customers,
        'current_year': display_year,
        'date_from': date_from,
        'date_to': date_to,
        'month': month,
        'year': year,
        'years': years,
    })
def _get_pos_cart(request):
    return request.session.get('pos_cart', {})


def _save_pos_cart(request, cart):
    request.session['pos_cart'] = cart
    request.session.modified = True


def _build_pos_cart(request):
    cart = _get_pos_cart(request)
    variant_ids = [int(k) for k in cart.keys() if str(k).isdigit()]

    variants = ProductVariant.objects.select_related(
        'product', 'unit'
    ).filter(
        id__in=variant_ids,
        product__is_active=True,
        is_active=True
    )

    variant_map = {str(v.id): v for v in variants}

    items = []
    total_qty = 0
    total_amount = Decimal('0')

    cleaned_cart = {}

    for variant_id, qty in cart.items():
        variant = variant_map.get(str(variant_id))
        if not variant:
            continue

        try:
            qty = int(qty)
        except (TypeError, ValueError):
            continue

        if qty <= 0:
            continue

        subtotal = variant.selling_price * qty

        items.append({
            'variant': variant,
            'variant_id': variant.id,
            'name': variant.product.name,
            'unit': variant.unit.name if variant.unit else '',
            'price': variant.selling_price,
            'stock': variant.stock,
            'quantity': qty,
            'subtotal': subtotal,
            'is_over_stock': qty > variant.stock,
        })

        cleaned_cart[str(variant.id)] = qty
        total_qty += qty
        total_amount += subtotal

    if cleaned_cart != cart:
        _save_pos_cart(request, cleaned_cart)

    return items, total_qty, total_amount


@login_required
def pos_view(request):
    q = request.GET.get('q', '').strip()

    products = ProductVariant.objects.select_related(
        'product', 'product__category', 'unit'
    ).filter(
        product__is_active=True,
        is_active=True
    )

    if q:
        products = products.filter(
            Q(product__name__icontains=q) |
            Q(product__brand__icontains=q) |
            Q(product__category__name__icontains=q)
        )

    products = products.order_by('product__name')[:50]

    customers = Customer.objects.filter(is_active=True).order_by('name')
    cart_items, total_qty, total_amount = _build_pos_cart(request)
    selected_customer_id = request.GET.get('new_customer_id', '').strip()

    return render(request, 'pos.html', {
        'products': products,
        'customers': customers,
        'cart_items': cart_items,
        'total_qty': total_qty,
        'total_amount': total_amount,
        'q': q,
        'selected_customer_id': selected_customer_id,
    })


@login_required
def pos_add_to_cart(request):
    if request.method != 'POST':
        return redirect('pos')

    variant_id = request.POST.get('variant_id')
    quantity_raw = request.POST.get('quantity', '1')
    next_q = request.POST.get('q', '').strip()

    try:
        quantity = int(quantity_raw)
    except ValueError:
        messages.error(request, "Số lượng không hợp lệ.")
        return redirect(f"{reverse('pos')}?q={next_q}" if next_q else reverse('pos'))

    if quantity <= 0:
        messages.error(request, "Số lượng phải lớn hơn 0.")
        return redirect(f"{reverse('pos')}?q={next_q}" if next_q else reverse('pos'))

    variant = get_object_or_404(
        ProductVariant.objects.select_related('product', 'unit'),
        pk=variant_id,
        product__is_active=True,
        is_active=True
    )

    cart = _get_pos_cart(request)
    current_qty = int(cart.get(str(variant.id), 0))
    new_qty = current_qty + quantity

    if new_qty > variant.stock:
        messages.error(
            request,
            f"Sản phẩm '{variant.product.name}' không đủ tồn kho. "
            f"Tồn hiện tại: {variant.stock}."
        )
        return redirect(f"{reverse('pos')}?q={next_q}" if next_q else reverse('pos'))

    cart[str(variant.id)] = new_qty
    _save_pos_cart(request, cart)

    messages.success(request, f"Đã thêm '{variant.product.name}' vào giỏ hàng.")
    return redirect(f"{reverse('pos')}?q={next_q}" if next_q else reverse('pos'))


@login_required
def pos_update_cart(request, variant_id):
    if request.method != 'POST':
        return redirect('pos')

    quantity_raw = request.POST.get('quantity', '1')

    try:
        quantity = int(quantity_raw)
    except ValueError:
        messages.error(request, "Số lượng không hợp lệ.")
        return redirect('pos')

    cart = _get_pos_cart(request)
    variant = get_object_or_404(
        ProductVariant.objects.select_related('product'),
        pk=variant_id,
        product__is_active=True,
        is_active=True
    )

    if quantity <= 0:
        cart.pop(str(variant_id), None)
        _save_pos_cart(request, cart)
        messages.success(request, f"Đã xóa '{variant.product.name}' khỏi giỏ hàng.")
        return redirect('pos')

    if quantity > variant.stock:
        messages.error(
            request,
            f"Sản phẩm '{variant.product.name}' không đủ tồn kho. "
            f"Tồn hiện tại: {variant.stock}."
        )
        return redirect('pos')

    cart[str(variant_id)] = quantity
    _save_pos_cart(request, cart)
    messages.success(request, f"Đã cập nhật số lượng '{variant.product.name}'.")
    return redirect('pos')


@login_required
def pos_remove_from_cart(request, variant_id):
    cart = _get_pos_cart(request)
    cart.pop(str(variant_id), None)
    _save_pos_cart(request, cart)
    messages.success(request, "Đã xóa sản phẩm khỏi giỏ hàng.")
    return redirect('pos')


@login_required
def pos_clear_cart(request):
    _save_pos_cart(request, {})
    messages.success(request, "Đã xóa toàn bộ giỏ hàng.")
    return redirect('pos')


@login_required
@transaction.atomic
def pos_checkout(request):
    if request.method != 'POST':
        return redirect('pos')

    cart_items, total_qty, total_amount = _build_pos_cart(request)

    if not cart_items:
        messages.error(request, "Giỏ hàng đang trống.")
        return redirect('pos')

    customer_id = request.POST.get('customer')
    note = request.POST.get('note', '').strip()
    amount_paid_raw = request.POST.get('amount_paid', '0').strip()
    print_invoice = request.POST.get('print_invoice') == 'on'

    discount_type = request.POST.get('discount_type', 'none').strip()
    discount_value_raw = request.POST.get('discount_value', '0').strip()

    try:
        amount_paid = Decimal(amount_paid_raw or '0')
        discount_value = Decimal(discount_value_raw or '0')
    except InvalidOperation:
        messages.error(request, "Giá trị không hợp lệ.")
        return redirect('pos')

    if amount_paid < 0 or discount_value < 0:
        messages.error(request, "Giá trị không được âm.")
        return redirect('pos')

    # ===== TÍNH GIẢM GIÁ =====
    discount_amount = Decimal('0')

    if discount_type == 'percent':
        discount_amount = total_amount * discount_value / Decimal('100')
    elif discount_type == 'amount':
        discount_amount = discount_value

    if discount_amount > total_amount:
        discount_amount = total_amount

    final_amount = total_amount - discount_amount

    # ===== LẤY KHÁCH =====
    customer = None
    if customer_id:
        customer = Customer.objects.filter(
            pk=customer_id,
            is_active=True
        ).first()
        if not customer:
            messages.error(request, "Khách hàng không hợp lệ.")
            return redirect('pos')

    # ===== CHECK TỒN KHO =====
    for item in cart_items:
        if item['quantity'] > item['stock']:
            messages.error(
                request,
                f"Sản phẩm '{item['name']}' không đủ tồn kho."
            )
            return redirect('pos')

    # ===== VALIDATE THANH TOÁN =====
    if not customer and amount_paid < final_amount:
        messages.error(request, "Khách lẻ phải thanh toán đủ tiền.")
        return redirect('pos')

    if customer and amount_paid > final_amount:
        messages.error(request, "Số tiền trả trước không được vượt tổng hóa đơn.")
        return redirect('pos')

    try:
        # ===== TẠO HÓA ĐƠN =====
        invoice = SaleInvoice.objects.create(
            customer=customer,
            note=note,
            total_amount=Decimal('0'),
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=Decimal('0'),
            final_amount=Decimal('0'),
            paid_amount=Decimal('0'),
            payment_status='unpaid',
            status='draft',
            created_by=request.user
        )

        # ===== CHI TIẾT =====
        for item in cart_items:
            SaleInvoiceDetail.objects.create(
                invoice=invoice,
                product_variant=item['variant'],
                quantity=item['quantity'],
                price=item['price']
            )

        # ===== TÍNH LẠI =====
        invoice.recalc_total()

        # ===== XÁC NHẬN (trừ kho + auto paid nếu khách lẻ) =====
        invoice.confirm()

        # ===== THANH TOÁN =====
        if customer and amount_paid > 0:
            SalePayment.objects.create(
                invoice=invoice,
                amount=amount_paid,
                note='Thanh toán tại POS'
            )

        # ===== XÓA GIỎ =====
        _save_pos_cart(request, {})

        # ===== THÔNG BÁO =====
        if not customer:
            change_amount = amount_paid - invoice.final_amount
            messages.success(
                request,
                f"Thanh toán thành công. Tiền thối lại: {change_amount:.0f} VNĐ"
            )
        else:
            messages.success(request, "Thanh toán thành công.")

        if print_invoice:
            return redirect('sale_invoice_print', pk=invoice.id)

        return redirect('pos')

    except ValidationError as e:
        messages.error(request, e.messages[0] if hasattr(e, 'messages') else "Không thể thanh toán.")
        return redirect('pos')

@login_required
def pos_customer_create(request):
    if request.method != 'POST':
        return redirect('pos')

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()

    if not name:
        messages.error(request, "Tên khách hàng không được để trống.")
        return redirect('pos')

    customer = Customer.objects.create(
        name=name,
        phone=phone if phone else None,
        address=address if address else None,
        is_active=True
    )

    messages.success(request, f"Đã thêm khách hàng '{customer.name}' thành công.")
    return redirect(f"{reverse('pos')}?new_customer_id={customer.id}")

@admin_required
def account_list(request):
    accounts = User.objects.select_related('profile').all().order_by('-is_superuser', 'username')
    return render(request, 'account_list.html', {
        'accounts': accounts
    })


@admin_required
def account_create(request):
    if request.method != 'POST':
        return redirect('account_list')

    username = request.POST.get('username', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    password = request.POST.get('password', '').strip()
    role = request.POST.get('role', 'employee').strip()

    if not username or not password:
        messages.error(request, "Tên đăng nhập và mật khẩu không được để trống.")
        return redirect('account_list')

    if User.objects.filter(username=username).exists():
        messages.error(request, "Tên đăng nhập đã tồn tại.")
        return redirect('account_list')

    is_admin = (role == 'admin')

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_active=True,
        is_staff=is_admin,
        is_superuser=is_admin
    )

    UserProfile.objects.create(
        user=user,
        phone=phone if phone else None
    )

    if is_admin:
        messages.success(request, "Tạo tài khoản admin thành công.")
    else:
        messages.success(request, "Tạo tài khoản nhân viên thành công.")

    return redirect('account_list')

@admin_required
def account_toggle_active(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # Không cho tự khóa chính mình để tránh bị đá ra ngoài
    if user == request.user:
        messages.error(request, "Bạn không thể tự khóa tài khoản của chính mình.")
        return redirect('account_list')

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    if user.is_active:
        messages.success(request, f"Đã kích hoạt lại tài khoản '{user.username}'.")
    else:
        messages.success(request, f"Đã vô hiệu hóa tài khoản '{user.username}'.")

    return redirect('account_list')

@admin_required
def account_update(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method != 'POST':
        return redirect('account_list')

    username = request.POST.get('username', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    role = request.POST.get('role', 'employee').strip()

    if not username:
        messages.error(request, "Tên đăng nhập không được để trống.")
        return redirect('account_list')

    existing_user = User.objects.filter(username=username).exclude(pk=user.id).first()
    if existing_user:
        messages.error(request, "Tên đăng nhập đã tồn tại.")
        return redirect('account_list')

    is_admin = (role == 'admin')

    # Không cho tự hạ quyền chính mình từ admin thành nhân viên
    if user == request.user and not is_admin:
        messages.error(request, "Bạn không thể tự đổi quyền của chính mình thành nhân viên.")
        return redirect('account_list')

    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.is_staff = is_admin
    user.is_superuser = is_admin
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.phone = phone if phone else None
    profile.save()

    messages.success(request, f"Cập nhật tài khoản '{user.username}' thành công.")
    return redirect('account_list')

@admin_required
def account_reset_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method != 'POST':
        return redirect('account_list')

    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    if not new_password:
        messages.error(request, "Mật khẩu mới không được để trống.")
        return redirect('account_list')

    if len(new_password) < 6:
        messages.error(request, "Mật khẩu mới phải có ít nhất 6 ký tự.")
        return redirect('account_list')

    if new_password != confirm_password:
        messages.error(request, "Xác nhận mật khẩu không khớp.")
        return redirect('account_list')

    user.set_password(new_password)
    user.save(update_fields=['password'])

    messages.success(request, f"Đã đổi mật khẩu cho tài khoản '{user.username}'.")
    return redirect('account_list')