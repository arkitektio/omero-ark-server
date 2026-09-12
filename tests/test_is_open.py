"""Unit tests for isOpen() — the TCP reachability probe used by ensure_omero_user.

No OMERO server needed: we bind a throwaway local socket to exercise both paths.
"""

import socket

from bridge.mutations.omero_user import isOpen


def test_open_port_returns_true():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert isOpen("127.0.0.1", port) is True
    finally:
        server.close()


def test_closed_port_returns_false():
    # Bind to grab a free port, then close it so nothing is listening.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    assert isOpen("127.0.0.1", port, timeout=0.5) is False


def test_port_accepts_string():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        # isOpen does int(port), so a string port must work too.
        assert isOpen("127.0.0.1", str(port)) is True
    finally:
        server.close()
