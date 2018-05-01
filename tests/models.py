from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        related_name='ingredients',
    )

    def __str__(self):
        return self.name


class User(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    buyer = models.ForeignKey(User, null=True)

    def get_total_price(self):
        return sum(item.price for item in self.purchaseorderitem_set.all())


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder)
    price = models.DecimalField()
