from pathlib import Path
import sys,runpy,tarfile,subprocess,os,json,hashlib,argparse
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel148');out=Path('/mnt/e/edk2-samurai-out/kernel148')
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--end',type=int);a=p.parse_args()
label=a.label;assert label.replace('-','').isalnum()
assert a.end is None or 1<=a.end<=10000
runpy.run_path(str(ref.parent/'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
archive=out/(label+'-private.tar.gz')
with tarfile.open(archive) as t:
    rd_members=[m for m in t if m.isfile() and m.name.endswith('.rd.gz')]
    assert rd_members
    m=next((m for m in rd_members if '/tu_' in m.name),rd_members[0])
    rd=out/(label+'-command-private.rd.gz');rd.write_bytes(t.extractfile(m).read())
log=out/(label+'-command-private.txt')
with log.open('wb') as f:
    subprocess.run([str(mesa/'decode-build/src/freedreno/decode/cffdump'),'--once']+(['--end='+str(a.end)] if a.end else [])+[str(rd)],
        env=dict(os.environ,RNN_PATH=str(mesa/'mesa-26.2.4/src/freedreno/registers')),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
s=log.read_text(errors='replace');ccu=sorted(set(l.strip().split('RB_CCU_CNTL:')[-1] for l in s.splitlines() if 'COLOR_CACHE_SIZE =' in l))
report=dict(label=label,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),rd_files=len(rd_members),
    first_rd_decoded=True,decoded_through_frame=a.end,bin_render_start=s.count('RM6_BIN_RENDER_START'),bin_resolve=s.count('RM6_BIN_RESOLVE'),ccu_configurations=ccu,
    raw_decoder_output_private=True)
(ref/(label+'-command-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
