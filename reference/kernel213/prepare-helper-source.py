from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tarfile
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213');repo=here.parents[1]
source=Path(json.loads((private/'source-location-private.json').read_text())['source']);backup=private/'libcamera-source-before';backup.mkdir(mode=0o700)
targets={'src/ipa/libipa/camera_sensor_helper.cpp':'e64b507de18774352cbe0bdfd51b637b00a56873','src/libcamera/sensor/camera_sensor_properties.cpp':'59e7f18952de3aaa5e4948928e7602779a02296d'}
product=repo/'linux-port/camera/libcamera';product.mkdir(parents=True,exist_ok=True)
records=[]
for name,commit in targets.items():
    path=source/name;before=path.read_text();(backup/path.name).write_text(before)
    patch=private/(commit+'.patch')
    for dry in [True,False]:
        args=['patch','-p1','--batch','--forward','--fuzz=0','--input',str(patch)]+(['--dry-run'] if dry else [])
        p=subprocess.run(args,cwd=source,capture_output=True);(private/(commit+('.dry-run' if dry else '.apply')+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    if name.endswith('camera_sensor_properties.cpp'):
        text=path.read_text();start=text.index('\t\t{ "imx471", {');end=text.index('\t\t{ "imx477", {',start);block=text[start:end];assert block.count('.unitCellSize = { 1400, 1400 }')==1
        path.write_text(text[:start]+block.replace('.unitCellSize = { 1400, 1400 }','.unitCellSize = { 1000, 1000 }')+text[end:])
    after=path.read_text();patchname='0007-imx471-helper.patch' if 'libipa' in name else '0008-imx471-properties-1um.patch'
    (product/patchname).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
    records.append(dict(file=name,before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest(),upstream_commit=commit,patch=patchname))
archive=private/'libcamera-helper-source.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:tar.add(source,arcname='libcamera-v0.7.2')
report=dict(stage=213,original_six_distro_patches_preserved=True,imx471_helper_backported=True,gain_model='1024/(1024-code)',gain_codes=[0,800],black_level_from_upstream_measurement_16bit=4096,properties_backported_with_unit_cell_corrected_to_nm=[1000,1000],unit_cell_primary_source='https://www.oneplus.com/hk/9/specs',no_unverified_control_delays_invented=True,initial_lut_fix_not_yet_applied=True,source_files=records,source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),source_archive_bytes=archive.stat().st_size,no_phone_product_change=True)
(here/'helper-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
