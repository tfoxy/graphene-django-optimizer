# graphene-django-optimizer

[![build status](https://img.shields.io/travis/tfoxy/graphene-django-optimizer.svg)](https://travis-ci.com/github/tfoxy/graphene-django-optimizer)
[![coverage](https://img.shields.io/codecov/c/github/tfoxy/graphene-django-optimizer.svg)](https://codecov.io/gh/tfoxy/graphene-django-optimizer)
[![PyPI version](https://img.shields.io/pypi/v/graphene-django-optimizer.svg)](https://pypi.org/project/graphene-django-optimizer/)
![python version](https://img.shields.io/pypi/pyversions/graphene-django-optimizer.svg)
![django version](https://img.shields.io/pypi/djversions/graphene-django-optimizer.svg)

Optimize queries executed by [graphene-django](https://github.com/graphql-python/graphene-django) automatically, using [`select_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-related), [`prefetch_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#prefetch-related) and [`only`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#only) methods of Django QuerySet.



## Install

```bash
pip install graphene-django-optimizer
```

*Note: If you are using Graphene V2, please install version `0.8`. v0.9 and forward will support only Graphene V3*

## Usage

Having the following schema based on [the tutorial of graphene-django](http://docs.graphene-python.org/projects/django/en/latest/tutorial-plain/#hello-graphql-schema-and-object-types) (notice the use of `gql_optimizer`)

```py
# cookbook/ingredients/schema.py
import graphene

from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from cookbook.ingredients.models import Category, Ingredient


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category


class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient


class Query(graphene.ObjectType):
    all_categories = graphene.List(CategoryType)
    all_ingredients = graphene.List(IngredientType)

    def resolve_all_categories(root, info):
        return gql_optimizer.query(Category.objects.all(), info)

    def resolve_all_ingredients(root, info):
        return gql_optimizer.query(Ingredient.objects.all(), info)
```


We will show some graphql queries and the queryset that will be executed.

Fetching all the ingredients with the related category:

```graphql
{
  allIngredients {
    id
    name
    category {
        id
        name
    }
  }
}
```

```py
# optimized queryset:
ingredients = (
    Ingredient.objects
    .select_related('category')
    .only('id', 'name', 'category__id', 'category__name')
)
```

Fetching all the categories with the related ingredients:

```graphql
{
  allCategories {
    id
    name
    ingredients {
        id
        name
    }
  }
}
```

```py
# optimized queryset:
categories = (
    Category.objects
    .only('id', 'name')
    .prefetch_related(Prefetch(
        'ingredients',
        queryset=Ingredient.objects.only('id', 'name'),
    ))
)
```


## Advanced usage

Sometimes we need to have a custom resolver function. In those cases, the field can't be auto optimized.
So we need to use `gql_optimizer.resolver_hints` decorator to indicate the optimizations.

If the resolver returns a model field, we can use the `model_field` argument:

```py
import graphene
import graphene_django_optimizer as gql_optimizer


class ItemType(gql_optimizer.OptimizedDjangoObjectType):
    product = graphene.Field('ProductType')

    @gql_optimizer.resolver_hints(
        model_field='product',
    )
    def resolve_product(root, info):
        # check if user have permission for seeing the product
        if info.context.user.is_anonymous():
            return None
        return root.product
```

This will automatically optimize any subfield of `product`.

Now, if the resolver uses related fields, you can use the `select_related` argument:

```py
import graphene
import graphene_django_optimizer as gql_optimizer


class ItemType(gql_optimizer.OptimizedDjangoObjectType):
    name = graphene.String()

    @gql_optimizer.resolver_hints(
        select_related=('product', 'shipping'),
        only=('product__name', 'shipping__name'),
    )
    def resolve_name(root, info):
        return '{} {}'.format(root.product.name, root.shipping.name)
```

Notice the usage of the type `OptimizedDjangoObjectType`, which enables
optimization of any single node queries.

Finally, if your field has an argument for filtering results,
you can use the `prefetch_related` argument with a function
that returns a `Prefetch` instance as the value.

```py
from django.db.models import Prefetch
import graphene
import graphene_django_optimizer as gql_optimizer


class CartType(gql_optimizer.OptimizedDjangoObjectType):
    items = graphene.List(
        'ItemType',
        product_id=graphene.ID(),
    )

    @gql_optimizer.resolver_hints(
        prefetch_related=lambda info, product_id: Prefetch(
            'items',
            queryset=gql_optimizer.query(Item.objects.filter(product_id=product_id), info),
            to_attr='gql_product_id_' + product_id,
        ),
    )
    def resolve_items(root, info, product_id):
        return getattr(root, 'gql_product_id_' + product_id)
```

With these hints, any field can be optimized.


### Optimize with non model fields

Sometimes we need to have a custom non model fields. In those cases, the optimizer would not optimize with the Django `.only()` method.
So if we still want to optimize with the `.only()` method, we need to use `disable_abort_only` option:

```py

class IngredientType(gql_optimizer.OptimizedDjangoObjectType):
    calculated_calories = graphene.String()

    class Meta:
        model = Ingredient
    
    def resolve_calculated_calories(root, info):
        return get_calories_for_ingredient(root.id)


class Query(object):
    all_ingredients = graphene.List(IngredientType)

    def resolve_all_ingredients(root, info):
        return gql_optimizer.query(Ingredient.objects.all(), info, disable_abort_only=True)
```
