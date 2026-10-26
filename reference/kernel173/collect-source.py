from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k173-source')
if out.exists():
    assert not (out / 'validation.json').exists()
    assert (out / 'boot-id-private.txt').read_bytes() == Path('/proc/sys/kernel/random/boot_id').read_bytes()
else:
    out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k172-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
def command(args):
    p = subprocess.run(args,capture_output=True)
    assert p.returncode == 0, (args,p.stderr.decode())
    return p.stdout.decode()
names = ['Headphone Jack Switch','Handset Mic Switch','Left Speaker Switch','Right Speaker Switch',
         'SLIMBUS_0_RX Audio Mixer MultiMedia1','QUAT_MI2S_RX Audio Mixer MultiMedia1',
         'SLIM RX0 MUX','SLIM RX1 MUX','RX INT1_1 MIX1 INP0','RX INT2_1 MIX1 INP0',
         'RX INT1_1 INTERP','RX INT2_1 INTERP','RX INT1 DEM MUX','RX INT2 DEM MUX',
         'RX HPH Mode','COMP1 Switch','COMP2 Switch','HPHL Volume','HPHR Volume','ADC2 Volume',
         'AMIC MUX1','ADC MUX1','CDC_IF TX1 MUX','AIF1_CAP Mixer SLIM TX1',
         'DMIC MUX5','ADC MUX5','CDC_IF TX5 MUX','AIF1_CAP Mixer SLIM TX5',
         'MultiMedia2 Mixer SLIMBUS_0_TX']
controls = {}
(out / 'controls-all-private.txt').write_text(command(['amixer','-c','0','contents']))
for n in names:
    data = command(['amixer','-c','0','cget',"name='"+n+"'"])
    controls[n] = dict(value=re.search(r': values=(.*)',data)[1].strip(),
                       items=re.findall(r"Item #\d+ '([^']+)'",data))
    (out / (n.replace(' ','-')+'-private.txt')).write_text(data)
jacks = {}
for n in ['Headphone Jack','Mic Jack']:
    data = command(['amixer','-c','0','cget',"iface=CARD,name='"+n+"'"])
    jacks[n] = re.search(r': values=(.*)',data)[1].strip()
assert all(v == 'off' for v in jacks.values())
assert all(p.read_text().strip() == 'closed' for p in Path('/proc/asound/card0').glob('pcm*/sub*/status'))
for n in ['Realme_X2_Pro.conf','HiFi.conf']:
    shutil.copyfile('/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/'+n,out / (n+'-before-private'))
helper = Path('/usr/libexec/samurai-audio-route')
assert not helper.exists()
(out / 'dmesg-before-private.txt').write_text(command(['dmesg']))
amps = {n:Path('/sys/bus/i2c/devices/'+n+'/status').read_text() for n in ['1-0039','1-003a']}
assert all('powered=0 muted=1' in s for s in amps.values())
report = dict(stage=173,kernel_build=172,same_k172_boot=True,ucm132_before_sha256={n:hashlib.sha256((out / (n+'-before-private')).read_bytes()).hexdigest() for n in ['HiFi.conf','Realme_X2_Pro.conf']},
              jack_status=jacks,controls=controls,amps=amps,software_helper_absent=True)
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k173-source-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
