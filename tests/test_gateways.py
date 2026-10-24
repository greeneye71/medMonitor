import json

import app
from app import gateways
from app.gateways import Gateway


def write(tmp_path, data):
    p = tmp_path / "gateways.json"
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def test_load_missing_fallback(tmp_path):
    assert gateways.load(tmp_path, "/z2m/configuration.yaml") == [
        Gateway(1, "Gateway 1", "zigbee2mqtt", "/z2m/configuration.yaml", 8080)]


def test_load_registry(tmp_path):
    write(tmp_path, {"gateways": [
        {"id": 2, "name": "Magazzino", "base_topic": "zigbee2mqtt_2",
         "config": "/z2m-2/configuration.yaml", "frontend_port": 8081},
        {"id": 1, "name": "Laboratorio", "base_topic": "zigbee2mqtt",
         "config": "/z2m/configuration.yaml", "frontend_port": 8080},
    ]})
    gws = gateways.load(tmp_path, "/fallback.yaml")
    assert [g.id for g in gws] == [1, 2]
    assert gws[1] == Gateway(2, "Magazzino", "zigbee2mqtt_2", "/z2m-2/configuration.yaml", 8081)
    assert gateways.by_id(gws, 2).name == "Magazzino"
    assert gateways.by_id(gws, 9) is None


def test_load_invalid_falls_back(tmp_path):
    fallback = [Gateway(1, "Gateway 1", "zigbee2mqtt", "/f.yaml", 8080)]
    for bad in ["not json{", {}, {"gateways": []}, [1, 2],
                {"gateways": [{"id": 1, "name": "A", "base_topic": "a", "config": "x"},
                              {"id": 1, "name": "B", "base_topic": "b", "config": "y"}]},
                {"gateways": [{"id": 1, "name": "A", "config": "x"}]},
                {"gateways": [{"id": "uno", "name": "A", "base_topic": "a", "config": "x"}]}]:
        write(tmp_path, bad)
        assert gateways.load(tmp_path, "/f.yaml") == fallback, bad


def test_rename_atomic(tmp_path):
    write(tmp_path, {"gateways": [
        {"id": 1, "name": "Gateway 1", "base_topic": "zigbee2mqtt", "config": "/z2m/c.yaml"},
        {"id": 2, "name": "Vecchio", "base_topic": "zigbee2mqtt_2", "config": "/z2m-2/c.yaml",
         "frontend_port": 8081}]})
    gateways.rename(tmp_path, 2, "Ambulatorio")
    gws = gateways.load(tmp_path, "/f.yaml")
    assert gws[1] == Gateway(2, "Ambulatorio", "zigbee2mqtt_2", "/z2m-2/c.yaml", 8081)
    assert gws[0].name == "Gateway 1"
    assert [p.name for p in tmp_path.iterdir()] == ["gateways.json"]
    try:
        gateways.rename(tmp_path, 7, "X")
        assert False, "KeyError atteso"
    except KeyError:
        pass


def test_version():
    assert app.__version__ == "2.1.0"
