"""Build isolated artifacts, restoring the production216 source and build outputs."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,shutil,stat,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
proof=json.loads((here/'factory-mode-candidate-source-validation.json').read_text());candidate=private/'candidate-source';out=private/'candidate-build';out.mkdir(mode=0o700)
source=kernel/'drivers/media/i2c/imx471.c';board=kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert sha(source)=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
assert sha(candidate/'imx471.c')==proof['source_sha256'] and sha(candidate/'sm8150-samurai.dts')==proof['board_sha256']
modes=json.loads((private/'factory-imx471-modes-private.json').read_text())['modes'];differences=[]
values30={r['address']:r['value'] for r in modes[1]['registers']};values60={r['address']:r['value'] for r in modes[2]['registers']}
assert set(values30)==set(values60)
differences=[address for address in values30 if values30[address]!=values60[address]];assert set(differences)=={0x0340,0x0341,0x0202,0x0203}
for mode in modes:
    values={r['address']:r['value'] for r in mode['registers']};pll=(values[0x030e]<<8)|values[0x030f]
    link_frequency=mode['external_clock']*pll//values[0x030d]//2
    assert link_frequency==(748800000 if mode['index']==0 else 400000000)
    assert link_frequency*2*mode['lane_count']//mode['raw_bits']==mode['output_pixel_clock_metadata']
files={source,board,*[p for p in source.parent.glob('imx471*') if p.is_file()],*[p for p in source.parent.glob('.imx471*') if p.is_file()]}
files|={kernel/name for name in ['.config','Module.symvers','modules.order']}
saved={str(p.relative_to(kernel)):dict(data=p.read_bytes(),mode=stat.S_IMODE(p.stat().st_mode)) for p in files}
backup=private/'candidate-build-before';backup.mkdir(mode=0o700)
for relative,item in saved.items():
    path=backup/relative;path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.write_bytes(item['data']);path.chmod(0o600)
preserved={name:sha(kernel/name) for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/media/v4l2-core/v4l2-cci.ko']}
original_symbols=(kernel/'Module.symvers').read_bytes();assert len(original_symbols.splitlines())==16798
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
    source.write_bytes((candidate/'imx471.c').read_bytes());board.write_bytes((candidate/'sm8150-samurai.dts').read_bytes())
    with (out/'module-build-private.log').open('xb') as log:
        subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/media/i2c/imx471.ko'],cwd=kernel,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    (out/'generated-Module.symvers-private').write_bytes((kernel/'Module.symvers').read_bytes())
    module=out/'imx471-factory-modes.ko';shutil.copyfile(kernel/'drivers/media/i2c/imx471.ko',module);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(module)],check=True)
    recipe=(kernel/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1];commands=[];current=[]
    for token in shlex.split(recipe):
        if token==';':commands.append(current);current=[]
        else:current.append(token)
    commands.append(current);assert len(commands)==3
    base='arch/arm64/boot/dts/qcom/';mapping={base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/'source-pre.d'),base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/'dtc.d'),base+'.sm8150-samurai.dtb.dts.tmp':str(out/'factory-modes.pp.dts'),base+'sm8150-samurai.dtb':str(out/'factory-modes.dtb')}
    def rewrite(value):
        for before,after in sorted(mapping.items(),key=lambda pair:-len(pair[0])):value=value.replace(before,after)
        return value
    for index,args in enumerate(commands[:2]):
        p=subprocess.run([rewrite(value) for value in args],cwd=kernel,capture_output=True,timeout=60);(out/('dtb-'+str(index)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
finally:
    current_files={*[p for p in source.parent.glob('imx471*') if p.is_file()],*[p for p in source.parent.glob('.imx471*') if p.is_file()]}
    for path in current_files:
        if str(path.relative_to(kernel)) not in saved:
            assert path.parent==source.parent and (path.name.startswith('imx471') or path.name.startswith('.imx471'));path.unlink()
    for relative,item in saved.items():
        path=kernel/relative;path.write_bytes(item['data']);path.chmod(item['mode'])
assert all((kernel/name).read_bytes()==item['data'] for name,item in saved.items())
assert all(sha(kernel/name)==digest for name,digest in preserved.items())
available={line.split()[1] for line in original_symbols.decode().splitlines()}
imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(module)],text=True);assert all(line.split()[-1] in available for line in imports.splitlines() if line.strip())
vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(module)],text=True).strip();assert vermagic==json.loads((here.parent/'kernel216/imx471-module-build-validation.json').read_text())['vermagic']
assert subprocess.check_output(['modinfo','-F','intree',str(module)],text=True).strip()=='Y'
diagnostics=[line for line in (out/'module-build-private.log').read_text().splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()];assert not diagnostics,diagnostics
spec=importlib.util.spec_from_file_location('fdt_compare211',here.parent/'kernel211/fdt_compare.py');fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt);parse=fdt.parser()
old=parse((private.parent/'kernel211/sensor-domain-dtb/sensor-domain.dtb').read_bytes());new=parse((out/'factory-modes.dtb').read_bytes());assert set(old)==set(new)
changes=[dict(path=path,property=key) for path in old for key in set(old[path])|set(new[path]) if old[path].get(key)!=new[path].get(key)]
assert changes==[dict(path='/soc@0/cci@ac4b000/i2c-bus@1/camera@10/port/endpoint',property='link-frequencies')],changes
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
report=dict(stage=217,unapplied_candidate_driver_and_dtb_built=True,module_sha256=sha(module),module_bytes=module.stat().st_size,dtb_sha256=sha(out/'factory-modes.dtb'),vermagic=vermagic,w1_module_diagnostics=0,all_import_symbols_available=True,host216_source_objects_metadata_image_and_canonical_dtb_restored=True,only_candidate_dtb_property_changed=changes[0],factory30_and60_only_frame_length_and_exposure_differ=True,link_frequencies_match_factory_op_pll_and_output_pixel_clock=True,full_quad_raw_requires_explicit_opt_in_and_firmware_frequency=True,physical_mode_and_full_rgb_processing_not_yet_accepted=True,no_device_install_flash_or_reboot=True)
(here/'factory-mode-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
