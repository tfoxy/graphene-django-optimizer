import pytest

from django.db.models import Prefetch
import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema


def assert_query_equality(left_query, right_query):
    assert str(left_query.query) == str(right_query.query)
    assert left_query._prefetch_related_lookups == right_query._prefetch_related_lookups
    for (i, lookup) in enumerate(left_query._prefetch_related_lookups):
        if isinstance(lookup, Prefetch):
            right_lookup = right_query._prefetch_related_lookups[i]
            assert_query_equality(lookup.queryset, right_lookup.queryset)


@pytest.mark.django_db
def test_query_should_reduce_number_of_queries_by_using_select_related():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "bar") {
                id
                parent {
                    id
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='bar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('parent')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_reduce_number_of_queries_by_using_prefetch_related():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                children {
                    id
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_optimize_when_using_fragments():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "bar") {
                ...ItemFragment
            }
        }
        fragment ItemFragment on ItemType {
            id
            parent {
                id
            }
        }
    ''')
    qs = Item.objects.filter(name='bar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('parent')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_not_try_to_optimize_scalar_model_fields():
    Item.objects.create(name='foo')
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                name
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_not_try_to_optimize_non_model_fields():
    Item.objects.create(name='foo')
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_prefetch_field_with_camel_case_name():
    item = Item.objects.create(name='foo')
    Item.objects.create(name='bar', item=item)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                itemSet {
                    id
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('item_set')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_select_nested_related_fields():
    parent = Item.objects.create(name='foo')
    parent = Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                parent {
                    id
                    parent {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foobar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('parent__parent')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_prefetch_nested_related_fields():
    parent = Item.objects.create(name='foo')
    parent = Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                children {
                    id
                    children {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children__children')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_prefetch_nested_select_related_field():
    parent = Item.objects.create(name='foo')
    item = Item.objects.create(name='foobar')
    Item.objects.create(name='bar', parent=parent, item=item)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                children {
                    id
                    item {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch('children', queryset=Item.objects.select_related('item')),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_select_nested_prefetch_related_field():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                item {
                    id
                    children {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foobar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('item').prefetch_related('item__children')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_query_should_select_nested_prefetch_and_select_related_fields():
    parent = Item.objects.create(name='foo')
    item = Item.objects.create(name='bar_item')
    Item.objects.create(name='bar', parent=parent, item=item)
    Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                item {
                    id
                    children {
                        id
                        item {
                            id
                        }
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foobar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('item').prefetch_related(
        Prefetch('item__children', queryset=Item.objects.select_related('item')),
    )
    assert_query_equality(items, optimized_items)
