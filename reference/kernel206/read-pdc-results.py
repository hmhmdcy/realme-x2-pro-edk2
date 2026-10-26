from pathlib import Path
import host, json
out = host.PRIVATE / 'pdc-first'
out.mkdir(mode=0o700)
for name in ['platform-selected-private.json', 'software-selected-private.json', 'platform-list-private.log', 'software-list-private.log']:
    host.download('/var/lib/samurai/k206-pdc-queries/' + name, out / name)
for kind in ['platform', 'software']:
    state = json.loads((out / (kind + '-selected-private.json')).read_text())
    print(json.dumps(dict(kind=kind, errors=state['errors'])))
    log = (out / (kind + '-list-private.log')).read_text()
    if kind == 'software':
        print(log)
    else:
        print(json.dumps(dict(platform_list_lines=len(log.splitlines()), platform_list_output_retained_privately=True)))
