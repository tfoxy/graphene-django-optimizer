# graphene-django-optimizer

[![build status](https://img.shields.io/travis/tfoxy/graphene-django-optimizer.svg)](https://travis-ci.org/tfoxy/graphene-django-optimizer)
[![coverage](https://img.shields.io/codecov/c/github/tfoxy/graphene-django-optimizer.svg)](https://codecov.io/gh/tfoxy/graphene-django-optimizer)
[![PyPI version](https://img.shields.io/pypi/v/graphene-django-optimizer.svg)](https://pypi.org/project/graphene-django-optimizer/)
![python version](https://img.shields.io/pypi/pyversions/graphene-django-optimizer.svg)
![django version](https://img.shields.io/pypi/djversions/graphene-django-optimizer.svg)

Optimize queries executed by [graphene-django](https://github.com/graphql-python/graphene-django) automatically, using [`select_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-related), [`prefetch_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#prefetch-related) and [`only`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#only) methods of Django QuerySet.


## Install

```bash
pip install graphene-django-optimizer
```


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


class Query(object):
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
  all_ingredients {
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
  all_categories {
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
