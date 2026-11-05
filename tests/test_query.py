import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.db.models import Prefetch
import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    GenericComment,
    GenericCommentedItem,
    Item,
    OtherItem,
    RelatedOneToManyItem,
    SomeOtherItem,
)
from .schema import schema
from .test_utils import assert_query_equality


@pytest.mark.django_db
def test_should_reduce_number_of_queries_by_using_select_related():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "bar") {
                id
                foo
                parent {
                    id
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="bar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("parent")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_reduce_number_of_queries_by_using_prefetch_related():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related("children")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_optimize_scalar_model_fields():
    # Item.objects.create(name='foo')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                name
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only("id", "name")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_optimize_scalar_foreign_key_model_fields():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "bar") {
                id
                parentId
            }
        }
    """,
    )
    qs = Item.objects.filter(name="bar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only("id", "parent_id")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_not_try_to_optimize_non_model_fields():
    # Item.objects.create(name='foo')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                foo
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_not_try_to_optimize_non_field_model_fields():
    # Item.objects.create(name='foo')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                unoptimizedTitle
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_try_to_optimize_non_field_model_fields_when_disabling_abort_only():
    # Item.objects.create(name='foo')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                unoptimizedTitle
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info, disable_abort_only=True)
    optimized_items = qs.only("id")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_optimize_when_using_fragments():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="bar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("parent").only("id", "parent__id")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_prefetch_field_with_camel_case_name():
    # item = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', item=item)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related("item_set")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_select_nested_related_fields():
    # parent = Item.objects.create(name='foo')
    # parent = Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foobar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("parent__parent")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_prefetch_nested_related_fields():
    # parent = Item.objects.create(name='foo')
    # parent = Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', parent=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related("children__children")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_prefetch_nested_select_related_field():
    # parent = Item.objects.create(name='foo')
    # item = Item.objects.create(name='foobar')
    # Item.objects.create(name='bar', parent=parent, item=item)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch("children", queryset=Item.objects.select_related("item")),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_select_nested_prefetch_related_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    # Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foobar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("item").prefetch_related("item__children")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_select_nested_prefetch_and_select_related_fields():
    # parent = Item.objects.create(name='foo')
    # item = Item.objects.create(name='bar_item')
    # Item.objects.create(name='bar', parent=parent, item=item)
    # Item.objects.create(name='foobar', item=parent)
    info = create_resolve_info(
        schema,
        """
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
    """,
    )
    qs = Item.objects.filter(name="foobar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("item").prefetch_related(
        Prefetch("item__children", queryset=Item.objects.select_related("item")),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_fetch_fields_of_related_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "bar") {
                id
                parent {
                    id
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="bar")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("parent").only("id", "parent__id")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_fetch_fields_of_prefetched_field():
    # parent = Item.objects.create(name='foo')
    # Item.objects.create(name='bar', parent=parent)
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                foo
                children {
                    id
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch("children", queryset=Item.objects.only("id", "parent__id")),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_fetch_child_model_field_for_interface_field():
    # Item.objects.create(name='foo')
    # ExtraDetailedItem.objects.create(name='foo', extra_detail='test')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                ... on ExtraDetailedItemType {
                    extraDetail
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("detaileditem__extradetaileditem").only(
        "id", "detaileditem__extradetaileditem__extra_detail"
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.skip(reason="will be tested in the future")
@pytest.mark.django_db
def test_should_fetch_field_of_child_model_when_parent_has_no_optimized_field():
    # Item.objects.create(name='foo')
    # DetailedItem.objects.create(name='foo', item_type='test')
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                item_type
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("detaileditem").only(
        "id", "detaileditem__item_type"
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_fetch_field_inside_interface_fragment():
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                ... on DetailedInterface {
                    detail
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related("detaileditem").only(
        "id", "detaileditem__detail"
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_use_nested_prefetch_related_while_also_selecting_only_required_fields():
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                children {
                    children {
                        id
                    }
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            "children",
            queryset=Item.objects.only("id", "parent_id").prefetch_related(
                Prefetch(
                    "children",
                    queryset=Item.objects.only("id", "parent_id"),
                )
            ),
        ),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_check_reverse_relations_add_foreign_key():
    info = create_resolve_info(
        schema,
        """
        query {
            items {
                otmItems {
                    id
                }
            }
        }
    """,
    )
    qs = Item.objects.all()
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            "otm_items",
            queryset=RelatedOneToManyItem.objects.only("id", "item_id"),
        ),
    )
    assert_query_equality(items, optimized_items)

    # When the query is not optimized, there will be an additional queries
    for i in range(3):
        the_item = Item.objects.create(name="foo")
        for k in range(3):
            RelatedOneToManyItem.objects.create(
                name="bar{}{}".format(i, k), item=the_item
            )

    with CaptureQueriesContext(connection) as expected_query_capture:
        for i in items:
            for k in i.otm_items.all():
                pass

    with CaptureQueriesContext(connection) as optimized_query_capture:
        for i in optimized_items:
            for k in i.otm_items.all():
                pass

    assert len(optimized_query_capture.captured_queries) == 2
    assert len(expected_query_capture) == len(optimized_query_capture)


@pytest.mark.django_db
def test_should_only_use_the_only_and_not_select_related():
    info = create_resolve_info(
        schema,
        """
        query {
            otherItems {
                id
                name
            }
        }
    """,
    )
    qs = OtherItem.objects.all()
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only("id", "name")
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_accept_two_hints_with_same_prefetch_to_attr_and_keep_one_of_them():
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                filteredChildren(name: "bar") {
                    id
                    name
                }
                auxFilteredChildren(name: "bar") { # Same name to generate Prefetch with same to_attr
                    id
                    name
                }
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            "children",
            queryset=Item.objects.filter(name="bar").only("id", "name"),
            to_attr="gql_filtered_children_foo",
        )
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_check_generic_relations_add_object_id_and_content_type():
    info = create_resolve_info(
        schema,
        """
        query {
            genericCommentedItems {
                comments {
                    id
                }
            }
        }
    """,
    )
    qs = GenericCommentedItem.objects.all()
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            "comments",
            queryset=GenericComment.objects.only("id", "object_id", "content_type"),
        ),
    )
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
@pytest.mark.parametrize("num_items,num_comments", [(1, 1), (3, 3), (5, 4)])
def test_should_prefetch_generic_relations_in_constant_number_of_queries(
    num_items, num_comments
):
    info = create_resolve_info(
        schema,
        """
        query {
            genericCommentedItems {
                comments {
                    id
                }
            }
        }
    """,
    )
    for i in range(num_items):
        item = GenericCommentedItem.objects.create(name="foo{}".format(i))
        for k in range(num_comments):
            item.comments.create(text="bar{}{}".format(i, k))

    items = gql_optimizer.query(GenericCommentedItem.objects.all(), info)

    with CaptureQueriesContext(connection) as query_capture:
        comment_ids = [comment.id for item in items for comment in item.comments.all()]

    assert len(comment_ids) == num_items * num_comments
    # One query for the items and one for the prefetched comments. Without
    # object_id/content_type in only(), Django reloads both deferred fields
    # for every comment when matching it to its parent.
    assert len(query_capture.captured_queries) == 2, [
        q["sql"] for q in query_capture.captured_queries
    ]


@pytest.mark.django_db
def test_should_select_related_inside_generic_relation_prefetch():
    info = create_resolve_info(
        schema,
        """
        query {
            genericCommentedItems {
                comments {
                    id
                    who {
                        id
                    }
                }
            }
        }
    """,
    )
    qs = GenericCommentedItem.objects.all()
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related(
        Prefetch(
            "comments",
            queryset=GenericComment.objects.select_related("who").only(
                "id", "object_id", "content_type", "who__id"
            ),
        ),
    )
    assert_query_equality(items, optimized_items)

    who = SomeOtherItem.objects.create(name="who")
    for i in range(3):
        item = GenericCommentedItem.objects.create(name="foo{}".format(i))
        for k in range(3):
            item.comments.create(text="bar{}{}".format(i, k), who=who)

    with CaptureQueriesContext(connection) as query_capture:
        who_ids = [comment.who.id for item in items for comment in item.comments.all()]

    assert who_ids == [who.id] * 9
    assert len(query_capture.captured_queries) == 2, [
        q["sql"] for q in query_capture.captured_queries
    ]
