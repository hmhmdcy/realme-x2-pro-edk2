"""Save the exact verified app overrides and distro package lock for rootfs work."""
from pathlib import Path
import ast,configparser,hashlib,io,json,tarfile
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel240')
with tarfile.open(P/'native-evidence-private.tar.gz','r:gz') as a:
 prefix='k240-snapshot-launcher-transaction/'
 manifest=json.loads(a.extractfile(prefix+'override-manifest-private.json').read())
 records={}
 for rel,item in manifest.items():
  name=Path(rel).name;assert name in ['org.gnome.Snapshot.desktop','org.gnome.Snapshot.service']
  data=a.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==item['sha256']
  assert b'GSK_RENDERER=cairo GDK_DISABLE=gl,vulkan,offload' in data
  config=configparser.ConfigParser(interpolation=None);config.optionxform=str;config.read_string(data.decode())
  for base in [R/'snapshot-launcher',ROOT/'linux-port/camera/snapshot-launcher']:
   base.mkdir(exist_ok=True);target=base/name;assert not target.exists();target.write_bytes(data)
  records[name]=dict(sha256=item['sha256'],bytes=len(data),mode=item['mode'])
lock=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(lock.read_text())
d['snapshot_distribution_packages']=json.loads((P/'snapshot-distro-manifest-private.json').read_text())['packages']
d['snapshot_launcher_files']=records;d['snapshot_launcher_profile']='snapshot-launcher/'
d['snapshot_launcher_scope']='per-user current device; full rootfs package integration still open'
lock.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/README.md';text=p.read_text();text+='\n当前已部署的[desktop副本](snapshot-launcher/org.gnome.Snapshot.desktop)和[D-Bus service副本](snapshot-launcher/org.gnome.Snapshot.service)按原生事务hash保存，供后续rootfs打包；不是已生成的新rootfs。当前设备回退先核事务manifest再移除两项用户覆盖，勿改动发行包文件。\n';p.write_text(text)
p=ROOT/'DOCS-INDEX.md';text=p.read_text().replace('最后整理：2026-10-14；本次维护未新增设备操作或验收。','最后整理：2026-10-16；实际硬件结果和未验收范围见功能清单与当前检查点。')
text=text.replace('| Camera实体前摄、静态启动与内部TPG | ', '| Camera应用、实体前后摄与内部TPG | [240桌面相机故障与CPU预览](reference/kernel240/README.md)、[239首参及近机型Linux方案](reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、')
p.write_text(text)
report=dict(stage=240,exact_native_verified_launcher_files=records,distro_packages_locked=14,
 no_new_phone_operation=True,rootfs_integration_still_open=True)
(R/'snapshot-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for p in R.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
suffixes={'.py','.cpp','.c','.h','.inc','.patch','.md','.yaml','.rules','.conf','.desktop','.service'}
files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*')) if p.is_file() and p.suffix in suffixes}
(R/'source-lock.json').write_text(json.dumps(files,indent=2)+'\n')
p=R/'source-final-validation.json';d=json.loads(p.read_text());d.update(source_files_locked=len(files),python_syntax_files=len(list(R.glob('*.py'))),exact_deployed_launcher_profile_saved=True);p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(report))
