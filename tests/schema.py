from django.db.models import Prefetch
import graphene
from graphene_django.fields import DjangoConnectionField
from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from .models import (
    DetailedItem,
    ExtraDetailedItem,
    Item,
    RelatedItem,
    UnrelatedModel,
    SomeOtherItem,
    OtherItem,
)


class ItemInterface(graphene.Interface):
    id = graphene.ID(required=True)
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


class BaseItemType(DjangoObjectType):
    title = gql_optimizer.field(
        graphene.String(),
        only='name',
    )
    father = gql_optimizer.field(
        graphene.Field('tests.schema.ItemType'),
        model_field='parent',
    )
    relay_all_children = DjangoConnectionField('tests.schema.ItemNode')

    class Meta:
        model = Item

    @gql_optimizer.resolver_hints(
        model_field='children',
    )
    def resolve_relay_all_children(root, info, **kwargs):
        return root.children.all()


class ItemNode(BaseItemType):
    class Meta:
        model = Item
        interfaces = (graphene.relay.Node, ItemInterface, )


class SomeOtherItemType(DjangoObjectType):
    class Meta:
        model = SomeOtherItem


class OtherItemType(DjangoObjectType):
    class Meta:
        model = OtherItem


class ItemType(BaseItemType):
    class Meta:
        model = Item
        interfaces = (ItemInterface, )


class DetailedInterface(graphene.Interface):
    detail = graphene.String()


class DetailedItemType(ItemType):
    class Meta:
        model = DetailedItem
        interfaces = (ItemInterface, DetailedInterface)


class RelatedItemType(ItemType):
    class Meta:
        model = RelatedItem
        interfaces = (ItemInterface, )


class ExtraDetailedItemType(DetailedItemType):
    class Meta:
        model = ExtraDetailedItem
        interfaces = (ItemInterface, )


class UnrelatedModelType(DjangoObjectType):
    class Meta:
        model = UnrelatedModel
        interfaces = (DetailedInterface, )


class Query(graphene.ObjectType):
    items = graphene.List(ItemInterface, name=graphene.String(required=True))
    relay_items = DjangoConnectionField(ItemNode)
    other_items = graphene.List(OtherItemType)

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)

    def resolve_relay_items(root, info, **kwargs):
        return gql_optimizer.query(Item.objects.all(), info)

    def resolve_other_items(root, info):
        return gql_optimizer.query(OtherItemType.objects.all(), info)


schema = graphene.Schema(query=Query, types=(UnrelatedModelType, ))
