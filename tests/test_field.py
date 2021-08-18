import pytest
import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import Item
from .schema import schema
from .test_utils import assert_query_equality


@pytest.mark.django_db
def test_should_optimize_non_django_field_if_it_has_an_optimization_hint_in_the_field():
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "bar") {
                id
                foo
                father {
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
def test_should_optimize_with_only_hint():
    info = create_resolve_info(
        schema,
        """
        query {
            items(name: "foo") {
                id
                title
            }
        }
    """,
    )
    qs = Item.objects.filter(name="foo")
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only("id", "name")
    assert_query_equality(items, optimized_items)
