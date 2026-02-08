import sys
import zmq


def main(port: int):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")

    while True:
        message = socket.recv()
        socket.send(b"test.mp3")


if __name__ == "__main__":
    port = int(sys.argv[1])
    main(port)
