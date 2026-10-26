from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');old=r/'reference/kernel126';ref=r/'reference/kernel128'
s=(old/'collect-final-health.sh').read_text().replace("'^#126 '","'^#128 '").replace('k126-embedded-runtime','k128-first-runtime').replace('k126-final-health','k128-final-health').replace('samurai-k126+','samurai-k128+').replace('k126-preflash','k128-preflash').replace('K126_FINAL','K128_FINAL')
s=s.replace('cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"','cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"\niw dev wlan0 link > "$dest/wlan-link-private.txt"\nstat -c "%u:%g:%a" /etc/NetworkManager/system-connections/samurai-wifi.nmconnection > "$dest/wifi-profile-owner.txt"\ncat /sys/kernel/debug/pm_genpd/pm_genpd_summary > "$dest/power.txt"')
(ref/'collect-final-health.sh').write_text(s)
print('K128_CURRENT_BOOT_FINAL_DESKTOP_RADIO_MODULE_TRACE_OFF_CAPTURE_READY',flush=True)
