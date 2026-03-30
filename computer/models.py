from django.db import models, transaction
from django.db.models import Sum, F
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return f"Hồ sơ - {self.user.username}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    class Meta:
        db_table = 'category'   

class Product(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name
    class Meta:
        db_table = 'product'

class Unit(models.Model):
    name = models.CharField(max_length=20)
    def __str__(self):
        return self.name
    class Meta:
        db_table = 'unit'        

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    selling_price = models.DecimalField(default=0,max_digits=10, decimal_places=0)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT
    )
    def __str__(self):
        return f"{self.product.name} - {self.unit.name}"
    class Meta:
        db_table = 'productvariant'

class Supplier(models.Model):
    name= models.CharField(max_length=100)
    phone= models.CharField(max_length=20)
    address= models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name
    class Meta:
        db_table = 'supplier'

class ImportReceipt(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='receipts')
    created_at = models.DateTimeField(auto_now_add=True)

    total_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    paid_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='import_receipts'
)
    PAYMEN_STATUS = (
        ('unpaid','Chưa thanh toán'),
        ('partial','Thanh toán một phần'),
        ('paid','Đã thanh toán')
    )
    payment_status = models.CharField(max_length=20, choices=PAYMEN_STATUS, default='unpaid')

    STATUS = (
        ('draft','Nháp'),
        ('confirmed','Đã xác nhận'),
    )
    status = models.CharField(max_length=20, choices=STATUS, default='draft')

    def __str__(self):
        return f"PN {self.id}"

    class Meta:
        db_table = 'import_receipt'

    def recalc_total(self):
        total = self.details.aggregate(s=Sum('subtotal'))['s'] or Decimal(0)
        self.total_amount = total
        self.save(update_fields=['total_amount'])

    def confirm(self):
        """Xác nhận phiếu nhập — chỉ chạy 1 lần, cập nhật stock, tính lại total trong transaction."""
        if self.status == 'confirmed':
            return
        with transaction.atomic():
            # khóa các detail để an toàn
            details = self.details.select_related('product_variant')
            # cập nhật stock với F expression
            for d in details:
                ProductVariant.objects.filter(pk=d.product_variant.pk).update(
                    stock=F('stock') + d.quantity
                )
            # tính lại tổng
            self.recalc_total()
            self.status = 'confirmed'
            self.save(update_fields=['status'])
    @property
    def debt(self):
        return self.total_amount - self.paid_amount
class ImportReceiptDetail(models.Model):
    receipt = models.ForeignKey(ImportReceipt, on_delete=models.CASCADE, related_name='details')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=15, decimal_places=0, default=0)

    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"

    class Meta:
        db_table = 'import_receipt_detail'
        unique_together = ['receipt', 'product_variant']

    def save(self, *args, **kwargs):
        if self.receipt.status == 'confirmed':
            raise ValidationError("Không thể sửa chi tiết của phiếu đã xác nhận")
        # tự tính subtotal trước khi lưu
        self.subtotal = (Decimal(self.price) * Decimal(self.quantity)) if self.price is not None else Decimal(0)
        super().save(*args, **kwargs)
        # nếu cần, cập nhật tổng của receipt (không bắt buộc—tùy luồng)
        self.receipt.recalc_total()

