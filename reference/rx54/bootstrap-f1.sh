set -euo pipefail
modprobe usbmon
exec python3 /mnt/e/edk2-samurai-out/rx54/eud-usb-console-f1.py --out /mnt/e/edk2-samurai-out/rx54/console-f1-01 --seconds 180
