#!/bin/sh
set -eu
umask 077
test ! -e /var/lib/samurai/k109-phosh-configured
test -f /tmp/k109-phosh-shadow-private.txt
chpasswd -e < /tmp/k109-phosh-shadow-private.txt
mv /tmp/k109-phosh-shadow-private.txt /var/lib/samurai/phosh-shadow-used-private.txt
mkdir -p /etc/phosh /etc/greetd /home/cy122/.config /home/cy122/.local/state /usr/local/bin
chown 10000:10000 /home/cy122/.config /home/cy122/.local /home/cy122/.local/state
chmod 700 /home/cy122/.config
chmod 755 /etc/phosh
gsettings list-schemas | grep -qx mobi.phosh.osk
cat > /etc/phosh/phoc.ini <<'EOF'
[output:DSI-1]
scale = 3
EOF
chmod 644 /etc/phosh/phoc.ini
cat > /etc/greetd/samurai-phosh.toml <<'EOF'
[terminal]
vt = 7

[default_session]
command = "/usr/libexec/phrog-greetd-session"
user = "greetd"

[initial_session]
command = "/usr/local/bin/samurai-phosh-session"
user = "cy122"
EOF
cat > /usr/local/bin/samurai-phosh-session <<'EOF'
#!/bin/sh
umask 077
mkdir -p "$HOME/.local/state"
export XDG_CURRENT_DESKTOP=Phosh:GNOME
exec >> "$HOME/.local/state/samurai-phosh-session.log" 2>&1
date -u
exec /usr/bin/phosh-session
EOF
chmod 755 /usr/local/bin/samurai-phosh-session
cat > /usr/share/glib-2.0/schemas/90_samurai_haptics.gschema.override <<'EOF'
[org.sigxcpu.feedbackd]
profile='silent'
allow-important=[]
max-haptic-strength=0.0
EOF
glib-compile-schemas --strict /usr/share/glib-2.0/schemas
cat > /etc/conf.d/greetd <<'EOF'
cfgfile="/etc/greetd/samurai-phosh.toml"
EOF
# Keep the established NCM/SSH owner and the currently validated radio service.
for service in usb-signaller usb-moded usb-moded-setup bluetooth modemmanager; do
    if rc-service "$service" status >/dev/null 2>&1; then rc-service "$service" stop; fi
    if test -L "/etc/runlevels/default/$service"; then rc-update del "$service" default; fi
done
rc-update add greetd default
cp /etc/deviceinfo /var/lib/samurai/k109-pre-phosh/deviceinfo-after-install
date -u > /var/lib/samurai/k109-phosh-configured
rc-service greetd start
echo PHOSH_NATIVE_DRM_SESSION_START_REQUESTED
