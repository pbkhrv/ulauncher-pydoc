"""
Show documentation for installed Python packages and modules

Displays documentation in the browser using Python pydoc's built-in HTTP server
"""
import sys
import pkgutil
from typing import NamedTuple
from functools import lru_cache
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.utils import fuzzy_search


MAX_RESULTS_VISIBLE = 9


class PydocExtension(Extension):
    """
    Main extension class, only exists to coordinate others
    """

    def __init__(self, pydoc_server_url):
        super(PydocExtension, self).__init__()
        self.pydoc_server_url = pydoc_server_url
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


def iter_all_modules():
    """
    Enumerate all accessible Python modules.
    """

    def ignore(_):
        pass

    # Built-in modules first
    for modname in sys.builtin_module_names:
        if modname != "__main__":
            yield modname

    # Then installed modules
    for _, modname, _ in pkgutil.walk_packages(onerror=ignore):
        yield modname


class SearchResultItem(NamedTuple):
    """
    Module info and match scores.
    """

    name: str
    pydoc_url: str
    name_depth: int
    # How well the basename matches the query, using Ulauncher's algo
    basename_match_score: float
    basename_exact_match: int
    # How well the last part of the name matches the query, using Ulauncher's algo
    leafname_match_score: float


def score_modname_query_match(modname_chunks, query_chunks, basename_query):
    """
    Score how well given modname matches given query using Ulauncher fuzzy search algo
    """
    # Basename match only matters if our search query includes one
    if len(query_chunks) > 1:
        basename = ".".join(modname_chunks[: len(query_chunks) - 1])
        basename_match_score = fuzzy_search.get_score(basename_query, basename)
    else:
        basename_match_score = 0

    # The last part of the name match is only relevant
    # if this modname has at least that many parts
    if len(modname_chunks) >= len(query_chunks):
        leafname_match_score = fuzzy_search.get_score(
            query_chunks[len(query_chunks) - 1], modname_chunks[len(query_chunks) - 1]
        )
    else:
        leafname_match_score = 0

    return (basename_match_score, leafname_match_score)


def result_sort_key(result_item):
    """
    Ranking of modname matches.
    """

    return (
        result_item.basename_exact_match,
        result_item.basename_match_score,
        result_item.leafname_match_score,
        result_item.name_depth,
        result_item.name,
    )


def search_modules(query, all_modnames):
    """
    Match all accessible modules against the query. Rank and sort results.
    """

    query_chunks = query.lower().split(".")

    # Basename means similar thing it does for files:
    # it's all the parts of the name up to the very last one.
    # Example: for a module named "mod.submod.blah", basename is "mod.submod"
    basename_query = ".".join(query_chunks[:-1])

    result_items = list()
    for modname in all_modnames:
        modname_chunks = modname.lower().split(".")
        basename = ".".join(modname_chunks[:-1])
        # Don't show modnames that have more parts than the search query
        if len(modname_chunks) <= len(query_chunks):
            basename_match_score, leafname_match_score = score_modname_query_match(
                modname_chunks, query_chunks, basename_query
            )
            result_items.append(
                SearchResultItem(
                    name=modname,
                    pydoc_url=f"{modname}.html",
                    name_depth=len(modname_chunks),
                    basename_match_score=basename_match_score,
                    basename_exact_match=1 if basename == basename_query else 0,
                    leafname_match_score=leafname_match_score,
                )
            )

    return sorted(result_items, key=result_sort_key, reverse=True)


def count_top_level_modnames():
    """
    Count all top-level (without submodules and subpackages) modnames
    """
    cnt = 0
    for modname in iter_all_modules():
        if "." not in modname:
            cnt += 1
    return cnt


@lru_cache(maxsize=128)
def get_module_description(modname, max_lines=5):
    """
    Attempt to get the module docstring and use it as description for search results
    """
    doc = ""
    name_chunks = modname.split(".")
    if len(name_chunks) > 1:
        tail = name_chunks[-1]
        mod = __import__(modname)
        doc = getattr(mod, tail).__doc__
    if not doc:
        doc = __import__(modname).__doc__ or ""
    lines = doc.splitlines()[:max_lines]
    desc = ""
    for line in lines:
        if not line and desc:
            return desc
        desc += "\n" if desc else ""
        desc += line
    return desc


# pylint: disable=too-few-public-methods
class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class manages user input """

    def on_event(self, event, extension):
        """
        Handle keyword query event.
        """
        # assuming only one ulauncher keyword
        arg = event.get_argument()
        if not arg:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon="images/enter-query.svg",
                        name="Please enter search query...",
                        description=(
                            f"Found {count_top_level_modnames()} "
                            "top level packages and modules"
                        ),
                        on_enter=DoNothingAction(),
                    )
                ]
            )

        # Find all accessible modules that match the query
        results = search_modules(arg, iter_all_modules())

        items = []
        for res in results[:MAX_RESULTS_VISIBLE]:
            url = f"{extension.pydoc_server_url}{res.pydoc_url}"
            items.append(
                ExtensionResultItem(
                    icon="images/python-module.svg",
                    name=res.name,
                    description=get_module_description(res.name),
                    on_enter=OpenUrlAction(url),
                )
            )
        if len(results) > MAX_RESULTS_VISIBLE:
            count_not_shown = len(results) - MAX_RESULTS_VISIBLE
            items.append(
                ExtensionSmallResultItem(
                    icon="images/empty.png",
                    name=f"{count_not_shown} more results not shown..",
                    on_enter=DoNothingAction(),
                )
            )

        return RenderResultListAction(items)
