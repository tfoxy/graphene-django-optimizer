from graphene.types.definitions import GrapheneObjectType
from graphene_django.types import DjangoObjectType
from graphql import ResolveInfo

from .query import query


class OptimizedDjangoObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def can_optimize_resolver(cls, resolver_info: ResolveInfo):
        return (
            isinstance(resolver_info.return_type, GrapheneObjectType) and
            resolver_info.return_type.graphene_type is cls)

    @classmethod
    def get_optimized_node(cls, info, qs, pk):
        try:
            return query(qs, info).get(pk=pk)
        except cls._meta.model.DoesNotExist:
            return None

    @classmethod
    def get_node(cls, info: ResolveInfo, id):
        if cls.can_optimize_resolver(info):
            return cls.get_optimized_node(info, cls._meta.model.objects, id)
        return super(OptimizedDjangoObjectType, cls).get_node(info, id)
