from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
dest = ref / 'kernel113'
text = (ref / 'kernel111/flash-sensors.ps1').read_text().replace('111','113').replace('logdump-k113-sensors.img','logdump-k113-sensor-power.img')
text = text.replace("$Prefix='sensors-first'", "$Prefix='sensor-power-first'")
text = text.replace("if (!$audit.candidate_audit_pass", "if ($audit.sensor_power_auto_enable -or !$audit.candidate_audit_pass")
(dest / 'flash-sensor-power.ps1').write_text(text)
text = (ref / 'kernel112/read-early-eud.ps1').read_text().replace('112','113')
(dest / 'read-early-eud.ps1').write_text(text)
text = (ref / 'kernel112/collect-runtime.sh').read_text().replace('112','113')
anchor = 'cat /sys/kernel/debug/devices_deferred'
pos = text.index(anchor)
text = text[:pos] + '''cat /sys/devices/platform/sensor-power/state > "$dest/power-state.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
''' + text[pos:]
(dest / 'collect-runtime.sh').write_text(text)
print('KERNEL113_BOUNDED_FLASH_LOG_RUNTIME_TOOLS_PREPARED')
