from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext


def assert_query_equality(left_query, right_query):
    assert str(left_query.query) == str(right_query.query)
    assert len(left_query._prefetch_related_lookups) == len(right_query._prefetch_related_lookups)
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


class _AssertNumQueriesContext(CaptureQueriesContext):
    """
        Adapted from
        https://docs.djangoproject.com/en/2.1/_modules/django/test/testcases/#_AssertNumQueriesContext
    """

    def __init__(self, num, connection):
        self.num = num
        super(self, _AssertNumQueriesContext).__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super(self, _AssertNumQueriesContext).__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self)

        assert executed == self.num, "%d queries executed, %d expected\nCaptured queries were:\n%s" % (
            executed, self.num,
            '\n'.join(
                '%d. %s' % (i, query['sql']) for i, query in enumerate(self.captured_queries, start=1)
            )
        )


def assert_num_queries(num, func=None, *args, **kwargs):
    """
        Adapted from
        https://docs.djangoproject.com/en/2.1/_modules/django/test/testcases/#TransactionTestCase.assertNumQueries
    """
    conn = connections[DEFAULT_DB_ALIAS]

    context = _AssertNumQueriesContext(num, conn)
    if func is None:
        return context

    with context:
        func(*args, **kwargs)
