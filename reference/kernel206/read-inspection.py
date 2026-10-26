"""Retain discovery output privately; print only command help and path summaries."""
from pathlib import Path
import host, json
out = host.PRIVATE / 'radio-inspection'
out.mkdir(mode=0o700)
for name in ['qmicli-pdc-help-private.log', 'service-processes-private.json', 'usr__sbin__samurai-wifi-private']:
    host.download('/var/lib/samurai/k206-radio-inspection/' + name, out / name)
help_text = (out / 'qmicli-pdc-help-private.log').read_text()
print(help_text)
processes = json.loads((out / 'service-processes-private.json').read_text())
print(json.dumps(dict(service_programs=[Path(p['args'][0]).name for p in processes])))
