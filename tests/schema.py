import graphene

from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from .models import (
    Item,
)


class ItemType(DjangoObjectType):
    foo = graphene.String()

    class Meta:
        model = Item

    def resolve_foo(root, info):
        return 'bar'


class Query(graphene.ObjectType):
    items = graphene.List(ItemType, name=graphene.String())

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)


schema = graphene.Schema(query=Query)
