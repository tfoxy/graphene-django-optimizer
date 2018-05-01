import pytest

import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Category,
    Ingredient,
    PurchaseOrder,
    User,
)
from .schema import schema


@pytest.mark.django_db
def test_query_should_reduce_number_of_queries_by_using_select_related():
    category = Category.objects.create(name='foo')
    Ingredient.objects.create(name='bar', category=category)
    info = create_resolve_info(schema, '''
        query {
            allIngredients {
                id
                name
                category {
                    id
                    name
                }
            }
        }
    ''')
    ingredients = gql_optimizer.query(Ingredient.objects.all(), info)
    # ingredients = gql_optimizer.query(Ingredient.objects.select_related('category').all(), info)
    assert len(ingredients) == 1
    assert ingredients[0].__dict__.get('_category_cache') == category


@pytest.mark.django_db
def test_query_should_reduce_number_of_queries_by_using_prefetch_related():
    category = Category.objects.create(name='foo')
    ingredient = Ingredient.objects.create(name='bar', category=category)
    info = create_resolve_info(schema, '''
        query {
            allCategories {
                id
                name
                ingredients {
                    id
                    name
                }
            }
        }
    ''')
    categories = gql_optimizer.query(Category.objects.all(), info)
    # categories = gql_optimizer.query(Category.objects.prefetch_related('ingredients').all(), info)
    assert len(categories) == 1
    assert categories.__dict__.get('_prefetch_related_lookups') == ('ingredients',)
    assert 'ingredients' in categories[0].__dict__.get('_prefetched_objects_cache')
    assert list(categories[0].__dict__['_prefetched_objects_cache']['ingredients']) == [ingredient]


@pytest.mark.django_db
def test_query_should_optimize_when_using_fragments():
    category = Category.objects.create(name='foo')
    Ingredient.objects.create(name='bar', category=category)
    info = create_resolve_info(schema, '''
        query {
            allIngredients {
                ...IngredientFragment
            }
        }
        fragment IngredientFragment on IngredientType {
            id
            name
            category {
                id
                name
            }
        }
    ''')
    ingredients = gql_optimizer.query(Ingredient.objects.all(), info)
    # ingredients = gql_optimizer.query(Ingredient.objects.select_related('category').all(), info)
    assert len(ingredients) == 1
    assert ingredients[0].__dict__.get('_category_cache') == category


@pytest.mark.django_db
def test_query_should_not_try_to_optimize_non_model_fields():
    purchase_order = PurchaseOrder.objects.create(id=1)
    info = create_resolve_info(schema, '''
        query {
            purchaseOrder(id: 1) {
                id
                foo
            }
        }
    ''')
    purchase_orders = gql_optimizer.query(PurchaseOrder.objects.all(), info)
    assert list(purchase_orders) == [purchase_order]


@pytest.mark.django_db
def test_query_should_prefetch_field_with_camel_case_name():
    user = User.objects.create(name='foo')
    purchase_order = PurchaseOrder.objects.create(buyer=user)
    info = create_resolve_info(schema, '''
        query {
            user(name: "foo") {
                id
                purchaseorderSet {
                    id
                }
            }
        }
    ''')
    users = gql_optimizer.query(User.objects.all(), info)
    # users = gql_optimizer.query(User.objects.prefetch_related('purchaseorder_set').all(), info)
    assert len(users) == 1
    assert users.__dict__.get('_prefetch_related_lookups') == ('purchaseorder_set',)
    assert 'purchaseorder' in users[0].__dict__.get('_prefetched_objects_cache')
    assert list(users[0].__dict__['_prefetched_objects_cache']['purchaseorder']) == [purchase_order]
