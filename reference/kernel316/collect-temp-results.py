from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1]
code='''
from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
p=Path('/proc',str(s['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':s,'worker_live':live,'logs':{p.name:p.read_text(errors='replace') for p in root.glob('*.log')},'dmesg':(root/'dmesg-after.txt').read_text(errors='replace')}))
'''.replace('ROOT',repr('/var/lib/samurai/k316-consumer-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
(host.PRIVATE/('consumer-'+run+'-results.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
if not d['state']['terminal'] or d['worker_live']:raise SystemExit('Still live; inspect the same handle')
report=dict(stage=316,run=run,capture=d['state']['summary'],selections={},installed=False)
for name,text in d['logs'].items():
 if not name.startswith('capture-'):continue
 label=name.removeprefix('capture-').removesuffix('.log')
 gst=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
 raw=re.search(r'RAW_RESULT model=(\w+) kind=raw frames=(\d+) stable=(\d+) failed=(\d+) result=(\d+)',text)
 item=dict(hardware_cameras_registered=text.count('for pipeline handler camss-vfe'),
  fixture_restored='FIXTURE_RESTORATION result=0' in text,related_errors=[line for line in text.splitlines() if any(word in line for word in ['ERROR ','GStreamer error:','Frame sync event missing'])])
 if gst:item.update(client='gstreamer',frames=int(gst[1]),width=int(gst[2]),height=int(gst[3]),bus_errors=int(gst[4]),result=int(gst[5]))
 if raw:item.update(client='libcamera-raw',frames=int(raw[2]),stable=int(raw[3]),failed=int(raw[4]),result=int(raw[5]),paired_requests=text.count('RawPair request='),mismatched_requests=text.count(' matched=0'))
 item['passed']=(bool(gst) or bool(raw)) and item['hardware_cameras_registered']==4 and item['fixture_restored'] and not item['related_errors'] and not item['result']
 if raw:item['passed'] &= not item['failed'] and not item['mismatched_requests'] and item['paired_requests']==item['frames']
 report['selections'][label]=item
fallback=d['logs'].get('fallback-enumeration.log','')
report['legacy_kernel_automatic_simple_fallback']=fallback.count('for pipeline handler simple')==4 and 'for pipeline handler camss-vfe' not in fallback if fallback else None
report['runtime_kernel_stage']=314
report['passed']=report['capture']['passed'] and bool(report['selections']) and all(v['passed'] for v in report['selections'].values())
(HERE/('consumer-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
