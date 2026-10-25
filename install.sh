#!/usr/bin/env bash
# medMonitor — installazione / aggiornamento su Fedora con Podman rootless + Quadlet.
#
# Uso:   ./install.sh            (da utente normale, NON root)
# Rilanciarlo è sicuro: aggiorna l'immagine, rigenera i servizi, cambia porta se richiesto,
# aggiunge o rimuove gateway (un gateway = un ambiente con la sua rete Zigbee).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$REPO_DIR/.env"
DATA_DIR="$HOME/medmonitor-data"
QUADLET_DIR="$HOME/.config/containers/systemd"
REGISTRY="$DATA_DIR/app/gateways.json"
DB_FILE="$DATA_DIR/app/medmonitor.db"
Z2M_FRONTEND_PORT=8080

say()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[32mOK\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31mERRORE:\033[0m %s\n' "$*" >&2; exit 1; }
warn() { printf '    \033[33mATTENZIONE\033[0m %s\n' "$*"; }

# --- 1. Prerequisiti ---------------------------------------------------------
say "Controllo prerequisiti"
[[ $EUID -ne 0 ]] || die "non lanciare come root: usa il tuo utente normale (sudo verrà chiesto solo quando serve)."
grep -qi fedora /etc/os-release 2>/dev/null || die "questo script è pensato per Fedora."
command -v podman >/dev/null || die "podman non installato. Esegui: sudo dnf install -y podman"
command -v curl >/dev/null || die "curl non installato. Esegui: sudo dnf install -y curl"
command -v python3 >/dev/null || die "python3 non installato. Esegui: sudo dnf install -y python3"
ok "Fedora, podman $(podman --version | awk '{print $3}')"

# --- 2. Funzioni gateway -----------------------------------------------------
# Registro gateway (gateways.json, letto dall'app) gestito con python3.
# Gateway 1: zigbee2mqtt / z2m / porta 8080. Gateway n>=2: zigbee2mqtt-n / z2m-n / zigbee2mqtt_n.
reg() {
    python3 - "$REGISTRY" "$DATA_DIR" "$DB_FILE" "${UI_PORT:-0}" "$@" <<'PY'
import glob, json, os, re, socket, sqlite3, sys
path, data_dir, db_file, ui_port, cmd, *args = sys.argv[1:]

def load():
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save(raw):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def conf_value(gid, key):
    d = os.path.join(data_dir, "z2m" if gid == 1 else f"z2m-{gid}")
    try:
        text = open(os.path.join(d, "configuration.yaml"), encoding="utf-8").read()
    except OSError:
        return ""
    m = re.search(rf"^\s*{key}:\s*(\S+)", text, re.M)
    return m.group(1) if m else ""

def active_sensors(gid):
    if not os.path.exists(db_file):
        return 0
    con = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    try:
        return con.execute("SELECT COUNT(*) FROM sensors WHERE active=1 AND gateway_id=?",
                           (gid,)).fetchone()[0]
    finally:
        con.close()

if cmd == "init":                       # init <name>
    save({"gateways": [{"id": 1, "name": args[0], "base_topic": "zigbee2mqtt",
                        "config": "/z2m/configuration.yaml", "frontend_port": 8080}],
          "next_id": 2})
elif cmd == "ids":
    print(" ".join(str(g["id"]) for g in load()["gateways"]))
elif cmd == "ports":
    print(" ".join(str(g.get("frontend_port", 8080)) for g in load()["gateways"]))
elif cmd == "port":                     # port <id>
    print(next(g.get("frontend_port", 8080) for g in load()["gateways"] if g["id"] == int(args[0])))
elif cmd == "table":
    print(f"    {'N.':<4}{'Ambiente':<28}{'IP':<18}{'Canale':<8}Sensori")
    for g in load()["gateways"]:
        ip = re.sub(r"^tcp://|:\d+$", "", conf_value(g["id"], "port")) or "-"
        try:
            n = active_sensors(g["id"])
        except sqlite3.Error:
            n = "?"
        print(f"    {g['id']:<4}{g['name'][:27]:<28}{ip:<18}{conf_value(g['id'], 'channel') or '-':<8}{n}")
elif cmd == "sensors":                  # sensors <id>  (exit 2 if the DB can't be read)
    try:
        print(active_sensors(int(args[0])))
    except sqlite3.Error:
        sys.exit(2)
elif cmd == "add":                      # add <name>  -> prints "id port channel"
    raw = load()
    gws = raw["gateways"]
    # ids are never reused, not even those of removed gateways
    removed = [int(m.group(1)) for d in glob.glob(os.path.join(data_dir, "z2m-*.removed-*"))
               if (m := re.search(r"z2m-(\d+)\.removed-", d))]
    gid = max([raw.get("next_id", 2), *(g["id"] + 1 for g in gws), *(r + 1 for r in removed)])
    used = {g.get("frontend_port", 8080) for g in gws} | {int(ui_port), 8000, 1883}
    port = 8079 + gid
    def busy(port):                     # already taken by another program on this host
        try:
            socket.create_connection(("127.0.0.1", port), 0.3).close()
            return True
        except OSError:
            return False
    while port in used or busy(port):
        port += 1
    channels = {conf_value(g["id"], "channel") for g in gws}
    channel = next((c for c in (11, 15, 20, 25) if str(c) not in channels), 26)
    gws.append({"id": gid, "name": args[0], "base_topic": f"zigbee2mqtt_{gid}",
                "config": f"/z2m-{gid}/configuration.yaml", "frontend_port": port})
    raw["next_id"] = gid + 1
    save(raw)
    print(gid, port, channel)
elif cmd == "remove":                   # remove <id>
    raw = load()
    gid = int(args[0])
    raw["gateways"] = [g for g in raw["gateways"] if g["id"] != gid]
    raw["next_id"] = max(raw.get("next_id", 2), gid + 1)
    save(raw)
PY
}

z2m_dir() { if (( $1 == 1 )); then echo "$DATA_DIR/z2m"; else echo "$DATA_DIR/z2m-$1"; fi; }

ask_ip() {   # ask_ip <domanda> <default>  -> IP_REPLY
    while true; do
        read -rp "    $1 [$2]: " IP_REPLY
        IP_REPLY="${IP_REPLY:-$2}"
        [[ "$IP_REPLY" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && return
        echo "    Indirizzo non valido (esempio: 192.168.1.50)."
    done
}

write_z2m_conf() {   # write_z2m_conf <file> <base_topic> <ip> <frontend_port> <canale>
    cat > "$1" <<EOF
homeassistant:
  enabled: false
mqtt:
  base_topic: $2
  server: mqtt://mosquitto:1883
serial:
  port: tcp://$3:6638
  adapter: ember
frontend:
  enabled: true
  port: $4
advanced:
  channel: $5
  network_key: GENERATE
  pan_id: GENERATE
  ext_pan_id: GENERATE
  last_seen: ISO_8601
  log_level: info
EOF
}

# --- 3. Parametri ------------------------------------------------------------
env_get() { [[ -f "$ENV_FILE" ]] && sed -n "s/^$1=//p" "$ENV_FILE" | tail -n1 || true; }

OLD_PORT="$(env_get UI_PORT)"
OLD_GATEWAY="$(env_get GATEWAY_IP)"
OLD_ADMIN="$(env_get ADMIN_PASSWORD)"
SECRET_KEY="$(env_get SECRET_KEY)"
[[ -n "$SECRET_KEY" ]] || SECRET_KEY="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"

port_busy() { ss -ltnH "sport = :$1" 2>/dev/null | grep -q .; }

GW_PORTS="$Z2M_FRONTEND_PORT"
[[ -f "$REGISTRY" ]] && GW_PORTS="$(reg ports)"

say "Configurazione (premi Invio per accettare il valore tra parentesi)"
while true; do
    read -rp "    Porta della UI web [${OLD_PORT:-8090}]: " UI_PORT
    UI_PORT="${UI_PORT:-${OLD_PORT:-8090}}"
    if ! [[ "$UI_PORT" =~ ^[0-9]+$ ]] || (( UI_PORT < 1024 || UI_PORT > 65535 )); then
        echo "    Porta non valida: usa un numero tra 1024 e 65535."; continue
    fi
    if (( UI_PORT == 8000 )); then echo "    La porta 8000 è riservata: scegline un'altra."; continue; fi
    if (( UI_PORT == 1883 )) || [[ " $GW_PORTS " == *" $UI_PORT "* ]]; then
        echo "    Porta usata da zigbee2mqtt/mosquitto: scegline un'altra."; continue
    fi
    # La porta occupata dal medmonitor già in esecuzione va bene: verrà riavviato.
    if port_busy "$UI_PORT" && ! { [[ "$UI_PORT" == "$OLD_PORT" ]] && systemctl --user -q is-active medmonitor.service; }; then
        echo "    La porta $UI_PORT è già in uso da un altro programma: scegline un'altra."; continue
    fi
    break
done

ask_ip "IP statico del gateway Zigbee 1 (SONOFF Dongle-M)" "$OLD_GATEWAY"
GATEWAY_IP="$IP_REPLY"

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

# --- 4. Cartelle, .env, configurazione zigbee2mqtt ---------------------------
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
    write_z2m_conf "$Z2M_CONF" zigbee2mqtt "$GATEWAY_IP" "$Z2M_FRONTEND_PORT" 11
    ok "creato $Z2M_CONF"
elif [[ -n "$OLD_GATEWAY" && "$GATEWAY_IP" != "$OLD_GATEWAY" ]]; then
    sed -i -E "s#tcp://[0-9.]+:([0-9]+)#tcp://$GATEWAY_IP:\1#" "$Z2M_CONF"
    ok "aggiornato IP gateway in $Z2M_CONF"
else
    ok "$Z2M_CONF già presente (non modificato)"
fi

# --- 5. Gateway (ambienti) ---------------------------------------------------
if [[ ! -f "$REGISTRY" ]]; then
    say "Nome dell'ambiente servito dal gateway $GATEWAY_IP"
    read -rp "    Nome ambiente [Gateway 1]: " GW_NAME
    reg init "${GW_NAME:-Gateway 1}"
    ok "creato $REGISTRY"
fi

add_gateway() {
    local name gid port channel dir
    read -rp "    Nome del nuovo ambiente (es. Ambulatorio): " name
    [[ -n "$name" ]] || { echo "    Nome obbligatorio."; return; }
    ask_ip "IP statico del nuovo gateway" ""
    read -r gid port channel < <(reg add "$name")
    dir="$(z2m_dir "$gid")"
    mkdir -p "$dir"
    write_z2m_conf "$dir/configuration.yaml" "zigbee2mqtt_$gid" "$IP_REPLY" "$port" "$channel"
    ok "aggiunto gateway $gid \"$name\" ($IP_REPLY, canale $channel, interfaccia zigbee2mqtt sulla porta $port)"
}

remove_gateway() {
    local gid n rc=0 answer dir stamp
    read -rp "    Numero del gateway da rimuovere: " gid
    if ! [[ "$gid" =~ ^[0-9]+$ ]] || [[ " $(reg ids) " != *" $gid "* ]]; then
        echo "    Gateway inesistente."; return
    fi
    if (( gid == 1 )); then
        echo "    Il gateway 1 non si può rimuovere (nome e IP si cambiano da Impostazioni → Gateway)."; return
    fi
    n="$(reg sensors "$gid")" || rc=$?
    if (( rc != 0 )); then
        warn "database non leggibile: non so se il gateway $gid ha sensori attivi."
        read -rp "    Scrivi RIMUOVI per confermare comunque: " answer
        [[ "$answer" == "RIMUOVI" ]] || { echo "    Annullato."; return; }
    elif (( n > 0 )); then
        echo "    Il gateway $gid ha $n sensori attivi: rimuovili prima da Impostazioni → Sensori."; return
    fi
    systemctl --user stop "zigbee2mqtt-$gid.service" 2>/dev/null || true
    rm -f "$QUADLET_DIR/zigbee2mqtt-$gid.container"
    dir="$(z2m_dir "$gid")"
    stamp="$(date +%Y%m%d-%H%M%S)"
    [[ -d "$dir" ]] && mv "$dir" "$dir.removed-$stamp"
    reg remove "$gid"
    ok "rimosso gateway $gid (configurazione conservata in $dir.removed-$stamp)"
}

while true; do
    say "Gateway configurati"
    reg table
    read -rp "    [A]ggiungi gateway, [R]imuovi gateway, [Invio] continua: " choice
    case "${choice,,}" in
        a) add_gateway ;;
        r) remove_gateway ;;
        "") break ;;
        *) echo "    Scelta non valida." ;;
    esac
