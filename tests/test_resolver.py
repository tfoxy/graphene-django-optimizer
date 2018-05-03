import pytest

import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema
from .test_utils import assert_query_equality


@pytest.mark.django_db
def test_should_optimize_non_django_field_if_it_has_an_optimization_hint_in_the_resolver():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                childrenNames
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)
