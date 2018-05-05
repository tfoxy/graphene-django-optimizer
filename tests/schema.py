import graphene

from django.db.models import Prefetch
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
    aux_children_names = graphene.String()
    filtered_children = graphene.List(
        'tests.schema.ItemType',
        name=graphene.String(required=True),
    )

    class Meta:
        model = Item

    def resolve_foo(root, info):
        return 'bar'

    @gql_optimizer.resolver_hints(
        model_field='children',
    )
    def resolve_children_names(root, info):
        return ' '.join(item.name for item in root.children.all())

    @gql_optimizer.resolver_hints(
        prefetch_related='children',
    )
    def resolve_aux_children_names(root, info):
        return ' '.join(item.name for item in root.children.all())

    @gql_optimizer.resolver_hints(
        prefetch_related=lambda info, name: Prefetch(
            'children',
            queryset=gql_optimizer.query(Item.objects.filter(name=name), info),
            to_attr='gql_filtered_children_' + name,
        ),
    )
    def resolve_filtered_children(root, info, name):
        return getattr(root, 'gql_filtered_children_' + name)


class Query(graphene.ObjectType):
    items = graphene.List(ItemType, name=graphene.String(required=True))

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)


schema = graphene.Schema(query=Query)
