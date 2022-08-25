from .utils import is_iterable, noop


def _normalize_model_field(value):
    if not callable(value):
        return_value = value
        value = lambda *args, **kwargs: return_value
    return value


def _normalize_hint_value(value):
    if not callable(value):
        if not is_iterable(value):
            value = (value,)
        return_value = value
        value = lambda *args, **kwargs: return_value
    return value


class OptimizationHints(object):
    def __init__(
        self,
        model_field=None,
        select_related=noop,
        prefetch_related=noop,
        only=noop,
        annotate=noop,
    ):
        self.model_field = _normalize_model_field(model_field)
        self.prefetch_related = _normalize_hint_value(prefetch_related)
        self.select_related = _normalize_hint_value(select_related)
        self.only = _normalize_hint_value(only)
        self.annotate = _normalize_hint_value(annotate)
