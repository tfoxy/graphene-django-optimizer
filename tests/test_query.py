import pytest

from django.db.models import Prefetch
import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item, OtherItem
)
from .schema import schema
from .test_utils import assert_query_equality


# @pytest.mark.django_db
def test_should_reduce_number_of_queries_by_using_select_related():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "bar") {
                id
                foo
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


# @pytest.mark.django_db
def test_should_reduce_number_of_queries_by_using_prefetch_related():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
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
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_optimize_scalar_model_fields():
    # Item.objects.create(name='foo')
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
    optimized_items = qs.only('id', 'name')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_optimize_scalar_foreign_key_model_fields():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "bar") {
                id
                parentId
            }
        }
    ''')
    qs = Item.objects.filter(name='bar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only('id', 'parent_id')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_not_try_to_optimize_non_model_fields():
    # Item.objects.create(name='foo')
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


# @pytest.mark.django_db
def test_should_not_try_to_optimize_non_field_model_fields():
    # Item.objects.create(name='foo')
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                unoptimizedTitle
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_optimize_when_using_fragments():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
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
    optimized_items = qs.select_related('parent').only('id', 'parent__id')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_prefetch_field_with_camel_case_name():
    # item = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', item=item)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                itemSet {
                    id
                    foo
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('item_set')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_select_nested_related_fields():
    # parent = Item.objects.create(name='foo')
    # parent = Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                foo
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


# @pytest.mark.django_db
def test_should_prefetch_nested_related_fields():
    # parent = Item.objects.create(name='foo')
    # parent = Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                children {
                    id
                    foo
                    children {
                        id
                        foo
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children__children')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_prefetch_nested_select_related_field():
    # parent = Item.objects.create(name='foo')
    # item = Item.objects.create(name='foobar')
    # Item.objects.create(name='bar', parent=parent, item=item)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                children {
                    id
                    foo
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


# @pytest.mark.django_db
def test_should_select_nested_prefetch_related_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                foo
                item {
                    id
                    children {
                        id
                        foo
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foobar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('item').prefetch_related('item__children')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_select_nested_prefetch_and_select_related_fields():
    # parent = Item.objects.create(name='foo')
    # item = Item.objects.create(name='bar_item')
    # Item.objects.create(name='bar', parent=parent, item=item)
    # Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foobar") {
                id
                foo
                item {
                    id
                    children {
                        id
                        foo
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


# @pytest.mark.django_db
def test_should_fetch_fields_of_related_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
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
    optimized_items = qs.select_related('parent').only('id', 'parent__id')
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_fetch_fields_of_prefetched_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                foo
                children {
                    id
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch('children', queryset=Item.objects.only('id')),
    )
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_fetch_child_model_field_for_interface_field():
    # Item.objects.create(name='foo')
    # ExtraDetailedItem.objects.create(name='foo', extra_detail='test')
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                ... on ExtraDetailedItemType {
                    extraDetail
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = (
        qs
        .select_related('detaileditem__extradetaileditem')
        .only('id', 'detaileditem__extradetaileditem__extra_detail')
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.skip(reason='will be tested in the future')
# @pytest.mark.django_db
def test_should_fetch_field_of_child_model_when_parent_has_no_optimized_field():
    # Item.objects.create(name='foo')
    # DetailedItem.objects.create(name='foo', item_type='test')
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                item_type
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = (
        qs
        .select_related('detaileditem')
        .only('id', 'detaileditem__item_type')
    )
    assert_query_equality(items, optimized_items)


def test_should_fetch_field_inside_interface_fragment():
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                id
                ... on DetailedInterface {
                    detail
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = (
        qs
        .select_related('detaileditem')
        .only('id', 'detaileditem__detail')
    )
    assert_query_equality(items, optimized_items)


def test_should_use_nested_prefetch_related_while_also_selecting_only_required_fields():
    info = create_resolve_info(schema, '''
        query {
            items(name: "foo") {
                children {
                    children {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            'children',
            queryset=Item.objects.only('id'),
        ),
    )
    assert_query_equality(items, optimized_items)


# @pytest.mark.django_db
def test_should_only_use_the_only_and_not_select_related():
    info = create_resolve_info(schema, '''
        query {
            otherItems {
                id
                name
            }
        }
    ''')
    qs = OtherItem.objects.all()
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only('id', 'name')
    assert_query_equality(items, optimized_items)
