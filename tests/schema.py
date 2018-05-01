import graphene

from graphene_django.types import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from .models import (
    Category,
    Ingredient,
    PurchaseOrder,
    PurchaseOrderItem,
    User,
)


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category


class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient


class UserType(DjangoObjectType):
    class Meta:
        model = User


class PurchaseOrderType(DjangoObjectType):
    foo = graphene.String()
    total_price = graphene.String()

    class Meta:
        model = PurchaseOrder

    def resolve_foo(order, info):
        return 'bar'

    def resolve_total_price(order, info):
        return order.get_total_price()


class PurchaseOrderItemType(DjangoObjectType):
    class Meta:
        model = PurchaseOrderItem


class Query(graphene.ObjectType):
    all_categories = graphene.List(CategoryType)
    all_ingredients = graphene.List(IngredientType)
    user = graphene.Field(UserType, name=graphene.String())
    purchase_order = graphene.Field(PurchaseOrderType, id=graphene.ID())

    def resolve_all_categories(root, info):
        return gql_optimizer.query(Category.objects.all(), info)

    def resolve_all_ingredients(root, info):
        return gql_optimizer.query(Ingredient.objects.all(), info)

    def resolve_user(root, info, name):
        return gql_optimizer.query(User.objects.filter(name=name), info).first()

    def resolve_purchase_order(root, info, id):
        return gql_optimizer.query(PurchaseOrder.objects.filter(id__in=id), info).first()


schema = graphene.Schema(query=Query)
