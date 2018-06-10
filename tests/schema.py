from django.db.models import Prefetch
import graphene
from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from .models import (
    DetailedItem,
    ExtraDetailedItem,
    Item,
    RelatedItem,
)


class ItemInterface(graphene.Interface):
    id = graphene.ID()
    parent_id = graphene.ID()
    foo = graphene.String()
    title = graphene.String()
    unoptimized_title = graphene.String()
    item_type = graphene.String()
    father = graphene.Field('tests.schema.ItemType')
    all_children = graphene.List('tests.schema.ItemType')
    children_names = graphene.String()
    aux_children_names = graphene.String()
    filtered_children = graphene.List(
        'tests.schema.ItemType',
        name=graphene.String(required=True),
    )

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


class ItemType(DjangoObjectType):
    title = gql_optimizer.field(
        graphene.String(),
        only='name',
    )
    father = gql_optimizer.field(
        graphene.Field('tests.schema.ItemType'),
        model_field='parent',
    )

    class Meta:
        model = Item
        interfaces = (ItemInterface, )


class DetailedItemType(ItemType):
    class Meta:
        model = DetailedItem
        interfaces = (ItemInterface, )


class RelatedItemType(ItemType):
    class Meta:
        model = RelatedItem
        interfaces = (ItemInterface, )


class ExtraDetailedItemType(DetailedItemType):
    class Meta:
        model = ExtraDetailedItem
        interfaces = (ItemInterface, )


class Query(graphene.ObjectType):
    items = graphene.List(ItemInterface, name=graphene.String(required=True))

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)


schema = graphene.Schema(query=Query)
