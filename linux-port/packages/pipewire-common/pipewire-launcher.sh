#!/bin/sh

cat >&2 <<EOF
*
* This script will be removed in the future to replace it with OpenRC user-services.
*
EOF

# Exit if the service is already running through user services
rc-service --user pipewire status 1>/dev/null 2>&1 && exit 0

# We need to kill any existing pipewire instance to restore sound
pkill -u "${USER}" -fx /usr/bin/pipewire-pulse 1>/dev/null 2>&1
pkill -u "${USER}" -fx /usr/bin/pipewire-media-session 1>/dev/null 2>&1
pkill -u "${USER}" -fx /usr/bin/wireplumber 1>/dev/null 2>&1
pkill -u "${USER}" -fx /usr/bin/pipewire 1>/dev/null 2>&1

exec /usr/bin/pipewire &

# Wait for the daemon with a bounded failure window. A failed audio daemon
# must not leave the desktop session's autostart process waiting forever.
wait_limit=${SAMURAI_PIPEWIRE_START_WAIT:-15}
case "$wait_limit" in ''|*[!0-9]*|0) wait_limit=15;; esac
attempt=0
while ! pgrep -x pipewire >/dev/null 2>&1; do
	attempt=$((attempt + 1))
	if [ "$attempt" -ge "$wait_limit" ]; then
		echo "pipewire did not start within ${wait_limit}s" >&2
		exit 1
	fi
	sleep 1
done

if [ -x /usr/bin/wireplumber ]; then
	exec /usr/bin/wireplumber &
elif [ -x /usr/bin/pipewire-media-session ]; then
	exec /usr/bin/pipewire-media-session &
fi

[ -f "/usr/share/pipewire/pipewire-pulse.conf" ] && exec /usr/bin/pipewire-pulse &
