import pytest

import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema
from .test_utils import assert_query_equality


@pytest.mark.django_db
def test_should_return_valid_result_in_a_relay_query():
    Item.objects.create(id=7, name='foo')
    result = schema.execute('''
        query {
            relayItems {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['relayItems']['edges'][0]['node']['id'] == '7'
    assert result.data['relayItems']['edges'][0]['node']['name'] == 'foo'


def test_should_reduce_number_of_queries_in_relay_schema_by_using_select_related():
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                        foo
                        parent {
                            id
                        }
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='bar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('parent')
    assert_query_equality(items, optimized_items)


def test_should_reduce_number_of_queries_in_relay_schema_by_using_prefetch_related():
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                        foo
                        children {
                            id
                            foo
                        }
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)
