from pathlib import Path
import runpy,os,subprocess,tarfile,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147'); out=Path('/mnt/e/edk2-samurai-out/kernel147')
runpy.run_path(str(ref.parent / 'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
with tarfile.open(out / 'aligned147-private.tar.gz') as t:
    m=next(m for m in t if m.name.endswith('.rd.gz'))
    rd=out / 'aligned147-command-private.rd.gz'; rd.write_bytes(t.extractfile(m).read())
log=out / 'aligned147-command-private.txt'
with log.open('wb') as f:
    subprocess.run([str(mesa / 'decode-build/src/freedreno/decode/cffdump'),'--once',str(rd)],env=dict(os.environ,RNN_PATH=str(mesa / 'mesa-26.2.4/src/freedreno/registers')),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
s=log.read_text()
assert 'COLOR_CACHE_SIZE = CCU_CACHE_SIZE_QUARTER | COLOR_OFFSET = 0xf8000' in s
assert 'RM6_BIN_RENDER_START' in s and 'RM6_BIN_RESOLVE' in s
report=dict(candidate_default_gmem_confirmed=True,quarter_ccu_gmem_cache_present=True,bin_render_and_resolve_commands_present=True,raw_decoder_output_private=True)
(ref / 'gmem-command-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_ACTUAL_DEFAULT_GMEM_RENDER_AND_RESOLVE_CONFIRMED')
