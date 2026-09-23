from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
# Create your models here.
class Employee1(models.Model):
    empno=models.IntegerField()
    empname=models.CharField(max_length=20)

class Category(models.Model):
    name=models.CharField(max_length=120,unique=True)
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity=models.IntegerField(default=1,null=True)
    short_description = models.CharField(max_length=160)
    image = models.ImageField(upload_to="products/images", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    offer_percent = models.PositiveIntegerField(default=0)

    @property
    def offer_price(self):
        if self.offer_percent:
            discount = self.price * (Decimal(100 - self.offer_percent) / Decimal(100))
            return discount.quantize(Decimal("0.01"))
        return self.price

    @property
    def has_offer(self):
        return self.offer_percent > 0

    def __str__(self):
        return self.name

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")

    def subtotal(self):
        return self.product.offer_price * self.quantity


class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    purchased_at = models.DateTimeField(auto_now_add=True)

    @property
    def was_on_offer(self):
        return self.unit_price < self.original_price