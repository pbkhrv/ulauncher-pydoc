"""
Module name search logic
"""
import re
from typing import NamedTuple, Iterable, Tuple, List
from ulauncher.utils import fuzzy_search


class NestedNameSearchResultItem(NamedTuple):
    """
    Ranking scores for the "nested names" search mode
    """

    module_name: str
    name_depth: int
    name_exact_match: int
    # How well the basename matches the query, using Ulauncher's algo
    basename_match_score: float
    basename_exact_match: int
    # How well the last part of the name matches the query, using Ulauncher's algo
    leafname_match_score: float


def score_name_query_match(
    name_chunks: List[str], query_chunks: List[str], basename_query: str
) -> Tuple[float, float]:
    """
    Score how well given name matches given query using Ulauncher fuzzy search algo
    """
    # Basename match only matters if our search query includes one
    if len(query_chunks) > 1:
        basename = ".".join(name_chunks[: len(query_chunks) - 1])
        basename_match_score = fuzzy_search.get_score(basename_query, basename)
    else:
        basename_match_score = 0

    # The last part of the name match is only relevant
    # if this name has at least that many parts
    if len(name_chunks) >= len(query_chunks):
        leafname_match_score = fuzzy_search.get_score(
            query_chunks[len(query_chunks) - 1], name_chunks[len(query_chunks) - 1]
        )
    else:
        leafname_match_score = 0

    return (basename_match_score, leafname_match_score)


def search_nested(query: str, module_names: Iterable[str]) -> Tuple[bool, List[str]]:
    """
    Search all accessible module/package names, rank and sort results.

    "Nested" means sub-module and sub-package names separated by dots.
    To keep the result list noise-free, we filter out names with more levels
    of sub-names than the query has:

    >>> search_nested('htt', ['http', 'http.client', 'http.client.boo'])
    (False, ['http'])

    Returns True if the query matches some name exactly:

    >>> search_nested('http', ['http', 'http.client'])
    (True, ['http'])

    Dots separate nested names, following the Python syntax:

    >>> search_nested('http.', ['http', 'http.client', 'http.client.boo'])
    (True, ['http', 'http.client'])

    Exact query matches are ranked highest:

    >>> search_nested('http', ['http2lib', 'http'])
    (True, ['http', 'http2lib'])

    Module's "basename" exact matches are ranked higher than other fuzzy matches:

    >>> search_nested('http.se', ['http.cli', 'httplib2.boo'])
    (False, ['http.cli', 'httplib2.boo'])
    """

    query_chunks = query.lower().split(".")
    exact_match_query = query.lower().rstrip(".")
    has_exact_match = False

    # Basename means similar thing it does for files:
    # it's all the parts of the name up to the very last one.
    # Example: for a module named "mod.submod.blah", basename is "mod.submod"
    basename_query = ".".join(query_chunks[:-1])

    result_items = list()
    for name in module_names:
        if name == exact_match_query:
            has_exact_match = True
        name_chunks = name.lower().split(".")
        basename = ".".join(name_chunks[:-1])
        # Don't show names that have more parts than the search query
        if len(name_chunks) <= len(query_chunks):
            basename_match_score, leafname_match_score = score_name_query_match(
                name_chunks, query_chunks, basename_query
            )
            result_items.append(
                NestedNameSearchResultItem(
                    module_name=name,
                    name_depth=len(name_chunks),
                    name_exact_match=1 if name == exact_match_query else 0,
                    basename_match_score=basename_match_score,
                    basename_exact_match=1 if basename == basename_query else 0,
                    leafname_match_score=leafname_match_score,
                )
            )

    def sort_key(item):
        return (
            item.name_exact_match,
            item.basename_exact_match,
            item.basename_match_score,
            item.leafname_match_score,
            item.name_depth,
            item.module_name,
        )

    names = [
        res.module_name for res in sorted(result_items, key=sort_key, reverse=True)
    ]
    return (has_exact_match, names)


class FullNameSearchResultItem(NamedTuple):
    """
    Ranking scores for the "full names" search mode
    """

    module_name: str
    head_match_score: float
    tail_match_score: float
    tail_exact_contains: int


def ordered_char_list_regex(chars):
    """
    Turn a list of characters into a regex pattern that matches them all in order
    """
    return ".*?".join(re.escape(char) for char in chars)


def search_fullname(query: str, module_names: Iterable[str]) -> List[str]:
    """
    Rank and sort module names by how well they match a wildcard query.
    Nesting of the names doesn't matter.

    Treat first asterisk as a wildcard that can match any part of the name:

    >>> search_fullname('ht*error', ['http', 'http.cli.error', 'http.cli'])[0]
    'http.cli.error'

    Module names must contain all characters from the first part of the query
    to be included in the results:

    >>> search_fullname('ul*action', ['ulauncher.shared.action', 'cozmo.actions'])
    ['ulauncher.shared.action']

    Query can also start with a wildcard, in which case the first part doesn't matter:

    >>> len(search_fullname('*action', ['http.cli.action', 'boo.action']))
    2

    Dots can be used in any part of the query:

    >>> search_fullname('ht.c*t.', ['http.client.err', 'http.server.request'])
    ['http.client.err']

    Exact matches of the query's tail are scored higher, to allow for quick lookup
    of modules with known names:

    >>> search_fullname('*widg', ['ulauncher.api.itemwidget', 'wedge'])[0]
    'ulauncher.api.itemwidget'

    """

    # Split the query into 2 parts: head and tail, separated by an asterisk
    qhead, _, qtail = query.lower().partition("*")

    # Every character in the "head" part of the query
    # must be present in the given order, so we turn it into a regex pattern
    head_regex = ordered_char_list_regex(qhead) if qhead else None

    result_items = []
    for name in module_names:
        # The search is case insensitive
        name_lower = name.lower()
        if head_regex:
            # If head is present, it regex must match
            head_match = re.search(head_regex, name_lower)

            # Head and tail parts of the name don't overlap
            name_tail_idx = head_match.span()[1] if head_match else 0
            name_tail = name_lower[name_tail_idx:]
        else:
            # If the wildcard was the first character in the query,
            # then every name matches it, and we treat the whole name as "tail"
            head_match = True
            name_tail = name_lower

        if head_match:
            head_score = fuzzy_search.get_score(qhead, name_lower) if qhead else 0
            tail_score = fuzzy_search.get_score(qtail, name_tail) if qtail else 0
            result_items.append(
                FullNameSearchResultItem(
                    module_name=name,
                    head_match_score=head_score,
                    tail_match_score=tail_score,
                    tail_exact_contains=1 if qtail in name_tail else 0,
                )
            )

    def sort_key(item):
        return (
            item.tail_exact_contains,
            item.tail_match_score,
            item.head_match_score,
            item.module_name,
        )

    return [res.module_name for res in sorted(result_items, key=sort_key, reverse=True)]
