set -euo pipefail
modprobe usbmon
exec python3 /mnt/e/edk2-samurai-out/rx54/eud-usb-repeated-console.py --out /mnt/e/edk2-samurai-out/rx54/repeated-console-01 --seconds 600
