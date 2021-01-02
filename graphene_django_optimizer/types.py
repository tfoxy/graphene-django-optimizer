from graphene.types.definitions import GrapheneObjectType
from graphene_django.types import DjangoObjectType

from .query import query


class OptimizedDjangoObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def can_optimize_resolver(cls, resolver_info):
        return (
            isinstance(resolver_info.return_type, GrapheneObjectType)
            and resolver_info.return_type.graphene_type is cls)

    @classmethod
    def get_queryset(cls, queryset, info):
        queryset = super(OptimizedDjangoObjectType, cls).get_queryset(queryset, info)
        if cls.can_optimize_resolver(info):
            queryset = query(queryset, info)
        return queryset
