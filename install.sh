#!/usr/bin/env bash
# medMonitor — installazione / aggiornamento su Fedora con Podman rootless + Quadlet.
#
# Uso:   ./install.sh            (da utente normale, NON root)
# Rilanciarlo è sicuro: aggiorna l'immagine, rigenera i servizi, cambia porta se richiesto.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$REPO_DIR/.env"
DATA_DIR="$HOME/medmonitor-data"
QUADLET_DIR="$HOME/.config/containers/systemd"
Z2M_FRONTEND_PORT=8080

say()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[32mOK\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31mERRORE:\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. Prerequisiti ---------------------------------------------------------
say "Controllo prerequisiti"
[[ $EUID -ne 0 ]] || die "non lanciare come root: usa il tuo utente normale (sudo verrà chiesto solo quando serve)."
grep -qi fedora /etc/os-release 2>/dev/null || die "questo script è pensato per Fedora."
command -v podman >/dev/null || die "podman non installato. Esegui: sudo dnf install -y podman"
command -v curl >/dev/null || die "curl non installato. Esegui: sudo dnf install -y curl"
ok "Fedora, podman $(podman --version | awk '{print $3}')"

# --- 2. Parametri ------------------------------------------------------------
env_get() { [[ -f "$ENV_FILE" ]] && sed -n "s/^$1=//p" "$ENV_FILE" | tail -n1 || true; }

OLD_PORT="$(env_get UI_PORT)"
OLD_GATEWAY="$(env_get GATEWAY_IP)"
OLD_ADMIN="$(env_get ADMIN_PASSWORD)"
SECRET_KEY="$(env_get SECRET_KEY)"
[[ -n "$SECRET_KEY" ]] || SECRET_KEY="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"

port_busy() { ss -ltnH "sport = :$1" 2>/dev/null | grep -q .; }

say "Configurazione (premi Invio per accettare il valore tra parentesi)"
while true; do
    read -rp "    Porta della UI web [${OLD_PORT:-8090}]: " UI_PORT
    UI_PORT="${UI_PORT:-${OLD_PORT:-8090}}"
    if ! [[ "$UI_PORT" =~ ^[0-9]+$ ]] || (( UI_PORT < 1024 || UI_PORT > 65535 )); then
        echo "    Porta non valida: usa un numero tra 1024 e 65535."; continue
    fi
    if (( UI_PORT == 8000 )); then echo "    La porta 8000 è riservata: scegline un'altra."; continue; fi
    if (( UI_PORT == Z2M_FRONTEND_PORT || UI_PORT == 1883 )); then
        echo "    Porta usata da zigbee2mqtt/mosquitto: scegline un'altra."; continue
    fi
    # La porta occupata dal medmonitor già in esecuzione va bene: verrà riavviato.
    if port_busy "$UI_PORT" && ! { [[ "$UI_PORT" == "$OLD_PORT" ]] && systemctl --user -q is-active medmonitor.service; }; then
        echo "    La porta $UI_PORT è già in uso da un altro programma: scegline un'altra."; continue
    fi
    break
done

while true; do
    read -rp "    IP statico del gateway Zigbee (SONOFF Dongle-M) [${OLD_GATEWAY}]: " GATEWAY_IP
    GATEWAY_IP="${GATEWAY_IP:-$OLD_GATEWAY}"
    [[ "$GATEWAY_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && break
    echo "    Indirizzo non valido (esempio: 192.168.1.50)."
done

if [[ -n "$OLD_ADMIN" ]]; then
    ADMIN_PASSWORD="$OLD_ADMIN"   # già installato: la password si cambia dalla UI
else
    while true; do
        read -rsp "    Password di amministrazione (min. 6 caratteri): " ADMIN_PASSWORD; echo
        (( ${#ADMIN_PASSWORD} >= 6 )) || { echo "    Troppo corta."; continue; }
        read -rsp "    Ripeti la password: " again; echo
        [[ "$ADMIN_PASSWORD" == "$again" ]] && break
        echo "    Le password non coincidono."
    done
fi

# --- 3. Cartelle, .env, configurazione zigbee2mqtt ---------------------------
say "Preparo dati e configurazione"
mkdir -p "$DATA_DIR/app" "$DATA_DIR/z2m" "$QUADLET_DIR"

umask 077
cat > "$ENV_FILE" <<EOF
UI_PORT=$UI_PORT
GATEWAY_IP=$GATEWAY_IP
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
TZ=Europe/Rome
EOF
umask 022
ok "$ENV_FILE"

Z2M_CONF="$DATA_DIR/z2m/configuration.yaml"
if [[ ! -f "$Z2M_CONF" ]]; then
    cat > "$Z2M_CONF" <<EOF
homeassistant:
  enabled: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://mosquitto:1883
serial:
  port: tcp://$GATEWAY_IP:6638
  adapter: ember
frontend:
  enabled: true
  port: $Z2M_FRONTEND_PORT
advanced:
  channel: 11
  network_key: GENERATE
  pan_id: GENERATE
  ext_pan_id: GENERATE
  last_seen: ISO_8601
  log_level: info
EOF
    ok "creato $Z2M_CONF"
elif [[ -n "$OLD_GATEWAY" && "$GATEWAY_IP" != "$OLD_GATEWAY" ]]; then
    sed -i -E "s#tcp://[0-9.]+:([0-9]+)#tcp://$GATEWAY_IP:\1#" "$Z2M_CONF"
    ok "aggiornato IP gateway in $Z2M_CONF"
else
    ok "$Z2M_CONF già presente (non modificato)"
fi

# --- 4. Immagine -------------------------------------------------------------
say "Costruisco l'immagine medmonitor (può richiedere qualche minuto la prima volta)"
podman build -t localhost/medmonitor:latest -f "$REPO_DIR/Containerfile" "$REPO_DIR"
podman pull -q docker.io/library/eclipse-mosquitto:2 >/dev/null
podman pull -q docker.io/koenkk/zigbee2mqtt:2 >/dev/null
ok "immagini pronte"

# --- 5. Servizi Quadlet ------------------------------------------------------
say "Genero i servizi systemd (Quadlet) in $QUADLET_DIR"

cat > "$QUADLET_DIR/medmonitor.network" <<EOF
[Network]
NetworkName=medmonitor
EOF

cat > "$QUADLET_DIR/mosquitto.container" <<EOF
[Unit]
Description=medMonitor - broker MQTT

[Container]
ContainerName=mosquitto
Image=docker.io/library/eclipse-mosquitto:2
Network=medmonitor.network
Volume=$REPO_DIR/deploy/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro,z
Volume=medmonitor-mosquitto:/mosquitto/data

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

cat > "$QUADLET_DIR/zigbee2mqtt.container" <<EOF
[Unit]
Description=medMonitor - zigbee2mqtt (gateway $GATEWAY_IP)
Wants=mosquitto.service
After=mosquitto.service

[Container]
ContainerName=zigbee2mqtt
Image=docker.io/koenkk/zigbee2mqtt:2
Network=medmonitor.network
Environment=TZ=Europe/Rome
Volume=$DATA_DIR/z2m:/app/data:z
PublishPort=127.0.0.1:$Z2M_FRONTEND_PORT:$Z2M_FRONTEND_PORT

[Service]
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

cat > "$QUADLET_DIR/medmonitor.container" <<EOF
[Unit]
Description=medMonitor - monitoraggio temperature (porta $UI_PORT)
Wants=mosquitto.service zigbee2mqtt.service
After=mosquitto.service

[Container]
ContainerName=medmonitor
Image=localhost/medmonitor:latest
Network=medmonitor.network
EnvironmentFile=$ENV_FILE
Environment=MQTT_HOST=mosquitto MQTT_PORT=1883 DATA_DIR=/data Z2M_CONFIG=/z2m/configuration.yaml
Volume=$DATA_DIR/app:/data:z
Volume=$DATA_DIR/z2m:/z2m:z
PublishPort=$UI_PORT:$UI_PORT

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
ok "medmonitor.network, mosquitto, zigbee2mqtt, medmonitor"

# --- 6. Avvio ----------------------------------------------------------------
say "Avvio i servizi"
systemctl --user daemon-reload
systemctl --user restart medmonitor-network.service mosquitto.service zigbee2mqtt.service medmonitor.service
ok "servizi avviati"

say "Abilito l'avvio automatico al boot (richiede sudo)"
sudo loginctl enable-linger "$USER"
ok "linger attivo per $USER"

if command -v firewall-cmd >/dev/null && sudo firewall-cmd --state >/dev/null 2>&1; then
    say "Apro la porta $UI_PORT nel firewall (richiede sudo)"
    if [[ -n "$OLD_PORT" && "$OLD_PORT" != "$UI_PORT" ]]; then
        sudo firewall-cmd -q --permanent --remove-port="$OLD_PORT/tcp" || true
        ok "chiusa la vecchia porta $OLD_PORT"
    fi
    sudo firewall-cmd -q --permanent --add-port="$UI_PORT/tcp"
    sudo firewall-cmd -q --reload
    ok "porta $UI_PORT/tcp aperta"
else
    ok "firewalld non attivo: nessuna regola da aggiungere"
fi

# --- 7. Verifica -------------------------------------------------------------
say "Verifica finale"
for _ in $(seq 1 30); do
    if HEALTH="$(curl -fs "http://localhost:$UI_PORT/health")"; then
        ok "medmonitor risponde: $HEALTH"
        IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
        printf '\n\033[1;32mInstallazione completata.\033[0m\n'
        printf '  UI medMonitor:   http://%s:%s\n' "${IP:-localhost}" "$UI_PORT"
        printf '  UI zigbee2mqtt:  http://localhost:%s (solo dal server; dal PC: ssh -L %s:localhost:%s utente@server)\n' "$Z2M_FRONTEND_PORT" "$Z2M_FRONTEND_PORT" "$Z2M_FRONTEND_PORT"
        printf '  Log:             journalctl --user -u medmonitor -f\n\n'
        exit 0
    fi
    sleep 2
done
die "medmonitor non risponde su http://localhost:$UI_PORT/health. Controlla: systemctl --user status medmonitor; journalctl --user -u medmonitor -n 50"
