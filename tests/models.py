from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey('Item', null=True, related_name='children')
    item = models.ForeignKey('Item', null=True)

    @property
    def title(self):
        return self.name

    @property
    def unoptimized_title(self):
        return self.unoptimized_title

    def all_children(self):
        return self.children.all()
