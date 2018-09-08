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


def test_should_optimize_query_by_only_requesting_id_field():
    try:
        from django.db.models import DEFERRED  # noqa: F401
    except ImportError:
        # Query cannot be optimized if DEFERRED is not present.
        # When the ConnectionField is used, it will throw the following error:
        # Expected value of type "ItemNode" but got: Item_Deferred_item_id_parent_id.
        return
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only('id')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_work_fine_with_page_info_field():
    Item.objects.create(id=7, name='foo')
    Item.objects.create(id=13, name='bar')
    Item.objects.create(id=17, name='foobar')
    result = schema.execute('''
        query {
            relayItems(first: 2) {
                pageInfo {
                    hasNextPage
                }
                edges {
                    node {
                        id
                    }
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['relayItems']['pageInfo']['hasNextPage'] is True