import socket

import yaml

from app import z2m_config

SAMPLE = """\
homeassistant:
  enabled: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://mosquitto:1883
serial:
  port: tcp://192.168.1.50:6638
  adapter: ember
frontend:
  port: 8080
advanced:
  channel: 11
  network_key: GENERATE
"""


def test_read(tmp_path):
    p = tmp_path / "configuration.yaml"
    p.write_text(SAMPLE)
    assert z2m_config.read_gateway(p) == {"ip": "192.168.1.50", "port": 6638,
                                          "adapter": "ember", "channel": 11}


def test_read_missing(tmp_path):
    assert z2m_config.read_gateway(tmp_path / "nope.yaml")["ip"] == ""


def test_write_preserves_other_keys(tmp_path):
    p = tmp_path / "configuration.yaml"
    p.write_text(SAMPLE)
    z2m_config.write_gateway(p, "10.0.0.7", 6638, "zstack", 20)
    cfg = yaml.safe_load(p.read_text())
    assert cfg["serial"] == {"port": "tcp://10.0.0.7:6638", "adapter": "zstack"}
    assert cfg["advanced"] == {"channel": 20, "network_key": "GENERATE"}
    assert cfg["mqtt"]["server"] == "mqtt://mosquitto:1883"
    assert cfg["frontend"]["port"] == 8080
    assert z2m_config.read_gateway(p)["ip"] == "10.0.0.7"


def test_connection():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    assert z2m_config.test_connection("127.0.0.1", port)
    srv.close()
    assert not z2m_config.test_connection("127.0.0.1", port, timeout=0.5)


def test_read_malformed(tmp_path):
    p = tmp_path / "c.yaml"
    for text in ("serial: [unclosed\n  : :", "- a\n- b\n", "serial: tcp://x\nadvanced: 5\n",
                 "advanced:\n  channel: abc\n"):
        p.write_text(text, encoding="utf-8")
        assert z2m_config.read_gateway(p)["port"] == 6638
    z2m_config.write_gateway(p, "192.168.1.9", 6638, "ember", 15)
    assert z2m_config.read_gateway(p)["channel"] == 15
