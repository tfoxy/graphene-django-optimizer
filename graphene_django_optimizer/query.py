import functools

from django.core.exceptions import FieldDoesNotExist
from django.db.models import ForeignKey, Prefetch
from django.db.models.constants import LOOKUP_SEP
from graphene.types.resolver import attr_resolver
from graphene_django import DjangoObjectType
from graphene_django.fields import DjangoListField
from graphql import ResolveInfo
from graphql.execution.base import (
    get_field_def,
)
from graphql.language.ast import FragmentSpread

from .utils import is_iterable


def query(queryset, info):
    return QueryOptimizer(info).optimize(queryset)


class QueryOptimizer(object):
    def __init__(self, info):
        self.root_info = info

    def optimize(self, queryset):
        info = self.root_info
        field_def = get_field_def(info.schema, info.parent_type, info.field_name)
        store = self._optimize_gql_selections(
            self._get_type(field_def),
            info.field_asts[0],
            info.parent_type,
        )
        return store.optimize_queryset(queryset)

    def _get_type(self, field_def):
        a_type = field_def.type
        if hasattr(a_type, 'of_type'):
            a_type = a_type.of_type
        return a_type

    def _optimize_gql_selections(self, field_type, field_ast, parent_type):
        store = QueryOptimizerStore()
        selection_set = field_ast.selection_set
        if not selection_set:
            return store
        model = field_type.graphene_type._meta.model
        for selection in selection_set.selections:
            name = selection.name.value
            if isinstance(selection, FragmentSpread):
                fragment = self.root_info.fragments[name]
                fragment_store = self._optimize_gql_selections(
                    field_type,
                    fragment,
                    parent_type,
                )
                store.append(fragment_store)
            else:
                selection_field_def = field_type.fields[name]
                self._optimize_field(
                    store,
                    model,
                    selection,
                    selection_field_def,
                    field_type,
                )
        return store

    def _optimize_field(self, store, model, selection, field_def, parent_type):
        self._optimize_field_by_name(store, model, selection, field_def, parent_type)
        self._optimize_field_by_hints(store, selection, field_def, parent_type)

    def _optimize_field_by_name(self, store, model, selection, field_def, parent_type):
        name = self._get_name_from_resolver(field_def.resolver)
        if not name:
            return
        model_field = self._get_model_field_from_name(model, name)
        if not model_field:
            return
        if self._is_foreign_key_id(model_field, name):
            return
        if model_field.many_to_one or model_field.one_to_one:
            field_store = self._optimize_gql_selections(
                self._get_type(field_def),
                selection,
                parent_type,
            )
            store.select_related(name, field_store)
        elif model_field.one_to_many or model_field.many_to_many:
            field_store = self._optimize_gql_selections(
                self._get_type(field_def),
                selection,
                parent_type,
            )
            related_queryset = model_field.related_model.objects.all()
            store.prefetch_related(name, field_store, related_queryset)

    def _get_optimization_hints(self, resolver):
        return getattr(resolver, 'optimization_hints', None)

    def _optimize_field_by_hints(self, store, selection, field_def, parent_type):
        optimization_hints = self._get_optimization_hints(field_def.resolver)
        if not optimization_hints:
            return
        info = self._create_resolve_info(
            selection.name.value,
            (selection,),
            self._get_type(field_def),
            parent_type,
        )
        args = tuple(arg.value.value for arg in selection.arguments)
        self._add_optimization_hints(
            optimization_hints.select_related(info, *args),
            store.select_list,
        )
        self._add_optimization_hints(
            optimization_hints.prefetch_related(info, *args),
            store.prefetch_list,
        )

    def _add_optimization_hints(self, source, target):
        if source:
            if not is_iterable(source):
                source = (source,)
            target += source

    def _get_name_from_resolver(self, resolver):
        optimization_hints = self._get_optimization_hints(resolver)
        if optimization_hints:
            name = optimization_hints.model_field
            if name:
                return name
        if resolver == DjangoObjectType.resolve_id:
            return 'id'
        elif isinstance(resolver, functools.partial):
            resolver_fn = resolver
            if resolver_fn.func == DjangoListField.list_resolver:
                resolver_fn = resolver_fn.args[0]
            if resolver_fn.func == attr_resolver:
                return resolver_fn.args[0]

    def _get_model_field_from_name(self, model, name):
        try:
            return model._meta.get_field(name)
        except FieldDoesNotExist:
            descriptor = model.__dict__[name]
            return getattr(descriptor, 'rel', None) \
                or getattr(descriptor, 'related', None)  # Django < 1.9

    def _is_foreign_key_id(self, model_field, name):
        return (
            isinstance(model_field, ForeignKey) and
            model_field.name != name and
            model_field.get_attname() == name
        )

    def _create_resolve_info(self, field_name, field_asts, return_type, parent_type):
        return ResolveInfo(
            field_name,
            field_asts,
            return_type,
            parent_type,
            schema=self.root_info.schema,
            fragments=self.root_info.fragments,
            root_value=self.root_info.root_value,
            operation=self.root_info.operation,
            variable_values=self.root_info.variable_values,
            context=self.root_info.context,
        )


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

    def prefetch_related(self, name, store, queryset):
        if len(store.prefetch_list) == 0 and len(store.select_list) == 0:
            self.prefetch_list.append(name)
        elif len(store.select_list) == 0:
            for prefetch in store.prefetch_list:
                self.prefetch_list.append(name + LOOKUP_SEP + prefetch)
        else:
            queryset = store.optimize_queryset(queryset)
            self.prefetch_list.append(Prefetch(name, queryset=queryset))

    def optimize_queryset(self, queryset):
        for select in self.select_list:
            queryset = queryset.select_related(select)
        for prefetch in self.prefetch_list:
            queryset = queryset.prefetch_related(prefetch)
        return queryset

    def append(self, store):
        self.select_list += store.select_list
        self.prefetch_list += store.prefetch_list
