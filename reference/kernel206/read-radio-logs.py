from pathlib import Path
import host, json, re, sys
label = sys.argv[1]
assert re.fullmatch(r'[a-z0-9-]+', label)
out = host.PRIVATE / ('radio-logs-' + label)
out.mkdir(mode=0o700)
report = {}
for name in ['tftp.log', 'rmtfs.log']:
    target = out / (name + '-private')
    host.download('/run/samurai-wifi/' + name, target)
    text = target.read_text(errors='replace')
    terms = ['read request', 'write request', 'denied', 'reject', 'Permission denied', 'No such file', 'open ', 'iovec', 'oem_stanvbk', 'oem_dycnvbk', 'gps', 'gnss', 'mcfg']
    report[name] = dict(bytes=target.stat().st_size, lines=len(text.splitlines()), matches={term: text.lower().count(term.lower()) for term in terms})
(out / 'safe-statistics.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
