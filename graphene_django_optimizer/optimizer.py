import functools

from graphene.types.resolver import attr_resolver
from graphene_django import DjangoObjectType
from graphene_django.fields import DjangoListField
from graphql.execution.base import (
    get_field_def,
    get_operation_root_type,
)
from graphql.language.ast import FragmentSpread


def query(query, info):
    return QueryOptimizer(info).optimize(query)


class QueryOptimizer(object):
    def __init__(self, info):
        self.root_ast = info.field_asts[0]
        self.schema = info.schema
        self.fragments = info.fragments
        parent_type = get_operation_root_type(info.schema, info.operation)
        field_def = get_field_def(info.schema, parent_type, info.field_name)
        root_type = field_def.type
        if hasattr(root_type, 'of_type'):
            root_type = root_type.of_type
        self.root_type = root_type

    def optimize(self, query):
        return self._optimize_gql_selections(
            query,
            self.root_type,
            self.root_ast.selection_set.selections,
        )

    def _optimize_gql_selections(self, query, field_type, selections):
        model = field_type.graphene_type._meta.model
        for selection in selections:
            name = selection.name.value
            if isinstance(selection, FragmentSpread):
                fragment = self.fragments[name]
                query = self._optimize_gql_selections(
                    query,
                    field_type,
                    fragment.selection_set.selections,
                )
            else:
                field = field_type.fields[name]
                resolver = field.resolver
                model_field_name = None
                if resolver == DjangoObjectType.resolve_id:
                    model_field_name = 'id'
                elif isinstance(resolver, functools.partial):
                    resolver_fn = resolver
                    if resolver_fn.func == DjangoListField.list_resolver:
                        resolver_fn = resolver_fn.args[0]
                    if resolver_fn.func == attr_resolver:
                        model_field_name = resolver_fn.args[0]
                if model_field_name:
                    model_field_name_lookup = model_field_name
                    if model_field_name_lookup.endswith('_set'):
                        model_field_name_lookup = model_field_name_lookup[:-4]
                    value_model_field = model._meta.get_field(model_field_name_lookup)
                    if value_model_field.many_to_one or value_model_field.one_to_one:
                        query = query.select_related(model_field_name)
                    if value_model_field.one_to_many:
                        query = query.prefetch_related(model_field_name)
        return query
