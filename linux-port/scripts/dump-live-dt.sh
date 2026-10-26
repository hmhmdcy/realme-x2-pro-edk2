#!/bin/bash
# 从实机 /proc/device-tree 转储里取授权事实（ramoops、reserved-memory、ufs、keys）。
set -u
DT=/tmp/live-dt
rm -rf "$DT"; mkdir -p "$DT"
tar -xf "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar" -C "$DT"

echo "=== reserved-memory children ==="
ls "$DT/reserved-memory" 2>/dev/null | head -40

echo "=== ramoops node (hexdump via string cells) ==="
for f in "$DT"/reserved-memory/ramoops*/*; do
  case "$(basename "$f")" in
    name|phandle) continue;;
  esac
  v=$(od -An -tx4 "$f" 2>/dev/null | tr -s ' ' | head -2)
  echo "$(basename "$(dirname "$f")")/$(basename "$f") = $v"
done

echo "=== reserved-memory regs (big-endian cells) ==="
for d in "$DT"/reserved-memory/*/; do
  n=$(basename "$d")
  if [ -f "$d/reg" ]; then
    printf "%-28s %s\n" "$n" "$(od -An -tx4 -N32 "$d/reg" | tr -s ' ')"
  fi
done

echo "=== smem / cmd-db presence ==="
ls "$DT/reserved-memory" | grep -iE 'cmd|smem|rmtfs|aop|secure|mem_dump|sp_|user_contig|cma'

echo "=== memory node ==="
od -An -tx4 "$DT/memory@80000000/reg" 2>/dev/null | head -3
ls "$DT" | grep -i memory

echo "=== gpio_keys ==="
for f in "$DT"/gpio_keys/*; do echo "-- $f"; done
for k in vol_up vol_down; do
  for f in "$DT/gpio_keys/$k"/*; do
    b=$(basename "$f"); [ "$b" = "name" ] && continue
    v=$(od -An -tx4 "$f" 2>/dev/null | tr -s ' ' | head -1)
    [ -z "$v" ] && v="$(cat "$f" 2>/dev/null | tr -d '\0')"
    printf "%-10s %-22s %s\n" "$k" "$b" "$v"
  done
done

echo "=== ufs supplies (phandles only) ==="
for p in vcc-supply vccq-supply vccq2-supply vdd-hba-supply; do
  f="$DT/soc@0/ufshc@1d84000/$p"
  [ -f "$f" ] && printf "%-18s %s\n" "$p" "$(od -An -tx4 "$f" | tr -s ' ')"
done

echo "=== usb dwc3 ==="
ls "$DT/soc@0" | grep -iE 'usb|ssusb' | head
