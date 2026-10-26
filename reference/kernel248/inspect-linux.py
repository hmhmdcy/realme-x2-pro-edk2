from pathlib import Path
import hashlib,json,os,shutil,subprocess
r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();guard=r/'k247-runtime/boot-id-private.txt';same=guard.exists() and boot==guard.read_bytes()
def cmd(args):
 x=subprocess.run(args,capture_output=True,timeout=15);return dict(returncode=x.returncode,stdout=x.stdout.decode(errors='replace'),stderr=x.stderr.decode(errors='replace'))
parts=[]
for p in sorted(Path('/dev/disk/by-partlabel').iterdir()):
 q=p.resolve();sys=Path('/sys/class/block')/q.name
 parts.append(dict(label=p.name,block=q.name,bytes=int((sys/'size').read_text())*512,start=int((sys/'start').read_text())*512 if (sys/'start').exists() else None))
mounts=Path('/proc/mounts').read_text();sv=os.statvfs('/');watch=json.loads((r/'gnss-assist/watch-state.json').read_text());dm=subprocess.check_output(['dmesg']).decode();fatals={k:dm.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dsp_fatal='fatal error received').items()};tools={x:shutil.which(x) for x in ['tar','zstd','gzip','partclone.f2fs','fsck.f2fs','dump.f2fs','mkfs.f2fs','losetup','fstrim','blkid','mount','umount','dd','pv','getfattr','setfattr','curl','wget','socat','busybox']};f2fs=cmd(['sh','-c','command -v dump.f2fs >/dev/null && dump.f2fs -V || true'])
report=dict(stage=248,current_boot_matches_247=same,kernel_release=os.uname().release,kernel_version=os.uname().version,root_total_bytes=sv.f_frsize*sv.f_blocks,root_used_bytes=sv.f_frsize*(sv.f_blocks-sv.f_bfree),root_available_bytes=sv.f_frsize*sv.f_bavail,partitions=parts,tools=tools,watch_running=watch.get('running'),gnss_active=watch.get('active'),remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')],taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=fatals,no_flash_or_reboot=True)
print(json.dumps(dict(report=report,private=dict(boot_id=boot.decode().strip(),model=Path('/proc/device-tree/model').read_bytes().hex(),mounts=mounts,cmdline=Path('/proc/cmdline').read_text(),lsblk=cmd(['lsblk','-b','-J','-o','NAME,SIZE,TYPE,FSTYPE,LABEL,PARTLABEL,PARTUUID,MOUNTPOINTS']),df=cmd(['df','-B1']),f2fs_version=f2fs,watch=watch,rom_metadata_available=Path('/vendor').exists()))))
