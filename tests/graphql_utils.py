from graphql import (
    GraphQLResolveInfo,
    Source,
    Undefined,
    parse,
)
from graphql.execution.execute import (
    ExecutionContext,
    get_field_def,
)
from graphql.utilities import get_operation_root_type
from collections import defaultdict

from graphql.pyutils import Path


def create_execution_context(schema, request_string, variables=None):
    source = Source(request_string, "GraphQL request")
    document_ast = parse(source)
    return ExecutionContext.build(
        schema,
        document_ast,
        root_value=None,
        context_value=None,
        raw_variable_values=variables,
        operation_name=None,
        middleware=None,
    )


def get_field_asts_from_execution_context(exe_context):
    fields = exe_context.collect_fields(
        type,
        exe_context.operation.selection_set,
        defaultdict(list),
        set(),
    )
    # field_asts = next(iter(fields.values()))
    field_asts = tuple(fields.values())[0]
    return field_asts


def create_resolve_info(schema, request_string, variables=None, return_type=None):
    exe_context = create_execution_context(schema, request_string, variables)
    parent_type = get_operation_root_type(schema, exe_context.operation)
    field_asts = get_field_asts_from_execution_context(exe_context)

    field_ast = field_asts[0]
    field_name = field_ast.name.value

    if return_type is None:
        field_def = get_field_def(schema, parent_type, field_name)
        if not field_def:
            return Undefined
        return_type = field_def.type

    # The resolve function's optional third argument is a context value that
    # is provided to every resolve function within an execution. It is commonly
    # used to represent an authenticated user, or request-specific caches.
    return GraphQLResolveInfo(
        field_name,
        field_asts,
        return_type,
        parent_type,
        Path(None, 0, None),
        schema,
        exe_context.fragments,
        exe_context.root_value,
        exe_context.operation,
        exe_context.variable_values,
        exe_context.context_value,
        exe_context.is_awaitable,
    )
