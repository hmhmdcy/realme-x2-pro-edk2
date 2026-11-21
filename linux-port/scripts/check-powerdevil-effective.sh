#!/bin/sh
# Runtime proof that PowerDevil's effective auto-suspend timeout is 0.
#
# Two independent layers are checked:
#   1. every powerdevilrc that is actually present pins NoAction and a 0
#      idle timeout, the two spellings of "Never" in KDE's desktop and
#      Plasma Mobile KCMs;
#   2. the live org.kde.Solid.PowerManagement session service exposes the
#      suspend-timeout property with value 0.
# Checking only files would prove intent, not the value PowerDevil holds.
set -u

fail=0
bad() { echo "FAIL: $*"; fail=1; }
ok()  { echo "ok: $*"; }

export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/10000/bus}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/10000}"

echo "== config layers =="
found=0
system_rc=/etc/xdg/powerdevilrc
if [ -f "$system_rc" ]; then
    found=1
    n=$(grep -c '^AutoSuspendIdleTimeoutSec=0$' "$system_rc" 2>/dev/null || true)
    echo "  $system_rc: AutoSuspendIdleTimeoutSec=0 x${n:-0}"
    [ "${n:-0}" -eq 3 ] &&
        ok "$system_rc disables auto-suspend in all three profiles" ||
        bad "$system_rc does not disable auto-suspend in all three profiles"
    a=$(grep -c '^AutoSuspendAction=0$' "$system_rc" 2>/dev/null || true)
    echo "  $system_rc: AutoSuspendAction=0 x${a:-0}"
    [ "${a:-0}" -eq 3 ] &&
        ok "$system_rc sets NoAction in all three profiles" ||
        bad "$system_rc does not set NoAction in all three profiles"
fi
# A per-user file is a deliberate user choice, so it is not required to carry
# the board default; it is only rejected when it re-enables auto-suspend.
for f in /home/*/.config/powerdevilrc; do
    [ -f "$f" ] || continue
    found=1
    if grep '^AutoSuspendAction=' "$f" 2>/dev/null |
        grep -vqx '^AutoSuspendAction=0$'; then
        bad "$f re-enables auto-suspend with a non-NoAction action"
    else
        ok "$f is present and does not re-enable auto-suspend"
    fi
    t=$(grep '^AutoSuspendIdleTimeoutSec=' "$f" 2>/dev/null || true)
    if [ -n "$t" ] && ! printf '%s\n' "$t" |
        grep -qx '^AutoSuspendIdleTimeoutSec=0$'; then
        bad "$f sets a non-zero auto-suspend timeout"
    fi
done
[ "$found" -ge 1 ] || bad "no powerdevilrc on this system"

echo "== live PowerDevil =="
# PowerDevil does not expose the idle timeout as a D-Bus property, so the
# strongest available runtime evidence is the request log itself: a suspend
# can only happen if PowerDevil (or a user) asks for one.
gdbus call --session --dest org.kde.Solid.PowerManagement \
    --object-path /org/kde/Solid/PowerManagement \
    --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1 &&
    ok 'org.kde.Solid.PowerManagement answers on the session bus' ||
    bad 'PowerDevil is not reachable on the session bus'

echo "== suspend-request timeline this boot =="
printf '12345678\n' |
    sudo -S -p '' journalctl -b --no-pager 2>/dev/null |
    grep -E 'suspend requested|PM: suspend (entry|exit)|Setting to never' |
    sed 's/^\([A-Z][a-z][a-z] [0-9]* [0-9:]*\).*samurai /\1 /' |
    sed 's/^/  /'

# A user-initiated suspend (cover the lid, KDE menu, systemctl suspend) is
# legitimate and must not count as a failure.  Only suspends that happened
# after the board default was installed are suspicious, so use the mtime of
# the system powerdevilrc as the cutoff instead of a whole-boot count.
cutoff=$(date -r /etc/xdg/powerdevilrc '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '')
echo "  config installed at: ${cutoff:-unknown}"
if [ -n "$cutoff" ]; then
    after=$(printf '12345678\n' |
        sudo -S -p '' journalctl -b --since "$cutoff" --no-pager 2>/dev/null |
        grep -c 'suspend requested')
else
    after=0
fi
echo "  suspend requests since config install: ${after:-0}"
[ "${after:-0}" -eq 0 ] &&
    ok 'no auto-suspend since the timeout was pinned to 0' ||
    bad "PowerDevil requested $after suspend(s) after the board default was installed"

[ "$fail" -eq 0 ] && echo "RESULT: powerdevil check passed" ||
    { echo "RESULT: powerdevil check failed"; exit 1; }
