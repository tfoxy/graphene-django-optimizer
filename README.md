# graphene-django-optimizer


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
categories = (
    Category.objects
    .only('id', 'name')
    .prefetch_related(Prefetch(
        'ingredients',
        queryset=Ingredient.objects.only('id', 'name'),
    ))
)
```


## Contribute

The system must have installed:

* python 3
* virtualenv

```sh
virtualenv -p python3 venv
. venv/bin/activate
pip install -r dev-requirements.txt
# run tests:
python setup.py test
```
