"""Disposable TCP forward used by remote/fleet tests, never a production proxy."""
from __future__ import annotations

import json
import os
from pathlib import Path
import select
import socket
import sys
import threading
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run():
    # The first argument contains only fixture process/port mappings, not secret values.
    fixture = json.loads(Path(sys.argv[1]).read_text())
    args = sys.argv[2:]
    if "-NT" not in args:
        sys.stdout.buffer.write(Path(fixture["key_file"]).read_bytes())
        return
    mapping = args[args.index("-L") + 1].split(":")
    local, remote = int(mapping[1]), int(mapping[3])
    remote = fixture.get("ports", {}).get(args[-1], remote)
    with open(fixture["pids"], "a") as out:
        out.write(str(os.getpid()) + "\n")
    time.sleep(fixture.get("bind_delay_s", 0))
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", local))
    listener.listen()

    def forward(client):
        try:
            with client, socket.create_connection(("127.0.0.1", remote), timeout=2) as server:
                client.setblocking(False)
                server.setblocking(False)
                peers = {client: server, server: client}
                while True:
                    readable, _, _ = select.select(list(peers), [], [], 1)
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        target = peers[source]
                        # Fixture responses are small; bounded blocking send preserves every byte.
                        target.setblocking(True)
                        target.sendall(data)
                        target.setblocking(False)
        except OSError:
            pass

    while True:
        client, _ = listener.accept()
        threading.Thread(target=forward, args=(client,), daemon=True).start()


if __name__ == "__main__":
    run()
