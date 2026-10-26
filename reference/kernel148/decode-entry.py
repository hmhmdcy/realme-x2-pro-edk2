from pathlib import Path
import runpy,tarfile,os,subprocess,re,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel148'); out=Path('/mnt/e/edk2-samurai-out/kernel148')
runpy.run_path(str(ref.parent / 'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
with tarfile.open(out / 'entry-private.tar.gz') as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
cores=[n for n in data if n.endswith('.data')]
if not cores:
    report=dict(core_saved=False,reason='The existing devcoredump expired before the archival copy.',offending_comm='gnome-control-center',fault_source='CCU',bo_mapping_relation_unproven=True)
    (ref / 'entry-fault-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report)
for name in cores:
    p=out / name; p.write_bytes(data[name])
    with (out / (name+'.decoded.txt')).open('wb') as f:
        subprocess.run([str(mesa / 'decode-build/src/freedreno/decode/crashdec'),'-s','-f',str(p)],env=dict(os.environ,RNN_PATH=str(mesa / 'mesa-26.2.4/src/freedreno/registers')),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=60)
    raw=p.read_text()
    fault=int(re.search(r'iova=([a-fA-F0-9]+)',raw).group(1),16)
    matches=[(int(a,16),int(s)) for a,s in re.findall(r'  - iova: (0x[0-9a-f]+)\n    size: (\d+)',raw)]
    nearby=sorted(matches,key=lambda x:abs(x[0]-fault))[:6]
    report=dict(core_saved=True,offending_comm=re.search(r'^comm: (.+)',raw,re.M).group(1),fault_source='CCU',fault_inside_listed_bo=any(a<=fault<a+s for a,s in matches),bo_count=len(matches),unaligned64k_bos=sum(a%65536!=0 for a,s in matches))
    (ref / 'entry-fault-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report)
    (out / 'entry-nearby-bos-private.json').write_text(json.dumps(dict(fault=fault,nearby=nearby),indent=2)+'\n')
source=mesa / 'mesa-26.2.4/src/freedreno/vulkan/tu_knl_drm_msm.cc'
s=source.read_text().splitlines()
with (out / 'turnip-allocation-path-private.txt').open('w') as f:
    for lo,hi in [(540,640),(2250,2520)]:
        f.write('\n'.join(f'{i+1}: {s[i]}' for i in range(lo,min(hi,len(s))))+'\n')
print('K148_ENTRY_ANALYSIS_RECORDED')
