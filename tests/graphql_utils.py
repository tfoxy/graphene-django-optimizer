from django.test import RequestFactory
from graphql import (
    ResolveInfo,
    Source,
    Undefined,
    parse,
)
from graphql.execution.base import (
    ExecutionContext,
    collect_fields,
    get_field_def,
    get_operation_root_type,
)
from graphql.pyutils.default_ordered_dict import DefaultOrderedDict


def create_execution_context(schema, request_string, variables=None, user=None):
    source = Source(request_string, 'GraphQL request')
    document_ast = parse(source)
    request = RequestFactory()
    request.user = user
    return ExecutionContext(
        schema,
        document_ast,
        root_value=None,
        context_value=request,
        variable_values=variables,
        operation_name=None,
        executor=None,
        middleware=None,
        allow_subscriptions=False,
    )


def get_field_asts_from_execution_context(exe_context):
    fields = collect_fields(
        exe_context,
        type,
        exe_context.operation.selection_set,
        DefaultOrderedDict(list),
        set()
    )
    # field_asts = next(iter(fields.values()))
    field_asts = tuple(fields.values())[0]
    return field_asts


def create_resolve_info(schema, request_string, variables=None, user=None):
    exe_context = create_execution_context(schema, request_string, variables, user)
    parent_type = get_operation_root_type(schema, exe_context.operation)
    field_asts = get_field_asts_from_execution_context(exe_context)

    field_ast = field_asts[0]
    field_name = field_ast.name.value

    field_def = get_field_def(schema, parent_type, field_name)
    if not field_def:
        return Undefined
    return_type = field_def.type

    # The resolve function's optional third argument is a context value that
    # is provided to every resolve function within an execution. It is commonly
    # used to represent an authenticated user, or request-specific caches.
    context = exe_context.context_value
    return ResolveInfo(
        field_name,
        field_asts,
        return_type,
        parent_type,
        schema=schema,
        fragments=exe_context.fragments,
        root_value=exe_context.root_value,
        operation=exe_context.operation,
        variable_values=exe_context.variable_values,
        context=context
    )
