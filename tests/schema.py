from django.db.models import Prefetch
import graphene
from graphene import ConnectionField, relay
from graphene_django.fields import DjangoConnectionField
import graphene_django_optimizer as gql_optimizer
from graphene_django_optimizer import OptimizedDjangoObjectType

from .models import (
    DetailedItem,
    ExtraDetailedItem,
    Item,
    RelatedItem,
    UnrelatedModel,
    SomeOtherItem,
    OtherItem,
    RelatedOneToManyItem,
)


def _prefetch_children(info, filter_input):
    if filter_input is None:
        filter_input = {}

    gte = filter_input.get('value', {}).get('gte', 0)
    return Prefetch(
        'children',
        queryset=gql_optimizer.query(Item.objects.filter(value__gte=int(gte)), info),
        to_attr='gql_custom_filtered_children',
    )


class RangeInput(graphene.InputObjectType):
    gte = graphene.Field(graphene.Int)


class ItemFilterInput(graphene.InputObjectType):
    value = graphene.Field(RangeInput)


class ItemInterface(graphene.Interface):
    id = relay.GlobalID()
    parent_id = relay.GlobalID()
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
    children_custom_filtered = gql_optimizer.field(
        ConnectionField('tests.schema.ItemConnection', filter_input=ItemFilterInput()),
        prefetch_related=_prefetch_children,
    )

    def resolve_foo(root, info):
        return 'bar'

    @gql_optimizer.resolver_hints(
        model_field=lambda: 'children',
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

    def resolve_children_custom_filtered(root, info, *_args):
        return getattr(root, 'gql_custom_filtered_children')


class BaseItemType(OptimizedDjangoObjectType):
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


class SomeOtherItemType(OptimizedDjangoObjectType):
    class Meta:
        model = SomeOtherItem


class OtherItemType(OptimizedDjangoObjectType):
    class Meta:
        model = OtherItem


class ItemType(BaseItemType):
    class Meta:
        model = Item
        interfaces = (ItemInterface, )


class ItemConnection(graphene.relay.Connection):
    class Meta:
        node = ItemType


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


class RelatedOneToManyItemType(OptimizedDjangoObjectType):
    class Meta:
        model = RelatedOneToManyItem


class UnrelatedModelType(OptimizedDjangoObjectType):
    class Meta:
        model = UnrelatedModel
        interfaces = (DetailedInterface, )


class DummyItemMutation(graphene.Mutation):
    item = graphene.Field(
        ItemNode, description='The retrieved item.', required=False)

    class Arguments:
        item_id = graphene.ID(description='The ID of the item.')

    class Meta:
        description = 'A dummy mutation that retrieves a given item node.'

    @staticmethod
    def mutate(info, item_id):
        return graphene.Node.get_node_from_global_id(
            info, item_id, only_type=ItemNode)


class Query(graphene.ObjectType):
    items = graphene.List(ItemInterface, name=graphene.String(required=True))
    relay_items = DjangoConnectionField(ItemNode)
    other_items = graphene.List(OtherItemType)
    some_other_items = graphene.List(SomeOtherItemType)

    def resolve_items(root, info, name):
        return gql_optimizer.query(Item.objects.filter(name=name), info)

    def resolve_relay_items(root, info, **kwargs):
        return gql_optimizer.query(Item.objects.all(), info)

    def resolve_other_items(root, info):
        return gql_optimizer.query(OtherItemType.objects.all(), info)


schema = graphene.Schema(
    query=Query, types=(UnrelatedModelType, ), mutation=DummyItemMutation)