done
read -ra GW_IDS <<< "$(reg ids)"

# --- 6. Immagine -------------------------------------------------------------
say "Costruisco l'immagine medmonitor (può richiedere qualche minuto la prima volta)"
podman build -t localhost/medmonitor:latest -f "$REPO_DIR/Containerfile" "$REPO_DIR"
podman pull -q docker.io/library/eclipse-mosquitto:2 >/dev/null
podman pull -q docker.io/koenkk/zigbee2mqtt:2 >/dev/null
ok "immagini pronte"

# --- 7. Servizi Quadlet ------------------------------------------------------
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

# write_z2m_unit <id> <nome container> <cartella dati> <porta interfaccia> <descrizione>
write_z2m_unit() {
    cat > "$QUADLET_DIR/$2.container" <<EOF
[Unit]
Description=medMonitor - zigbee2mqtt ($5)
Wants=mosquitto.service
After=mosquitto.service

[Container]
ContainerName=$2
Image=docker.io/koenkk/zigbee2mqtt:2
Network=medmonitor.network
Environment=TZ=Europe/Rome
Volume=$3:/app/data:z
PublishPort=127.0.0.1:$4:$4

[Service]
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
}

# unit di gateway non più nel registro
for f in "$QUADLET_DIR"/zigbee2mqtt-*.container; do
    [[ -e "$f" ]] || continue
    gid="${f##*/zigbee2mqtt-}"; gid="${gid%.container}"
    [[ " ${GW_IDS[*]} " == *" $gid "* ]] || rm -f "$f"
