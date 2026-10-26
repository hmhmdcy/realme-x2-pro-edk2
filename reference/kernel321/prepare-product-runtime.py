from pathlib import Path
import io,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
s=(HERE.parent/'kernel316/native-temp-probe.py').read_text().replace('stage=316','stage=321')
a=s.index('    deployed=subprocess.check_output');b=s.index('    wait_idle()',a);s=s[:a]+s[b:]
a=s.index("    save('unloading-deployed')");b=s.index("    save('capturing')",a);s=s[:a]+s[b:]
s=s.replace('temporary_module_only=True,installed_files_unchanged=True','temporary_userspace_only=True,installed_files_unchanged=True')
(HERE/'native-product-probe.py').write_text(s)
files={'worker.py':HERE/'native-product-probe.py','pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/raw-smoke':SDK/'private/camss315-runtime/raw-smoke'}
with tarfile.open(host.PRIVATE/'product-probe.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
 prefix=host.PRIVATE/'package-prefix'
 for p in prefix.rglob('*'):tar.add(p,arcname='prefix/'+p.relative_to(prefix).as_posix(),recursive=False)
for name in ['launch-probe.py','poll-probe.py']:
 s=(HERE.parent/'kernel318'/name).read_text().replace('k318-lsc-','k321-product-').replace("'probe.tar.gz'","'product-probe.tar.gz'").replace("'probe-'","'product-'")
 (HERE/name.replace('-probe','-product-probe')).write_text(s)
print('Prepared packaged r26 consumers on the already-deployed318 driver.')
