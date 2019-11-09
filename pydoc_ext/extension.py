"""
pydoc search extension
"""
import sys
import re
import pkgutil
import pydoc
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
    def ignore(*args, **kwargs):
        pass

    # Built-in modules first
    for modname in sys.builtin_module_names:
        if modname != "__main__":
            yield modname

    # Then installed modules
    for _, modname, _ in pkgutil.walk_packages(onerror=ignore):
        yield modname


def filter_nested_patterns(modnames, patterns):
    name_depth = len(patterns)
    filtered = set()
    filtered_shallow = set()
    regexes = [arg_to_regex(p) for p in patterns]
    for modname in modnames:
        names = modname.split(".")
        if all(re.match(rex, name, re.IGNORECASE) for rex, name in zip(regexes, names)):
            trunc_name = ".".join(names[:name_depth])
            if len(names) == name_depth:
                filtered.add(trunc_name)
            else:
                filtered_shallow.add(trunc_name)
    return list(filtered) if filtered else list(filtered_shallow)


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
        modules = filter_nested_patterns(iter_all_modules(), patterns)

        items = []
        for modname in modules[:MAX_RESULTS_VISIBLE]:
            url = f"{extension.pydoc_server_url}{modname}.html"
            items.append(
                ExtensionResultItem(
                    icon="images/item.svg",
                    name=modname,
                    description=modname,
                    on_enter=OpenUrlAction(url),
                )
            )

        return RenderResultListAction(items)
