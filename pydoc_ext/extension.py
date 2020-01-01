"""
Show documentation for installed Python packages and modules

Displays documentation in the browser using Python pydoc's built-in HTTP server
"""
import sys
import pkgutil
from typing import Iterable, List, Optional
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
from .module_search import search_nested, search_fullname


MAX_RESULTS_VISIBLE = 9


def get_python_version() -> str:
    """
    Python version string
    """
    return "{} [{}, {}]".format(
        platform.python_version(),
        platform.python_build()[0],
        platform.python_compiler(),
    )


def iter_all_module_names() -> Iterable[str]:
    """
    Enumerate all accessible Python modules.
    """

    def ignore(_):
        pass

    # Built-in modules first
    for name in sys.builtin_module_names:
        if name != "__main__":
            yield name

    # Then installed modules
    for _, name, _ in pkgutil.walk_packages(onerror=ignore):
        yield name


def count_top_level_module_names() -> int:
    """
    Count all top-level (without submodules and subpackages) module and package names
    """
    cnt = 0
    for name in iter_all_module_names():
        if "." not in name:
            cnt += 1
    return cnt


@lru_cache(maxsize=128)
def get_module_description(module_name: str, max_lines=5) -> str:
    """
    Attempt to get the module docstring and use it as description for search results
    """
    desc = ""
    try:
        doc = ""
        name_chunks = module_name.split(".")
        if len(name_chunks) > 1:
            tail = name_chunks[-1]
            mod = __import__(module_name)
            doc = getattr(mod, tail).__doc__
        if not doc:
            doc = __import__(module_name).__doc__ or ""
        lines = doc.splitlines()[:max_lines]
        for line in lines:
            if not line and desc:
                return desc
            desc += "\n" if desc else ""
            desc += line
    except Exception:  # pylint: disable=broad-except
        pass
    return desc


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
                    f"{count_top_level_module_names()}"
                ),
                description="Please enter search query to begin...",
                on_enter=DoNothingAction(),
                highlightable=False,
            ),
        ]
    )


def get_module_source_path(mod_query: str) -> Optional[str]:
    """
    Get the path to the module Python file
    """
    name = mod_query.rstrip(".")
    module = sys.modules.get(name, None)
    return module.__file__ if module else None


class PydocExtension(Extension):
    """
    Main extension class, only exists to coordinate others
    """

    def __init__(self, pydoc_server_url):
        super(PydocExtension, self).__init__()
        self.pydoc_server_url = pydoc_server_url
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


def items_open_source_file(mod_query: str) -> List[ResultItem]:
    """
    Find corresponding source file and show an "Open ....py" result item
    """
    mod_path = get_module_source_path(mod_query)
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
        self, event: KeywordQueryEvent, extension: Extension
    ) -> BaseAction:
        """
        Handle keyword query event.
        """
        kw = event.get_keyword()
        arg = event.get_argument()
        if not arg:
            return show_empty_query_results()

        # Find all accessible modules that match the query
        if "*" in arg:
            has_exact_match = False
            names = search_fullname(arg, iter_all_module_names())
        else:
            has_exact_match, names = search_nested(arg, iter_all_module_names())

        items: List[ResultItem] = []

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
