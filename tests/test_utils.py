from django.db.models import Prefetch


def assert_query_equality(left_query, right_query):
    assert str(left_query.query) == str(right_query.query)
    assert len(left_query._prefetch_related_lookups) == len(
        right_query._prefetch_related_lookups
    )
    for (i, lookup) in enumerate(left_query._prefetch_related_lookups):
        right_lookup = right_query._prefetch_related_lookups[i]
        if isinstance(lookup, Prefetch) and isinstance(right_lookup, Prefetch):
            assert_query_equality(lookup.queryset, right_lookup.queryset)
        elif isinstance(lookup, Prefetch):
            assert str(lookup.queryset.query) == right_lookup
        elif isinstance(right_lookup, Prefetch):
            assert lookup == str(right_lookup.queryset.query)
        else:
            assert lookup == right_lookup
