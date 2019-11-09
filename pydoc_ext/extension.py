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

        pattern = arg_to_regex(arg)

        # Find all accessible modules
        modules = [
            modname
            for modname in iter_all_modules()
            if re.match(pattern, modname, re.IGNORECASE)
        ]

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
