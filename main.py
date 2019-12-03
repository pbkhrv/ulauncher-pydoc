"""
Main entrypoint of the extension.

"""
import signal
import sys
from pydoc import _start_server, _url_handler
from pydoc_ext.extension import PydocExtension, iter_all_modules


def shutdown_and_exit(serverthread):
    """
    Gracefully shutdown the server.
    """
    if serverthread.serving:
        serverthread.stop()
    sys.exit(0)


def main():
    """
    Launch the pydoc http server and the extension
    """
    # The first module walk is slow - later ones will be much faster
    for _ in iter_all_modules():
        pass

    # Launch the pydoc HTTP server on random port
    serverthread = _start_server(_url_handler, 0)

    # Handle SIGINT gracefully
    signal.signal(signal.SIGINT, lambda sig, frame: shutdown_and_exit(serverthread))

    # Start the extension and wait for it to exit
    PydocExtension(serverthread.url).run()

    # Shutdown
    shutdown_and_exit(serverthread)

if __name__ == "__main__":
    main()