done

write_z2m_unit 1 zigbee2mqtt "$DATA_DIR/z2m" "$Z2M_FRONTEND_PORT" "gateway $GATEWAY_IP"
Z2M_UNITS=(zigbee2mqtt.service)
Z2M_VOLUMES="Volume=$DATA_DIR/z2m:/z2m:z"
for gid in "${GW_IDS[@]}"; do
    (( gid != 1 )) || continue
    write_z2m_unit "$gid" "zigbee2mqtt-$gid" "$DATA_DIR/z2m-$gid" "$(reg port "$gid")" "gateway $gid"
    Z2M_UNITS+=("zigbee2mqtt-$gid.service")
    Z2M_VOLUMES+=$'\n'"Volume=$DATA_DIR/z2m-$gid:/z2m-$gid:z"
done

cat > "$QUADLET_DIR/medmonitor.container" <<EOF
[Unit]
Description=medMonitor - monitoraggio temperature (porta $UI_PORT)
Wants=mosquitto.service ${Z2M_UNITS[*]}
After=mosquitto.service

[Container]
ContainerName=medmonitor
Image=localhost/medmonitor:latest
Network=medmonitor.network
EnvironmentFile=$ENV_FILE
Environment=MQTT_HOST=mosquitto MQTT_PORT=1883 DATA_DIR=/data Z2M_CONFIG=/z2m/configuration.yaml
Volume=$DATA_DIR/app:/data:z
$Z2M_VOLUMES
PublishPort=$UI_PORT:$UI_PORT

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
ok "medmonitor.network, mosquitto, ${Z2M_UNITS[*]%.service}, medmonitor"

