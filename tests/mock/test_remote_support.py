"""Disposable TCP forward used by remote/fleet tests, never a production proxy."""
from __future__ import annotations

import json
import os
from pathlib import Path
import random
import select
import socket
import sys
import threading
import time
import unittest


# bind(0) draws from the kernel's ephemeral range, so a port released by the caller can go to the next bind(0) or to
# any outgoing connection before the fixture's own process binds it. The default ephemeral ranges start at 32768
# (Linux) and 49152 (macOS, Windows); fixture ports come from below them, once per process.
FIXTURE_PORTS = range(20000, 30000)
_issued: set[int] = set()
_issued_lock = threading.Lock()


def free_port():
    """A loopback port free now, outside the ephemeral range and never issued twice in this process."""
    with _issued_lock:
        start = random.randrange(len(FIXTURE_PORTS))
        for offset in range(len(FIXTURE_PORTS)):
            port = FIXTURE_PORTS[(start + offset) % len(FIXTURE_PORTS)]
            if port in _issued:
                continue
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", port))
                except OSError:
                    continue
            _issued.add(port)
            return port
    raise RuntimeError("no free loopback fixture port")


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


def ephemeral_range():
    """The kernel's automatic (ephemeral) port range on this host, or None where it is not readable."""
    linux = Path("/proc/sys/net/ipv4/ip_local_port_range")
    if linux.is_file():
        first, last = map(int, linux.read_text().split())
        return first, last
    if sys.platform == "darwin":
        import subprocess
        out = subprocess.run(["sysctl", "-n", "net.inet.ip.portrange.first", "net.inet.ip.portrange.last"],
                             capture_output=True, text=True, check=True).stdout.split()
        return int(out[0]), int(out[1])
    return None


class FixturePortTests(unittest.TestCase):
    def test_fixture_ports_avoid_the_kernels_automatic_range_and_never_repeat(self):
        # CI 2026-11-03: a port released by bind(0) was claimed by another socket before the fake SSH forward bound
        # it, so RemoteSession refused it as "client tunnel port is occupied". Ports the kernel never assigns on its
        # own, issued once per process, cannot be claimed that way.
        automatic = ephemeral_range()
        if automatic is None:
            self.skipTest("this host's ephemeral port range is not readable")
        ports = [free_port() for _ in range(64)]
        self.assertEqual(len(ports), len(set(ports)))
        self.assertEqual([], [port for port in ports if automatic[0] <= port <= automatic[1]])



if __name__ == "__main__":
    run()
