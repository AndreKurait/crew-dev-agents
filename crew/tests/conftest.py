"""Keep every unit test offline, including dependency telemetry."""
import os
import socket

import pytest

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests must not contact GitHub, AWS, or another network service")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
