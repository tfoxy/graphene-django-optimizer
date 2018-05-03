import graphene

from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from .models import (
    Item,
)


class ItemType(DjangoObjectType):
    parent_id = graphene.ID()
    foo = graphene.String()
    title = graphene.String()
    unoptimized_title = graphene.String()
    father = gql_optimizer.field(
        graphene.Field('tests.schema.ItemType'),
        model_field='parent',
    )
    all_children = graphene.List('tests.schema.ItemType')
    children_names = graphene.String()

    class Meta:
        model = Item

    def resolve_foo(root, info):
        return 'bar'

    @gql_optimizer.resolver_hints(
        model_field='children',
    )
    def resolve_children_names(root, info):
        return ' '.join(item.name for item in root.children.all())


class Query(graphene.ObjectType):
    items = graphene.List(ItemType, name=graphene.String(required=True))

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)


schema = graphene.Schema(query=Query)
