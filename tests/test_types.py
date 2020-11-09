import pytest
from django.contrib.auth.models import User
from graphene import Node
from graphql_relay import to_global_id
from mock import patch

from .graphql_utils import create_resolve_info
from .models import SomeOtherItem, Item
from .schema import schema, SomeOtherItemType, DummyItemMutation


@pytest.mark.django_db
@patch('graphene_django_optimizer.types.query',
       return_value=SomeOtherItem.objects)
def test_should_optimize_the_single_node(mocked_optimizer):
    SomeOtherItem.objects.create(pk=7, name='Hello')

    info = create_resolve_info(schema, '''
        query ItemDetails {
            someOtherItems(id: $id) {
                id
                foo
                parent {
                    id
                }
            }
        }
    ''')

    info.return_type = schema.get_type('SomeOtherItemType')
    result = SomeOtherItemType.get_node(info, 7)

    assert result, 'Expected the item to be found and returned'
    assert result.pk == 7, 'The item is not the correct one'

    mocked_optimizer.assert_called_once_with(SomeOtherItem.objects, info)


@pytest.mark.django_db
@patch('graphene_django_optimizer.types.query')
def test_should_return_none_when_node_is_not_resolved(mocked_optimizer):
    SomeOtherItem.objects.create(id=7)

    info = create_resolve_info(schema, '''
        query {
            someOtherItems(id: $id) {
                id
                foo
                children {
                    id
                    foo
                }
            }
        }
    ''')

    info.return_type = schema.get_type('SomeOtherItemType')
    qs = SomeOtherItem.objects
    mocked_optimizer.return_value = qs

    assert SomeOtherItemType.get_node(info, 8) is None
    mocked_optimizer.assert_called_once_with(SomeOtherItem.objects, info)


@pytest.mark.django_db
@patch('graphene_django_optimizer.types.query')
def test_mutating_should_not_optimize(mocked_optimizer):
    Item.objects.create(id=7)

    info = create_resolve_info(schema, '''
        query {
            items(id: $id) {
                id
                foo
                children {
                    id
                    foo
                }
            }
        }
    ''')

    info.return_type = schema.get_type('SomeOtherItemType')
    result = DummyItemMutation.mutate(info, to_global_id('ItemNode', 7))
    assert result
    assert result.pk == 7
    assert mocked_optimizer.call_count == 0


@pytest.mark.django_db
def test_get_node_from_global_id_queryset():
    item_1 = Item.objects.create()
    item_2 = Item.objects.create()

    user = User.objects.create()
    item_3 = Item.objects.create(user=user)
    item_4 = Item.objects.create(user=user)

    info = create_resolve_info(
        schema,
        '''
        query {
            items(id: $id) {
                id
                foo
                children {
                    id
                    foo
                }
            }
        }
        ''',
        user=user,
    )

    assert not Node.get_node_from_global_id(info, to_global_id("ItemNode", item_1.id))
    assert not Node.get_node_from_global_id(info, to_global_id("ItemNode", item_2.id))

    assert Node.get_node_from_global_id(info, to_global_id("ItemNode", item_3.id)) == item_3
    assert Node.get_node_from_global_id(info, to_global_id("ItemNode", item_4.id)) == item_4
