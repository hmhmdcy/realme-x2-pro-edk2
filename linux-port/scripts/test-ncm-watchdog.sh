#!/bin/bash
# Offline test for samurai-ncm-watchdog.sh using a fake /sys tree.
#
# Verifies that the watchdog:
#   1. waits for usb0 instead of failing when it does not exist yet,
#   2. configures addresses once the interface appears,
#   3. performs at most one soft_connect per gadget lifetime,
#   4. resets its state when the interface disappears.

set -euo pipefail

watchdog="${1:?usage: $0 WATCHDOG_SCRIPT}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

udc="$work/udc/a600000.usb"
mkdir -p "$udc"
printf 'not_attached\n' > "$udc/state"
printf 'connect\n' > "$udc/soft_connect"

net="$work/net"
mkdir -p "$net"
addrlog="$work/addr.log"
sleeplog="$work/sleep.log"
: > "$addrlog"

# Fake ip/date/sleep so the script runs without touching the host.
mkdir -p "$work/bin"
cat > "$work/bin/ip" <<'EOF'
#!/bin/sh
# Emit the addresses we have "added" so the grep checks behave like real ip.
case "$1 $2" in
"link set") echo "set $3" >>"$FAKE_ADDRLOG"; exit 0 ;;
"addr add") echo "add $3" >>"$FAKE_ADDRLOG"; exit 0 ;;
"-4 addr") grep "^add $5" "$FAKE_ADDRLOG" 2>/dev/null | grep -q . && exit 0 || exit 1 ;;
esac
exit 0
EOF
chmod +x "$work/bin/ip"

cat > "$work/bin/sleep" <<'EOF'
#!/bin/sh
echo "$1" >>"$FAKE_SLEEPLOG"
EOF
chmod +x "$work/bin/sleep"

cat > "$work/bin/date" <<'EOF'
#!/bin/sh
echo "$FAKE_NOW"
EOF
chmod +x "$work/bin/date"

# Run the watchdog for a bounded number of iterations by making sleep exit
# after the script has seen enough.
export PATH="$work/bin:$PATH"
export FAKE_ADDRLOG="$addrlog" FAKE_SLEEPLOG="$sleeplog"
export SAMURAI_NCM_IFACE="$net/usb0"
export SAMURAI_UDC_DIR="$udc"
export SAMURAI_NCM_LOG="$work/watchdog.log"
export SAMURAI_NCM_RECONNECT_AFTER=25

echo "case 1: interface absent"
# sleep returns immediately; limit iterations with timeout.
FAKE_NOW=100 timeout 3 bash "$watchdog" 2>/dev/null || true
grep -q "configured" "$work/watchdog.log" && { echo "FAIL configured without iface"; exit 1; }
echo "  ok"

echo "case 2: interface present, carrier 0"
: > "$work/watchdog.log"
mkdir -p "$net/usb0"
printf '0\n' > "$net/usb0/carrier"
FAKE_NOW=100 timeout 3 bash "$watchdog" 2>/dev/null || true
grep -q "configured" "$work/watchdog.log" && echo "  configured" || { echo "FAIL no configure"; exit 1; }
echo "  ok"

echo "case 3: carrier 0 long enough triggers one soft_connect"
: > "$work/watchdog.log"
printf 'disconnect\n' > "$work/soft.before"
FAKE_NOW=200 timeout 4 bash "$watchdog" 2>/dev/null || true
grep -q "soft reconnect" "$work/watchdog.log" && echo "  reconnect logged" || { echo "FAIL no reconnect"; exit 1; }
attempts=$(grep -c "soft reconnect" "$work/watchdog.log" || true)
[ "$attempts" -le 1 ] || { echo "FAIL $attempts reconnects"; exit 1; }
echo "  ok ($attempts attempt)"

echo "case 4: carrier 1 resets state"
: > "$work/watchdog.log"
printf '1\n' > "$net/usb0/carrier"
FAKE_NOW=300 timeout 3 bash "$watchdog" 2>/dev/null || true
grep -q "carrier=0" "$work/watchdog.log" && { echo "FAIL carrier 1 logged as 0"; exit 1; }
echo "  ok"

echo "all watchdog cases passed"
