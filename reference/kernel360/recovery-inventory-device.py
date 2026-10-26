"""Read the recovered boot; stdout is private and may contain sensitive logs."""
from pathlib import Path
import base64,hashlib,json,re,subprocess
def text(name):
    try:return Path(name).read_text().strip()
    except OSError:return None
def binary(name):
    try:return Path(name).read_bytes()
    except OSError:return None
boot=text('/proc/sys/kernel/random/boot_id');release=text('/proc/sys/kernel/osrelease');model=(binary('/sys/firmware/devicetree/base/model') or b'').rstrip(b'\0').decode()
assert model=='Realme X2 Pro (RMX1931CN)' and release=='7.3.0-rc6-rmx1931-samurai-k298+'
assert boot=='3501b11d-9884-42da-8262-c713ce9a7c6b','Boot changed after the initial successful SSH observation'
root=Path('/var/lib/samurai/k356-boot-r5');state=json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None
note=binary('/sys/module/qcom_camss/notes/.note.gnu.build-id');modules={n:Path('/sys/module',n).exists() for n in ['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_boot_test']}
dt=Path('/sys/firmware/devicetree/base');temporary=[str(p.relative_to(dt)) for p in [dt/'soc@0/samurai-icp356-boot@ac10000',*[dt/'reserved-memory'/('samurai-icp356-'+n+'-iova') for n in ['fw','shared','heap','trace']]] if p.exists()]
workers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    cmd=binary(p/'cmdline') or b''
    if b'/var/lib/samurai/k356-boot-r5/worker.py' in cmd:workers.append(int(p.name))
pstore={p.name:base64.b64encode(p.read_bytes()).decode() for p in Path('/sys/fs/pstore').glob('*') if p.is_file()}
logs=subprocess.run(['dmesg'],capture_output=True).stdout
clocks={}
for line in (text('/sys/kernel/debug/clk/clk_summary') or '').splitlines():
    fields=line.split()
    if fields and any(fields[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[fields[0]]=int(fields[1])
report=dict(boot_id=boot,model=model,kernel=release,uptime_seconds=float((text('/proc/uptime') or '0').split()[0]),taint=text('/proc/sys/kernel/tainted'),cpu_online=text('/sys/devices/system/cpu/online'),
    camss_build_note_sha256=hashlib.sha256(note).hexdigest() if note else None,modules=modules,temporary_dt_nodes=temporary,worker_pids=workers,r5_state=state,
    r5_files=[p.name for p in root.iterdir()] if root.exists() else [],r5_manifest=text(root/'manifest.json'),r5_worker_log=text(root/'worker.log'),
    temporary_firmware_present=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
    temporary_firmware_sha256=hashlib.sha256(Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').read_bytes()).hexdigest() if Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists() else None,
    camss_runtime_status=text('/sys/bus/platform/devices/acb3000.camss/power/runtime_status'),icp_bps_ipe_clock_refs=clocks,
    old_guard_matches={name:binary(name)==(boot+'\n').encode() for name in ['/var/lib/samurai/k305-geometry-r2/boot-id-private.txt','/var/lib/samurai/k356-recovered/boot-id-private.txt','/var/lib/samurai/k298-work/boot-id-private.txt']},
    battery={p.name:{n:text(p/n) for n in ['capacity','temp','voltage_now','status']} for p in Path('/sys/class/power_supply').glob('*') if text(p/'type')=='Battery'},
    boot_reasons={k:v for item in (text('/proc/cmdline') or '').split() if '=' in item for k,v in [item.split('=',1)] if 'bootreason' in k or 'boot_reason' in k},
    pstore_b64=pstore,current_dmesg_b64=base64.b64encode(logs).decode())
print(json.dumps(report))
