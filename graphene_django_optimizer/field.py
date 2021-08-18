import types
from graphene.types.field import Field
from graphene.types.unmountedtype import UnmountedType

from .hints import OptimizationHints


def field(field_type, *args, **kwargs):
    if isinstance(field_type, UnmountedType):
        field_type = Field.mounted(field_type)

    optimization_hints = OptimizationHints(*args, **kwargs)
    wrap_resolve = field_type.wrap_resolve

    def get_optimized_resolver(self, parent_resolver):
        resolver = wrap_resolve(parent_resolver)
        resolver.optimization_hints = optimization_hints
        return resolver

    field_type.wrap_resolve = types.MethodType(get_optimized_resolver, field_type)
    return field_type
