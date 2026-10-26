from pathlib import Path
import hashlib, json, os, re, shlex, subprocess, time

out = Path('/var/lib/samurai/k173-single-card-recovery'); assert not out.exists(); out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
baseline = json.loads(Path('/var/lib/samurai/k173-source/validation.json').read_text())
for n,digest in baseline['ucm132_before_sha256'].items():
    assert hashlib.sha256((Path('/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro') / n).read_bytes()).hexdigest() == digest
assert all(p.read_text().strip() == 'closed' for p in Path('/proc/asound/card0').glob('pcm*/sub*/status'))
def command(args):
    p = subprocess.run(args,capture_output=True,timeout=30); assert p.returncode == 0,(args,p.stderr.decode()); return p.stdout.decode()
def pulse(args): return command(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+shlex.join(['pactl']+args)])
def modules():
    return [dict(index=int(p[0]),name=p[1],argument=p[2] if len(p)>2 else '') for p in
            (l.split('\t') for l in pulse(['list','short','modules']).splitlines())]
before = modules(); (out / 'modules-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
udevs = [r for r in before if r['name']=='module-udev-detect']; assert len(udevs)==1
cards = [r for r in before if r['name']=='module-alsa-card']
assert cards and all('device_id="0"' in r['argument'] and 'name="platform-sound"' in r['argument'] for r in cards)
pulse(['unload-module',str(udevs[0]['index'])])
for r in cards:
    if any(x['index']==r['index'] for x in modules()): pulse(['unload-module',str(r['index'])])
assert not any(r['name']=='module-alsa-card' for r in modules())
pulse(['load-module','module-udev-detect']+shlex.split(udevs[0]['argument'])); time.sleep(3)
card = json.loads(pulse(['-f','json','list','cards'])); sinks = json.loads(pulse(['-f','json','list','sinks']))
sources = [r for r in json.loads(pulse(['-f','json','list','sources'])) if not r['name'].endswith('.monitor')]
assert len(card)==len(sinks)==len(sources)==1
original = json.loads(Path('/var/lib/samurai/k173-deploy/pulse-before-private.json').read_text())
for old,new,kind in [(original['sinks'][0],sinks[0],'sink'),(original['sources'][0],sources[0],'source')]:
    pulse(['set-'+kind+'-volume',new['name']]+[str(v['value']) for v in old['volume'].values()])
    pulse(['set-'+kind+'-mute',new['name'],'1' if old['mute'] else '0'])
    pulse(['set-default-'+kind,new['name']])
time.sleep(3)
report = dict(stage=173,original_ucm132_restored=True,duplicate_card_modules_removed=len(cards),
              card_count=1,sink_count=1,hardware_source_count=1,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              pcm_closed=all(p.read_text().strip()=='closed' for p in Path('/proc/asound/card0').glob('pcm*/sub*/status')))
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert report['same_boot'] and report['taint']==0 and report['pcm_closed']
