from pathlib import Path
import dbus,hashlib,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
services={};private={}
for name in ['rmtfs','tftp']:
 pid=int(Path('/run/samurai-wifi',name+'.pid').read_text());p=Path('/proc')/str(pid);assert p.exists();exe=p.joinpath('exe').resolve();services[name]=dict(alive=True,executable=exe.name,sha256=hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest())
 assert exe.name=={'rmtfs':'samurai-rmtfs-cow','tftp':'samurai-tqftpserv'}[name]
 env=dict(x.split(b'=',1) for x in p.joinpath('environ').read_bytes().split(b'\0') if b'=' in x)
 if name=='tftp':assert env.get(b'SAMURAI_TFTP_RW_ROOT')==b'/run/samurai-wifi/tftp-rw'
 private[name]=dict(pid=pid,argv=p.joinpath('cmdline').read_bytes().decode(errors='replace'))
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and not watch['active'] and watch['time_prepared'];bus.close()
outputs={}
for name,option in [('lock','--loc-get-engine-lock'),('mode','--loc-get-operation-mode'),('dms','--dms-get-operating-mode')]:
 x=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=12);assert x.returncode==0;outputs[name]=(x.stdout+x.stderr).decode().strip()
x=subprocess.run(['qmicli','--help-loc'],capture_output=True,timeout=10);assert x.returncode==0
report=dict(stage=245,same244_boot=True,services=services,receiver=outputs,time_prepared=True,location_enabled=0,taint=int(Path('/proc/sys/kernel/tainted').read_text()),set_engine_lock_help=[line.strip() for line in x.stdout.decode().splitlines() if 'engine-lock' in line])
print(json.dumps({'report':report,'private':private|dict(help=x.stdout.decode(),watch=watch,dmesg=subprocess.check_output(['dmesg']).decode())}))