class Payment(models.Model):
    receipt = models.ForeignKey(
        'ImportReceipt',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'payment'
        ordering = ['-date']

    def clean(self):
        if not self.receipt_id:
            raise ValidationError("Phiếu nhập không hợp lệ.")

        if self.receipt.status != 'confirmed':
            raise ValidationError("Chỉ thanh toán khi phiếu đã xác nhận.")

        if self.amount is None or self.amount <= 0:
            raise ValidationError("Số tiền thanh toán phải lớn hơn 0.")

        # Tính số tiền đã thanh toán trước đó
        total_paid_before = self.receipt.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # Nếu là update bản ghi cũ thì trừ số tiền cũ ra để tránh cộng trùng
        if self.pk:
            old_payment = Payment.objects.filter(pk=self.pk).first()
            if old_payment:
                total_paid_before -= old_payment.amount

        remaining = self.receipt.total_amount - total_paid_before

        if self.amount > remaining:
            raise ValidationError(f"Số tiền thanh toán vượt quá số còn nợ ({remaining}).")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        total_paid = self.receipt.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        self.receipt.paid_amount = total_paid

        if total_paid <= 0:
            self.receipt.payment_status = 'unpaid'
        elif total_paid < self.receipt.total_amount:
            self.receipt.payment_status = 'partial'
        else:
            self.receipt.payment_status = 'paid'

        self.receipt.save(update_fields=['paid_amount', 'payment_status'])

    def __str__(self):
        return f"Thanh toán {self.amount} cho phiếu nhập {self.receipt.id}"


@property
def is_paid(self):
    return self.paid_amount >= self.total_amount

@property
def remaining(self):
    return max(self.total_amount - self.paid_amount, 0)

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'customer'
        ordering = ['name']

    def __str__(self):
        return self.name

class SaleInvoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Chưa thanh toán'),
        ('partial', 'Thanh toán một phần'),
        ('paid', 'Đã thanh toán'),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ('none', 'Không giảm'),
        ('percent', 'Giảm theo %'),
        ('amount', 'Giảm theo tiền'),
    ]

    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='none')
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0) # số tiền giảm thực tế
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)    # tổng sau giảm

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    note = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='sale_invoices'
)
    class Meta:
        db_table = 'sale_invoice'
        ordering = ['-id']

    def recalc_total(self):
        total = self.details.aggregate(total=models.Sum('subtotal'))['total'] or Decimal('0')
        self.total_amount = total

        discount_amount = Decimal('0')

        if self.discount_type == 'percent':
            discount_amount = total * (self.discount_value / Decimal('100'))
        elif self.discount_type == 'amount':
            discount_amount = self.discount_value

        # không cho giảm vượt tổng tiền
        if discount_amount > total:
            discount_amount = total

        self.discount_amount = discount_amount
        self.final_amount = total - discount_amount

        self.save(update_fields=['total_amount', 'discount_amount', 'final_amount'])

    @property
    def debt(self):
        return self.final_amount - self.paid_amount

    def confirm(self):
        if self.status != 'draft':
            raise ValidationError("Hóa đơn này đã được xác nhận trước đó.")

        details = self.details.select_related('product_variant', 'product_variant__product').all()

        if not details.exists():
            raise ValidationError("Hóa đơn bán phải có ít nhất 1 sản phẩm.")

        # kiểm tra tồn kho trước
        for detail in details:
            if detail.product_variant.stock < detail.quantity:
                raise ValidationError(
                    f"Sản phẩm '{detail.product_variant.product.name}' không đủ tồn kho. "
                    f"Tồn hiện tại: {detail.product_variant.stock}, số lượng bán: {detail.quantity}."
                )

        # trừ kho
        for detail in details:
            variant = detail.product_variant
            variant.stock -= detail.quantity
            variant.save(update_fields=['stock'])

        self.status = 'confirmed'

        # Không chọn khách hàng => khách lẻ => tự động thanh toán đủ
        if not self.customer_id:
            self.paid_amount = self.final_amount
            self.payment_status = 'paid'
        else:
            # Có khách hàng => có thể nợ
            if self.paid_amount <= 0:
                self.paid_amount = Decimal('0')
                self.payment_status = 'unpaid'
            elif self.paid_amount < self.final_amount:
                self.payment_status = 'partial'
            else:
                self.payment_status = 'paid'

        self.save(update_fields=['status', 'paid_amount', 'payment_status'])

    def __str__(self):
        return f"Hóa đơn bán #{self.id}"
class SaleInvoiceDetail(models.Model):
    invoice = models.ForeignKey(
        SaleInvoice,
        on_delete=models.CASCADE,
        related_name='details'
    )
    product_variant = models.ForeignKey('ProductVariant', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'sale_invoice_detail'
        ordering = ['id']

    def clean(self):
        if not self.product_variant_id:
            raise ValidationError("Sản phẩm không hợp lệ.")

        if self.quantity is None or self.quantity <= 0:
            raise ValidationError("Số lượng bán phải lớn hơn 0.")

        if self.price is None or self.price <= 0:
            raise ValidationError("Đơn giá bán phải lớn hơn 0.")

        if self.product_variant.stock < self.quantity:
            raise ValidationError(
                f"Sản phẩm '{self.product_variant.product.name}' không đủ tồn kho. "
                f"Tồn hiện tại: {self.product_variant.stock}, số lượng bán: {self.quantity}."
            )

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(self.quantity) * self.price
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hóa đơn #{self.invoice.id} - {self.product_variant.product.name}"     
    
class SalePayment(models.Model):
    invoice = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'sale_payment'
        ordering = ['-date']

    def clean(self):
        if self.invoice.status != 'confirmed':
            raise ValidationError("Chỉ thanh toán khi hóa đơn đã xác nhận.")

        # Không có khách hàng => khách lẻ => không lưu công nợ
        if not self.invoice.customer_id:
            raise ValidationError("Hóa đơn khách lẻ không cần thanh toán công nợ.")

        if self.amount is None or self.amount <= 0:
            raise ValidationError("Số tiền thanh toán phải lớn hơn 0.")

        remaining = self.invoice.final_amount - self.invoice.paid_amount
        if self.amount > remaining:
            raise ValidationError("Số tiền thanh toán vượt quá số còn nợ.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        total_paid = self.invoice.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        self.invoice.paid_amount = total_paid

        if total_paid <= 0:
            self.invoice.payment_status = 'unpaid'
        elif total_paid < self.invoice.final_amount:
            self.invoice.payment_status = 'partial'
        else:
            self.invoice.payment_status = 'paid'

        self.invoice.save(update_fields=['paid_amount', 'payment_status'])

    def __str__(self):
        return f"Thanh toán {self.amount} cho hóa đơn {self.invoice.id}"