import functools

from django.core.exceptions import FieldDoesNotExist
from django.db.models import ForeignKey, Prefetch
from django.db.models.constants import LOOKUP_SEP
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
        self.root_type = self._get_type(field_def)

    def optimize(self, query):
        store = self._optimize_gql_selections(
            self.root_type,
            self.root_ast,
        )
        return store.optimize_query(query)

    def _get_type(self, field_def):
        a_type = field_def.type
        if hasattr(a_type, 'of_type'):
            a_type = a_type.of_type
        return a_type

    def _optimize_gql_selections(self, field_type, field_ast):
        store = QueryOptimizerStore()
        selection_set = field_ast.selection_set
        if not selection_set:
            return store
        model = field_type.graphene_type._meta.model
        for selection in selection_set.selections:
            name = selection.name.value
            if isinstance(selection, FragmentSpread):
                fragment = self.fragments[name]
                fragment_store = self._optimize_gql_selections(
                    field_type,
                    fragment,
                )
                store.append(fragment_store)
            else:
                selection_field_def = field_type.fields[name]
                self._optimize_field(store, model, selection, selection_field_def)
        return store

    def _optimize_field(self, store, model, selection, field_def):
        resolver = field_def.resolver
        name = None
        optimization_hints = getattr(resolver, 'optimization_hints', None)
        if optimization_hints:
            name = optimization_hints.model_field
        if not name:
            if resolver == DjangoObjectType.resolve_id:
                name = 'id'
            elif isinstance(resolver, functools.partial):
                resolver_fn = resolver
                if resolver_fn.func == DjangoListField.list_resolver:
                    resolver_fn = resolver_fn.args[0]
                if resolver_fn.func == attr_resolver:
                    name = resolver_fn.args[0]
        if name:
            model_field = self._get_model_field_from_name(model, name)
            if not model_field:
                return
            if (
                isinstance(model_field, ForeignKey) and
                model_field.name != name and
                model_field.get_attname() == name
            ):
                # If it is a Foreign Key ID,
                # don't try to select_related or prefetch_related
                return
            if model_field.many_to_one or model_field.one_to_one:
                field_store = self._optimize_gql_selections(
                    self._get_type(field_def),
                    selection,
                )
                store.select_related(name, field_store)
            if model_field.one_to_many or model_field.many_to_many:
                field_store = self._optimize_gql_selections(
                    self._get_type(field_def),
                    selection,
                )
                store.prefetch_related(name, field_store, model_field.related_model)

    def _get_model_field_from_name(self, model, name):
        try:
            return model._meta.get_field(name)
        except FieldDoesNotExist:
            descriptor = model.__dict__[name]
            return getattr(descriptor, 'rel', None) \
                or getattr(descriptor, 'related', None)  # Django < 1.9


class QueryOptimizerStore():
    def __init__(self):
        self.select_list = []
        self.prefetch_list = []

    def select_related(self, name, store):
        if len(store.select_list) == 0:
            self.select_list.append(name)
        else:
            for select in store.select_list:
                self.select_list.append(name + LOOKUP_SEP + select)
        for prefetch in store.prefetch_list:
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(name)
            else:
                prefetch = name + LOOKUP_SEP + prefetch
            self.prefetch_list.append(prefetch)

    def prefetch_related(self, name, store, model):
        if len(store.prefetch_list) == 0 and len(store.select_list) == 0:
            self.prefetch_list.append(name)
        elif len(store.select_list) == 0:
            for prefetch in store.prefetch_list:
                self.prefetch_list.append(name + LOOKUP_SEP + prefetch)
        else:
            queryset = store.optimize_query(model.objects.all())
            self.prefetch_list.append(Prefetch(name, queryset=queryset))

    def optimize_query(self, query):
        for select in self.select_list:
            query = query.select_related(select)
        for prefetch in self.prefetch_list:
            query = query.prefetch_related(prefetch)
        return query

    def append(self, store):
        self.select_list += store.select_list
        self.prefetch_list += store.prefetch_list
