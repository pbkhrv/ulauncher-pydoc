from pydoc import _start_server, _url_handler
from pydoc_ext.extension import PydocExtension, iter_all_modules

if __name__ == "__main__":
    # The first module walk is slow - later ones will be much faster
    for modname in iter_all_modules():
        pass

    # Launch the pydoc HTTP server on random port
    serverthread = _start_server(_url_handler, 0)

    # Start the extension and wait for it to exit
    PydocExtension(serverthread.url).run()

    # Shutdown the pydoc HTTP server
    if serverthread.serving:
        serverthread.stop()
