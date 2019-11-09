from pydoc import _start_server, _url_handler
from pydoc_ext.extension import PydocExtension

if __name__ == "__main__":
    # Launch the pydoc HTTP server on random port
    serverthread = _start_server(_url_handler, 0)

    # Start the extension and wait for it to exit
    PydocExtension(serverthread.url).run()

    print("Shutting down serverthread...")

    # Shutdown the pydoc HTTP server
    if serverthread.serving:
        serverthread.stop()
