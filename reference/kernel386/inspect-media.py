from pathlib import Path
import json,shlex
import host
code="""from pathlib import Path
import json
rows=[]
for p in Path('/sys/bus/media/devices').glob('media*'):
 rows.append(dict(name=p.name,resolved=str(p.resolve()),device_link_exists=(p/'device').exists(),device_resolved=str((p/'device').resolve())))
print(json.dumps(dict(media=rows,media_bus_exists=Path('/sys/bus/media').exists(),media_class_exists=Path('/sys/class/media').exists())))
"""
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'media-path-inspection-private.json').write_bytes(q.stdout)
print(q.stdout.decode())
