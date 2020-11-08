import pytest

from django.db.models import Prefetch
import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema
from .test_utils import assert_query_equality


# @pytest.mark.django_db
def test_should_optimize_non_django_field_if_it_has_an_optimization_hint_in_the_resolver():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
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
    optimized_items = qs.prefetch_related(
        Prefetch(
            'children',
            queryset=Item.objects.only('id', 'parent_id'),
        ),
    )
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_optimize_with_prefetch_related_as_a_string():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
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


def test_should_optimize_with_prefetch_related_as_a_function():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
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


QUERY_CONNECTION_NESTED_INPUT_OBJECT = '''
    query($filters: ItemFilterInput) {
        items(name: "foo") {
            id
            foo
            childrenCustomFiltered(filterInput: $filters) {
                edges {
                    node {
                        id
                        value
                    }
                }
            }
        }
    }
'''


@pytest.mark.parametrize("variables, expected_gte", [
    ({"filters": {'value': {'gte': 11}}}, 11),
    ({}, 0),
])
@pytest.mark.django_db
def test_should_optimize_with_prefetch_related_as_a_function_with_object_input(
    variables, expected_gte
):
    """This test attempt to provide a nested object as a variable and a null value
    as a filter. The objective is to ensure null and nested objects are properly
    resolved.
    """

    query = QUERY_CONNECTION_NESTED_INPUT_OBJECT
    info = create_resolve_info(schema, query, variables=variables)

    optimized_items = Item.objects.prefetch_related(
        Prefetch(
            'children',
            queryset=Item.objects.only('id', 'value').filter(value__gte=expected_gte),
            to_attr='gql_custom_filtered_children',
        ),
    )

    items = gql_optimizer.query(Item.objects, info)
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
                    parentId
                    foo
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['items'][0]['filteredChildren'][0]['id'] == 'SXRlbVR5cGU6Mg=='
    assert result.data['items'][0]['filteredChildren'][0]['parentId'] == 'SXRlbVR5cGU6MQ=='


@pytest.mark.django_db
def test_should_return_valid_result_with_prefetch_related_as_a_function_using_variable():
    parent = Item.objects.create(id=1, name='foo')
    Item.objects.create(id=2, name='bar', parent=parent)
    Item.objects.create(id=3, name='foobar', parent=parent)
    result = schema.execute('''
        query Foo ($name: String!) {
            items(name: "foo") {
                id
                foo
                filteredChildren(name: $name) {
                    id
                    parentId
                    foo
                }
            }
        }
    ''', variables={'name': 'bar'})
    assert not result.errors
    assert result.data['items'][0]['filteredChildren'][0]['id'] == 'SXRlbVR5cGU6Mg=='
    assert result.data['items'][0]['filteredChildren'][0]['parentId'] == 'SXRlbVR5cGU6MQ=='
