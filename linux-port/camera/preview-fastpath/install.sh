#!/bin/sh
set -eu

src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
home=${1:-/home/cy122}
user=${2:-cy122}

install -Dm755 "$src/samsinkinject.so" /usr/lib/samsinkinject.so

mkdir -p "$home/.local/share/applications"
mkdir -p "$home/.local/share/dbus-1/services"
install -m 644 "$src/../snapshot-launcher/org.gnome.Snapshot.desktop" \
  "$home/.local/share/applications/org.gnome.Snapshot.desktop"
install -m 644 "$src/../snapshot-launcher/org.gnome.Snapshot.service" \
  "$home/.local/share/dbus-1/services/org.gnome.Snapshot.service"

chown "$user:$user" \
  "$home/.local/share/applications/org.gnome.Snapshot.desktop" \
  "$home/.local/share/dbus-1/services/org.gnome.Snapshot.service"
