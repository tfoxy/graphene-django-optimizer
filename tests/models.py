from django.contrib.auth.models import User
from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey('Item', on_delete=models.SET_NULL, null=True, related_name='children')
    item = models.ForeignKey('Item', on_delete=models.SET_NULL, null=True)
    value = models.IntegerField(default=10)
    user = models.ForeignKey(User, related_name="items", on_delete=models.PROTECT, null=True)

    item_type = 'simple'

    @property
    def title(self):
        return self.name

    @property
    def unoptimized_title(self):
        return self.title

    def all_children(self):
        return self.children.all()


class DetailedItem(Item):
    detail = models.TextField(null=True)
    item_type = models.CharField(max_length=100, null=True)


class RelatedItem(Item):
    related_items = models.ManyToManyField(Item)


class RelatedOneToManyItem(models.Model):
    name = models.CharField(max_length=100, blank=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='otm_items')


class ExtraDetailedItem(DetailedItem):
    extra_detail = models.TextField()


class UnrelatedModel(models.Model):
    detail = models.TextField(null=True)


class SomeOtherItem(models.Model):
    name = models.CharField(max_length=100, blank=True)


class OtherItem(models.Model):
    name = models.CharField(max_length=100, blank=True)
    some_other_item = models.ForeignKey('SomeOtherItem', on_delete=models.PROTECT, null=False)