# --- 8. Avvio ----------------------------------------------------------------
say "Avvio i servizi"
systemctl --user daemon-reload
systemctl --user restart medmonitor-network.service mosquitto.service "${Z2M_UNITS[@]}" medmonitor.service
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

# --- 9. Verifica -------------------------------------------------------------
say "Verifica finale"
# true if the /health JSON field $1 is true
healthy() { [[ "$HEALTH" =~ \"$1\":\ *true ]]; }
# names of the gateways reported offline by /health, one per line
offline_gateways() {
    python3 -c 'import json, sys
for g in json.loads(sys.argv[1]).get("gateways", []):
    if not g["online"]:
        print(g["name"])' "$HEALTH"
}
for i in $(seq 1 30); do
    if HEALTH="$(curl -fs "http://localhost:$UI_PORT/health")"; then
        # MQTT and zigbee2mqtt need a few seconds after startup: keep polling before warning
        if { ! healthy mqtt_connected || [[ -n "$(offline_gateways)" ]]; } && (( i < 30 )); then
            sleep 2; continue
        fi
        ok "medmonitor risponde: $HEALTH"
        [[ "$HEALTH" =~ \"db\":\ *\"ok\" ]] || warn "database non accessibile: controlla i log"
        healthy mqtt_connected || warn "medmonitor non connesso a mosquitto: systemctl --user status mosquitto"
        healthy scheduler_running || warn "scheduler fermo: nessun campionamento né allarme"
        while read -r name; do
            [[ -n "$name" ]] && warn "gateway \"$name\" non in linea: controlla IP/rete del dongle (Impostazioni → Gateway)"
        done <<< "$(offline_gateways)"
        IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
        printf '\n\033[1;32mInstallazione completata.\033[0m\n'
        printf '  UI medMonitor:   http://%s:%s\n' "${IP:-localhost}" "$UI_PORT"
        for gid in "${GW_IDS[@]}"; do
            port="$(reg port "$gid")"
            printf '  UI zigbee2mqtt (gateway %s): http://localhost:%s (solo dal server; dal PC: ssh -L %s:localhost:%s utente@server)\n' "$gid" "$port" "$port" "$port"
        done
        printf '  Log:             journalctl --user -u medmonitor -f\n\n'
        exit 0
    fi
    sleep 2
done
die "medmonitor non risponde su http://localhost:$UI_PORT/health. Controlla: systemctl --user status medmonitor; journalctl --user -u medmonitor -n 50"
