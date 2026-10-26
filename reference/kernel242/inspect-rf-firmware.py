"""Read-only Linux RF/clock/firmware provenance; does not start GNSS."""
from pathlib import Path
import hashlib,json,subprocess
r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
def read(p):
 try:return Path(p).read_text(errors='replace')
 except OSError as e:return dict(error=e.errno)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb',buffering=0) as f:
  while x:=f.read(4*1024*1024):h.update(x)
 return h.hexdigest()
private={}
private['snapshots']={p:read(p) for p in ['/sys/kernel/debug/clk/clk_summary','/sys/kernel/debug/regulator/regulator_summary','/sys/kernel/debug/gpio','/etc/samurai-wifi/modem-sha256.txt','/run/samurai-wifi/firmware-check.txt','/run/samurai-wifi/mcfg-prepare.log','/run/samurai-wifi/mcfg-state/source-manifest-private.json','/run/samurai-wifi/nv-source-hashes.txt','/run/samurai-wifi/tftp.log','/run/samurai-wifi/rmtfs.log']}
private['trace_formats']={str(p):read(p) for group in ['qrtr','clk','regulator'] for p in Path('/sys/kernel/tracing/events',group).glob('*/format')}
private['pinmux']={str(p):read(p) for p in Path('/sys/kernel/debug/pinctrl').glob('*/pinmux-pins')}
private['remoteprocs']=[]
for p in Path('/sys/class/remoteproc').glob('remoteproc*'):
 item=dict(path=str(p.resolve()),name=read(p/'name'),state=read(p/'state'),firmware=read(p/'firmware'))
 if isinstance(item['firmware'],str):
  fw=Path('/lib/firmware')/item['firmware'].strip()
  item['firmware_path']=str(fw);item['resolved_path']=str(fw.resolve());item['present']=fw.is_file()
  if fw.is_file():item.update(bytes=fw.stat().st_size,sha256=sha(fw))
 private['remoteprocs'].append(item)
private['dmesg']=subprocess.check_output(['dmesg']).decode(errors='replace')
private['tooling']=subprocess.run(['sh','-c','command -v strace; command -v bpftrace; command -v trace-cmd; command -v tcpdump'],capture_output=True,text=True).stdout
report=dict(stage=242,current236_boot=True,remoteproc_count=len(private['remoteprocs']),all_running=all(x['state'].strip()=='running' for x in private['remoteprocs']),
 all_firmware_files_present=all(x['present'] for x in private['remoteprocs']),trace_format_count=len(private['trace_formats']),
 clk_summary_read=isinstance(private['snapshots']['/sys/kernel/debug/clk/clk_summary'],str),regulator_summary_read=isinstance(private['snapshots']['/sys/kernel/debug/regulator/regulator_summary'],str),
 readonly=True,no_clock_gpio_regulator_or_modem_writes=True)
print(json.dumps(dict(report=report,private=private)))
