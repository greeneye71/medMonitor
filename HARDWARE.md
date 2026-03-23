# Hardware consigliato

## Gateway ZigBee

Poiché l'app gira su VM, si usa un gateway con connettività
Wi-Fi o Ethernet invece di un dongle USB.

### Sonoff ZBBridge Pro (consigliato) ~22 €
- Wi-Fi 2.4GHz, firmware nativo o Tasmota
- MQTT nativo, ZigBee 3.0, chip EFR32MG21

### SLZB-06 ~35 € (Ethernet, più stabile)
- Ethernet, open source, compatibile Zigbee2MQTT

## Sensori temperatura

### Frigorifero (0°C / +30°C)
- Sonoff SNZB-02D: ~14 €, -20/+60°C, ±0.5°C, display LCD
- MOES ZSS-ZK-THL: ~12 €, -10/+50°C, ±0.3°C

### Freezer (-30°C / 0°C)
- Aqara Temperature T1: ~16 €, -40/+85°C, ±0.3°C  ← consigliato
- Sonoff SNZB-02P: ~12 €, -40/+85°C, IP65

## Costo totale configurazione base

| Componente | Costo |
|---|---|
| Gateway Sonoff ZBBridge Pro | ~22 € |
| Sensore frigorifero (SNZB-02D) | ~14 € |
| Sensore freezer (Aqara T1) | ~16 € |
| **Totale** | **~52 €** |

## Requisiti sistema

### Windows (nativo)

| Risorsa | Minimo | Consigliato |
|---|---|---|
| CPU | 2 core | 4 core |
| RAM | 4 GB | 8 GB |
| Disco | 10 GB | 30 GB |
| OS | Windows 10/11 | Windows 11 Pro |
| Python | 3.11+ | 3.11+ |
| Mosquitto | 2.0+ | 2.0+ |

### VM Linux / Docker

| Risorsa | Minimo | Consigliato |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB | 50 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |