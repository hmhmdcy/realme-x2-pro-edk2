from pathlib import Path
import json
import os
import subprocess

root = Path('/var/lib/samurai/k184-sensor-light-v1')
summary = json.loads((root / 'light/summary.json').read_text())
samples = json.loads((root / 'light/samples-private.json').read_text())
summary['channel_statistics'] = [
    {'index': i, 'minimum': min(v), 'maximum': max(v), 'unique': len(set(v))}
    for i in range(max(len(s['values']) for s in samples))
    if (v := [s['values'][i] for s in samples if len(s['values']) > i])
]
summary['actual_lux_response_to_light_proven'] = False
summary['taint'] = int(Path('/proc/sys/kernel/tainted').read_text())
summary['slpi_final'] = Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()
summary['sensor_power_final'] = Path('/sys/devices/platform/sensor-power/state').read_text().strip()
summary['recovery_final'] = Path('/sys/class/remoteproc/remoteproc0/recovery').read_text().strip()
summary['trial_complete'] = (root / 'trial-exit.txt').exists()
(root / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
print(subprocess.run(['sh', '-c', 'command -v cc; command -v pkg-config; ldd /usr/libexec/iio-sensor-proxy; ls /usr/lib/girepository-1.0/*Ssc* 2>/dev/null'], capture_output=True, text=True).stdout)
