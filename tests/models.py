from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey('Item', null=True, related_name='children')
    item = models.ForeignKey('Item', null=True)
