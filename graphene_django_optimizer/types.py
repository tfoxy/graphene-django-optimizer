from graphene_django.types import DjangoObjectType
from .query import query


class OptimizedDjangoObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def get_optimized_node(cls, info, qs, pk):
        try:
            return query(qs, info).get(pk=pk)
        except cls._meta.model.DoesNotExist:
            return None

    @classmethod
    def get_node(cls, info, id):
        return cls.get_optimized_node(info, cls._meta.model.objects, id)
