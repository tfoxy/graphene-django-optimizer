import pytest

from django.db.models import Prefetch
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
                foo
                childrenNames
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_optimize_with_prefetch_related_as_a_string():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                auxChildrenNames
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_optimize_with_prefetch_related_as_a_function():
    parent = Item.objects.create(name='foo')
    Item.objects.create(name='bar', parent=parent)
    Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                filteredChildren(name: "bar") {
                    id
                    foo
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            'children',
            queryset=Item.objects.filter(name='bar'),
            to_attr='gql_filtered_children_bar',
        ),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_return_valid_result_with_prefetch_related_as_a_function():
    parent = Item.objects.create(id=1, name='foo')
    Item.objects.create(id=2, name='bar', parent=parent)
    Item.objects.create(id=3, name='foobar', parent=parent)
    result = schema.execute('''
        query {
            items(name: "foo") {
                id
                foo
                filteredChildren(name: "bar") {
                    id
                    foo
                }
            }
        }
    ''')
    assert result.data['items'][0]['filteredChildren'][0]['id'] == '2'
