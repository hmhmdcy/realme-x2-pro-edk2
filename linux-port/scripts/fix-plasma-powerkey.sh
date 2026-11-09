#!/bin/sh
# Install the exclusive power-key/DPMS service from this workspace.
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run this as root" >&2
	exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
package_dir=$repo_root/packages/samurai-desktop
bridge=$package_dir/samurai-powerkey
service=$package_dir/samurai-powerkey.openrc

for command in kscreen-doctor loginctl python3; do
	command -v "$command" >/dev/null 2>&1 || {
		echo "$command is required" >&2
		exit 1
	}
done
for file in "$bridge" "$service"; do
	[ -f "$file" ] || {
		echo "missing source: $file" >&2
		exit 1
	}
done

install -Dm755 "$bridge" /usr/libexec/samurai-powerkey
install -Dm755 "$service" /etc/init.d/samurai-powerkey
rm -f /etc/xdg/autostart/samurai-powerkey.desktop

pkill -f '^python3 /usr/libexec/samurai-powerkey$' >/dev/null 2>&1 || true
rc-update add samurai-powerkey default >/dev/null 2>&1 || true
rc-service samurai-powerkey restart >/dev/null 2>&1 ||
	rc-service samurai-powerkey start

sleep 2
if ! rc-service samurai-powerkey status >/dev/null 2>&1; then
	echo "samurai-powerkey service failed to start" >&2
	tail -30 /var/log/samurai-powerkey.log >&2 || true
	exit 1
fi
if ! grep -q "grabbed .*power-key handling" /var/log/samurai-powerkey.log; then
	echo "power-key input was not grabbed" >&2
	tail -30 /var/log/samurai-powerkey.log >&2 || true
	exit 1
fi

echo "power-key service is active"
/usr/libexec/samurai-powerkey --status
echo "log: /var/log/samurai-powerkey.log"
