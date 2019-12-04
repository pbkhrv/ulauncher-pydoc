"""
Show documentation for installed Python packages and modules

Displays documentation in the browser using Python pydoc's built-in HTTP server
"""
import sys
import pkgutil
from typing import NamedTuple, Iterable, Tuple, List, Type, Optional
from functools import lru_cache
import platform
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ResultItem import ResultItem
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.BaseAction import BaseAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
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


def iter_all_modules() -> Iterable[str]:
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


class FullNameSearchResultItem(NamedTuple):
    """
    Ranking scores for the "full names" search mode
    """

    module_name: str
    head_match_score: float
    tail_match_score: float


def score_modname_query_match(
    modname_chunks: List[str], query_chunks: List[str], basename_query: str
) -> Tuple[float, float]:
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


def search_modules_nested(
    query: str, all_modnames: Iterable[str]
) -> Tuple[bool, List[str]]:
    """
    Search all accessible module/package names, rank and sort results.

    "Nested" means sub-module and sub-package names separated by dots.
    To keep the result list noise-free, we filter out names with more levels
    of sub-names than the query has:

    >>> search_modules_nested('htt', ['http', 'http.client', 'http.client.boo'])
    (False, ['http'])

    Returns True if the query matches some name exactly:

    >>> search_modules_nested('http', ['http', 'http.client'])
    (True, ['http'])

    Dots separate nested names, following the Python syntax:

    >>> search_modules_nested('http.', ['http', 'http.client', 'http.client.boo'])
    (True, ['http', 'http.client'])

    Exact query matches are ranked highest:

    >>> search_modules_nested('http', ['http2lib', 'http'])
    (True, ['http', 'http2lib'])

    Module's "basename" exact matches are ranked higher than other fuzzy matches:

    >>> search_modules_nested('http.se', ['http.cli', 'httplib2.boo'])
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
    for modname in all_modnames:
        if modname == exact_match_query:
            has_exact_match = True
        modname_chunks = modname.lower().split(".")
        basename = ".".join(modname_chunks[:-1])
        # Don't show modnames that have more parts than the search query
        if len(modname_chunks) <= len(query_chunks):
            basename_match_score, leafname_match_score = score_modname_query_match(
                modname_chunks, query_chunks, basename_query
            )
            result_items.append(
                NestedNameSearchResultItem(
                    module_name=modname,
                    name_depth=len(modname_chunks),
                    name_exact_match=1 if modname == exact_match_query else 0,
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


# def search_modules_full(query: str, all_modnames: Iterable[str]) -> List[str]:
#    """
#    Search full module names, not restricted by nesting level of the query.
#    Rank and sort the results.
#    """


def count_top_level_modnames() -> int:
    """
    Count all top-level (without submodules and subpackages) modnames
    """
    cnt = 0
    for modname in iter_all_modules():
        if "." not in modname:
            cnt += 1
    return cnt


@lru_cache(maxsize=128)
def get_module_description(modname: str, max_lines=5) -> str:
    """
    Attempt to get the module docstring and use it as description for search results
    """
    desc = ""
    try:
        doc = ""
        name_chunks = modname.split(".")
        if len(name_chunks) > 1:
            tail = name_chunks[-1]
            mod = __import__(modname)
            doc = getattr(mod, tail).__doc__
        if not doc:
            doc = __import__(modname).__doc__ or ""
        lines = doc.splitlines()[:max_lines]
        for line in lines:
            if not line and desc:
                return desc
            desc += "\n" if desc else ""
            desc += line
    except Exception:  # pylint: disable=broad-except
        pass
    return desc


def get_python_version() -> str:
    """
    Python version string
    """
    return "{} [{}, {}]".format(
        platform.python_version(),
        platform.python_build()[0],
        platform.python_compiler(),
    )


def show_empty_query_results() -> RenderResultListAction:
    """
    Show info about Python and installed packages and modules
    """
    return RenderResultListAction(
        [
            ExtensionResultItem(
                icon="images/python.svg",
                name=f"Python version: {get_python_version()}",
                on_enter=DoNothingAction(),
                highlightable=False,
            ),
            ExtensionResultItem(
                icon="images/enter-query.svg",
                name=(
                    "Top level packages and modules found: "
                    f"{count_top_level_modnames()}"
                ),
                description="Please enter search query to begin...",
                on_enter=DoNothingAction(),
                highlightable=False,
            ),
        ]
    )


def get_mod_source_path(mod_query: str) -> Optional[str]:
    """
    Get the path to the module Python file
    """
    modname = mod_query.rstrip(".")
    module = sys.modules.get(modname, None)
    return module.__file__ if module else None


def items_open_source_file(mod_query: str) -> List[Type[ResultItem]]:
    """
    Find corresponding source file and show an "Open ....py" result item
    """
    mod_path = get_mod_source_path(mod_query)
    if mod_path:
        return [
            ExtensionSmallResultItem(
                icon="images/enter-query.svg",
                name=f"Open {mod_path}",
                on_enter=OpenAction(mod_path),
                highlightable=False,
            )
        ]
    return []


# pylint: disable=too-few-public-methods
class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class manages user input """

    def on_event(
        self, event: KeywordQueryEvent, extension: Type[Extension]
    ) -> Type[BaseAction]:
        """
        Handle keyword query event.
        """
        # assuming only one ulauncher keyword
        kw = event.get_keyword()
        arg = event.get_argument()
        if not arg:
            return show_empty_query_results()

        # Find all accessible modules that match the query
        has_exact_match, names = search_modules_nested(arg, iter_all_modules())

        items = []

        # Offer to open the matching module source file in text editor
        if has_exact_match:
            items += items_open_source_file(arg)

        for name in names[:MAX_RESULTS_VISIBLE]:
            url = f"{extension.pydoc_server_url}{name}.html"
            items.append(
                ExtensionResultItem(
                    icon="images/python-module.svg",
                    name=name,
                    description=get_module_description(name),
                    on_enter=OpenUrlAction(url),
                    on_alt_enter=SetUserQueryAction(f"{kw} {name}."),
                )
            )

        if len(names) > MAX_RESULTS_VISIBLE:
            count_not_shown = len(names) - MAX_RESULTS_VISIBLE
            items.append(
                ExtensionSmallResultItem(
                    icon="images/empty.png",
                    name=f"{count_not_shown} more results not shown..",
                    on_enter=DoNothingAction(),
                    highlightable=False,
                )
            )

        return RenderResultListAction(items)
