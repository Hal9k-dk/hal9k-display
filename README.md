# hal9k-display — Ansible

Reproduces the `hal9k-display` Arch Linux host (a multi-screen kiosk/display
machine at [hal9k.dk](https://hal9k.dk)).

## Quick start

```bash
# 1. Install Ansible + community collections
pip install ansible
ansible-galaxy collection install community.general ansible.posix

# 2. Decrypt secrets when you need to edit them
ansible-vault edit vars/secrets.yml

# 3. Run the playbook
just deploy
# or: ansible-playbook -i inventory/hosts.ini site.yml
```

> **`.vaultpass`** contains the vault password and must not be committed to
> version control. It is already listed in `.gitignore`. `ansible.cfg` points
> Ansible at it automatically via `vault_password_file = .vaultpass`.

## Roles

| Role | What it does |
|------|-------------|
| `base` | User creation, SSH keys, sudo, autologin, locale, bashrc, sway autostart, essential packages |
| `networking` | systemd-networkd + systemd-resolved; Ethernet/WLAN/WWAN DHCP profiles |
| `sway` | Sway config, `sway-session.target`, systemd user environment integration |
| `kiosk` | Firefox multi-screen kiosk (`kiosk.sh`), `serve.py` screen-grabber HTTP API, `refresh` helper, `ydotool` daemon, clock web app |
| `mosquitto` | Local MQTT broker on port 1883 + bridge to `mqtt.hal9k.dk:8883` |
| `mqtt-logger` | Python mqtt-logger service (uv venv), InfluxDB env file, user systemd unit |
| `heartbeat` | `/usr/local/bin/hal9k-heartbeat` + systemd timer (minutely MQTT heartbeat) |

## Secrets

`vars/secrets.yml` (ansible-vault encrypted):

| Variable | Description |
|----------|-------------|
| `mosquitto_remote_password` | Password for the `hal9k` user on `mqtt.hal9k.dk` |
| `mqtt_logger_influxdb_token` | InfluxDB API token for `influxdb.belunktum.dk` |

## Notes

- The `kiosk/files/clock/GortonDigitalLight.otf` font is included as-is from the
  running host. Replace with a licensed copy if needed.
- The `mqtt-logger` Python source is vendored under
  `roles/mqtt-logger/files/mqtt_logger_src/`. `uv sync` is run on the target to
  build the virtualenv.
- No disk partitioning / GRUB installation is automated — the playbook assumes
  a working Arch Linux base install.
