"""Collect the two existing runs and summarise relevant RGB/PM evidence."""
from pathlib import Path
import json,re,shlex,statistics
import host
code=r'''
from pathlib import Path
import hashlib,json,os,struct
def note(raw):
    offset=struct.unpack_from('<Q',raw,40)[0]
    size,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    return next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
runs={}
for n in [1,2]:
    root=Path('/var/lib/samurai/k307-rgb-r'+str(n))
    runs[str(n)]={'state':json.loads((root/'state.json').read_text()),
                  'log':(root/'capture.log').read_text(errors='replace') if (root/'capture.log').exists() else ''}
import subprocess
module=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
health={'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
        'loaded_camss_matches_disk':note(module.read_bytes())==Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes(),
        'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()
                     for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
        'camera_rails':{}, 'consumers':{}}
for p in Path('/sys/class/regulator').glob('regulator.*'):
    name=(p/'name').read_text().strip()
    if name.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):
        health['camera_rails'][name]={'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())}
for p in Path('/proc').glob('[0-9]*'):
    try:
        name=(p/'comm').read_text().strip()
        if name in ['pipewire','wireplumber']:
            health['consumers'][name]=health['consumers'].get(name,0)+1
    except FileNotFoundError:pass
print(json.dumps({'runs':runs,'health':health}))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'capture-results.json').write_bytes(q.stdout)
data=json.loads(q.stdout)
report={'stage':307,'runs':{},'health':data['health']}
for n,run in data['runs'].items():
    log=run['log']
    rows=[]
    for match in re.finditer(r'RGB_BG frame=(\d+) sequence=(\d+) grid=(\d+)x(\d+) offset=(\d+),(\d+) region=(\d+)x(\d+) counts=([\d,]+) means=([\d.,]+)',log):
        v=match.groups()
        rows.append({'frame':int(v[0]),'sof':int(v[1]),'grid':[int(v[2]),int(v[3])],
                     'offset':[int(v[4]),int(v[5])],'region':[int(v[6]),int(v[7])],
                     'counts':list(map(int,v[8].split(','))),'means':list(map(float,v[9].split(',')))})
    images={int(f):int(s) for f,s in re.findall(r'FRAME number=(\d+) index=\d+ sequence=(\d+)',log)}
    phases={}
    for p in range(4):
        stable=[r for r in rows if p*9+4<=r['frame']<p*9+9]
        phases[str(p)]=[round(statistics.mean(r['means'][c] for r in stable),6) for c in range(4)] if stable else []
    report['runs'][n]={'summary':run['state'].get('summary'), 'terminal':run['state']['terminal'],
        'rgb_frames':len(rows),'all_image_sof_pairs_match':len(rows)==36 and all(images.get(r['frame'])==r['sof'] for r in rows),
        'geometry':{key:rows[0][key] for key in ['grid','offset','region']} if rows else {},
        'channel_count_sets':sorted({tuple(r['counts']) for r in rows}),
        'channel_order':['R','B','Gr','Gb'],'stable_phase_means':phases,
        'raw_cell_count_and_sum_bounds_checked_in_native_probe':len(rows)==36,
        'metadata_bytes':sorted(set(map(int,re.findall(r'STATS frame=\d+ phase=\d+ index=\d+ sequence=\d+ bytes=(\d+)',log))))}
health=report['health']
report['resources_restored']=(health['taint']==0 and health['loaded_camss_matches_disk'] and
    all(v=='suspended' for v in health['platforms'].values()) and
    len(health['camera_rails'])==9 and all(v=={'state':'disabled','users':0} for v in health['camera_rails'].values()) and
    health['consumers']=={'pipewire':1,'wireplumber':1})
report['passed']=report['resources_restored'] and all(r['terminal'] and r['summary']['passed'] and r['all_image_sof_pairs_match'] for r in report['runs'].values())
HERE=Path(__file__).resolve().parent
(HERE/'rgb-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
