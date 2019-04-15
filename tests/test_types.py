import pytest
from mock import patch

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema, ItemType


@pytest.mark.django_db
@patch('graphene_django_optimizer.types.query', return_value=Item.objects)
def test_should_optimize_the_single_node(mocked_optimizer):
    Item.objects.create(id=7)

    info = create_resolve_info(schema, '''
        query ItemDetails {
            items(id: $id) {
                id
                foo
                parent {
                    id
                }
            }
        }
    ''')

    result = ItemType.get_node(info, 7)

    assert result, 'Expected the item to be found and returned'
    assert result.pk == 7, 'The item is not the correct one'

    mocked_optimizer.assert_called_once_with(Item.objects, info)


@pytest.mark.django_db
@patch('graphene_django_optimizer.types.query')
def test_should_return_none_when_node_is_not_resolved(mocked_optimizer):
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

    qs = Item.objects.filter(name='foo')
    mocked_optimizer.return_value = qs

    assert ItemType.get_optimized_node(info, qs, 7) is None
    mocked_optimizer.assert_called_once_with(qs, info)
