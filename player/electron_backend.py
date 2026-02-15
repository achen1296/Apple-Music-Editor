import sys
from collections.abc import Callable
from urllib.parse import ParseResultBytes, urlparse

import zmq

try:
    from library_musicdb import Library
except ImportError:
    sys.path.append("..")
    from library_musicdb import Library


def trackfile(parsed_url: ParseResultBytes):
    # todo use track ID
    return parsed_url.path.removeprefix(b"/")


HANDLERS: dict[str, Callable[[ParseResultBytes], bytes]] = {
    func.__name__: func
    for func in [
        trackfile
    ]
}


def handle_request(url: bytes) -> bytes:
    parsed_url = urlparse(url)

    if not parsed_url.hostname:
        raise Exception("no hostname")
    try:
        handler = HANDLERS[parsed_url.hostname.decode()]
    except KeyError:
        raise Exception(f"unknown hostname {parsed_url.hostname}")

    return handler(parsed_url)


def main(port: int):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")

    with open("backend_log.txt", "wb") as log_file:  # for debugging
        while True:
            url = socket.recv()

            log_file.write(b"recv: ")
            log_file.write(url)
            log_file.write(b"\n")

            try:
                response = handle_request(url)
            except Exception as x:
                response = "; ".join(x.args).encode()

            log_file.write(b"send: ")
            log_file.write(response)
            log_file.write(b"\n\n")

            socket.send(response)

            log_file.flush()


if __name__ == "__main__":
    port = int(sys.argv[1])
    main(port)
