from pathlib import Path
import io,json,re,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run);root='/var/lib/samurai/k366-boot-'+run
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and all(m['intree']=='Y' for m in build['modules'])
build['modules']=[m for m in build['modules'] if m['name'] in ['qcom-camss-icp-a5-core','camss-icp-a5-boot-test']]
region=build['firmware_region'];assert region['offline_overlay_named_firmware_resolves']
facts={n:dict(phandle=region[k]) for n,k in [('camss@acb3000','camss'),('clock-controller@ad00000','camcc'),('iommu@15000000','smmu')]}
manifest=dict(kernel_release=build['modules'][0]['vermagic'].split()[0],**{n:facts[n]['phandle'] for n in ['camss@acb3000','clock-controller@ad00000','iommu@15000000']},interrupt_parent=json.loads((P.parent/'kernel356/irq-parent-private.json').read_text())['interrupt_parent'])
manifest.update({key:region[key] for key in ['firmware_region_path','firmware_physical','firmware_bytes','existing_firmware_phandle']})
manifest['boot_guard']=json.loads((P/'postboot-adoption-private.json').read_text())['guard_path']
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for row in build['modules']:tar.add(row['private_path'],arcname='core.ko' if row['name']=='qcom-camss-icp-a5-core' else 'test.ko')
 tar.add(HERE/'boot-worker.py',arcname='worker.py')
 tar.add(P.parent/'kernel352/CAMERA_ICP.elf-private',arcname='firmware.elf')
 data=json.dumps(manifest).encode();info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
code="""from pathlib import Path
import io,tarfile,sys,os
root=Path(ROOT);assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
raw=sys.stdin.buffer.read();tar=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz');members=tar.getmembers()
assert {m.name for m in members}=={'core.ko','test.ko','worker.py','manifest.json','firmware.elf'} and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for member in members:
 with root.joinpath(member.name).open('xb') as stream:stream.write(tar.extractfile(member).read());stream.flush();os.fsync(stream.fileno())
descriptor=os.open(root,os.O_RDONLY|os.O_DIRECTORY);os.fsync(descriptor);os.close(descriptor)
print('Prepared temporary OEM A5 bootstrap diagnostic.')
""".replace('ROOT',repr(root)).replace('GUARD',repr(manifest['boot_guard']))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=30);print(q.stdout.decode())
code="""from pathlib import Path;import subprocess,json;root=Path(ROOT);log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);print(json.dumps(dict(pid=child.pid,root=str(root))))""".replace('ROOT',repr(root))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);(P/('launch-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
