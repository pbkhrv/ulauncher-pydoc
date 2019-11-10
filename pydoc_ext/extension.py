"""
pydoc search extension
"""
import sys
import re
import pkgutil
import pydoc
from typing import NamedTuple
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


MAX_RESULTS_VISIBLE = 10


class PydocExtension(Extension):
    """
    Main extension class, only exists to coordinate others
    """

    def __init__(self, pydoc_server_url):
        super(PydocExtension, self).__init__()
        self.pydoc_server_url = pydoc_server_url
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


def arg_to_regex(arg):
    arg = arg.strip(" ")
    args = re.split(r"\s+", arg)
    return ".*?" + ".+?".join(args) + ".*"


def iter_all_modules():
    """
    Enumerate all accessible Python modules
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
    Python nuggets.
    """

    name: str
    description: str
    pydoc_url: str
    name_depth: int
    basename_exact_match: bool


def filter_modnames_by_patterns(modnames, patterns):
    """
    Match given module names against the nested search pattern.
    Return meta data about every match.
    """
    # How many levels deep we are searching:
    # "apt" is 1 level deep
    # "mod.submod.whatever" is 3 levels deep
    search_depth = len(patterns)

    # Turn each pattern into a regex that we can match
    regexes = [arg_to_regex(p) for p in patterns]

    # Basename is the same concept as in file paths:
    # If module is named "mod.submod.whatever" then its basename is "mod.submod"
    basename_pattern_exact = ".".join(patterns[:-1])
    for modname in modnames:
        name_chunks = modname.split(".")
        basename = ".".join(name_chunks[: search_depth - 1]).lower()
        basename_exact_match = search_depth > 1 and basename == basename_pattern_exact
        if all(
            re.match(rex, chunk, re.IGNORECASE)
            for rex, chunk in zip(regexes, name_chunks)
        ):
            yield SearchResultItem(
                name=modname,
                description=modname,
                pydoc_url=f"{modname}.html",
                name_depth=len(name_chunks),
                basename_exact_match=basename_exact_match,
            )


def result_sort_key(item):
    return (item.basename_exact_match, item.name_depth, item.name)


def search_modules(patterns):
    search_depth = len(patterns)
    result_items = [
        item
        for item in filter_modnames_by_patterns(iter_all_modules(), patterns)
        if item.name_depth <= search_depth
    ]
    return sorted(result_items, key=result_sort_key, reverse=True)


# pylint: disable=too-few-public-methods
class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class manages user input """

    def __init__(self):
        super(KeywordQueryEventListener, self).__init__()

    def on_event(self, event, extension):
        """
        Handle keyword query event.
        """
        # assuming only one ulauncher keyword
        arg = event.get_argument()
        if not arg:
            return DoNothingAction()

        patterns = arg.split(".")

        # Find all accessible modules
        results = search_modules(patterns)

        items = []
        for res in results[:MAX_RESULTS_VISIBLE]:
            url = f"{extension.pydoc_server_url}{res.pydoc_url}"
            items.append(
                ExtensionResultItem(
                    icon="images/item.svg",
                    name=res.name,
                    description=res.description,
                    on_enter=OpenUrlAction(url),
                )
            )

        return RenderResultListAction(items)
