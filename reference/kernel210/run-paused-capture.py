from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k210-capture-tools'
host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
for name in ['capture-static-front.py','pause-monitor-capture.py']:host.upload(here/name,dest+'/'+name)
p=host.ssh('python3 '+dest+'/pause-monitor-capture.py',timeout=120)
(host.PRIVATE/'static-capture-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['six_physical_raw10_frames_captured']
q=host.ssh('cat /var/lib/samurai/k210-capture-monitor-fixture/summary.json')
fixture=json.loads(q.stdout);assert fixture['monitor_resumed']
report['monitor_fixture']=fixture
(here/'static-front-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
