"""Collect fixed-source timestamp rules and rejected output hashes, read-only."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'result.json').read_bytes())['child_returncode']==1
windows={'init/Makefile':[(27,61)],'init/version.c':[(40,65)],'usr/Makefile':[(58,77)],
         'usr/gen_initramfs.sh':[(190,201),(215,235),(241,252)],
         'usr/gen_init_cpio.c':[(378,390),(648,672)],
         'Documentation/kbuild/reproducible-builds.rst':[(20,44)]}
evidence={}
for name,ranges in windows.items():
    p=OUT/'source354'/name;lines=p.read_text().splitlines()
    evidence[name]={'sha256':sha(p),'lines':[{'line':i,'text':lines[i-1]} for a,b in ranges for i in range(a,min(b,len(lines))+1)]}
callers=['Makefile','init/Makefile','usr/Makefile','usr/gen_initramfs.sh','usr/gen_init_cpio.c','scripts/Makefile.lib','scripts/mkcompile_h']
result={'status':'read-only design evidence; no second build',
 'SOURCE_DATE_EPOCH_references_in_relevant_callers':{n:[i+1 for i,s in enumerate((OUT/'source354'/n).read_text().splitlines()) if 'SOURCE_DATE_EPOCH' in s] for n in callers},
 'fixed_source':evidence,
 'commands':{name:{'original_first_line':(BASE/'build'/name).read_text().splitlines()[0],
                   'rejected_first_line':(OUT/'build'/name).read_text().splitlines()[0]}
             for name in ['usr/.initramfs_data.cpio.cmd','usr/.initramfs_inc_data.cmd']},
 'uts_temporary':{'old':(BASE/'build/init/utsversion-tmp.h').read_text(),'new':(OUT/'build/init/utsversion-tmp.h').read_text()},
 'rejected_outputs':{n:{'sha256':sha(OUT/'build'/n),'bytes':(OUT/'build'/n).stat().st_size} for n in
 ['arch/arm64/boot/Image','vmlinux','init/version.o','init/version-timestamp.o','usr/initramfs_data.o','usr/initramfs_data.cpio','usr/initramfs_inc_data']},
 'original_initramfs_object_sha256':sha(BASE/'build/usr/initramfs_data.o'),
 'original_initramfs_cpio_sha256':sha(BASE/'build/usr/initramfs_data.cpio'),
 'original_initramfs_gzip_sha256':sha(BASE/'build/usr/initramfs_inc_data'),
 'next_step_is_design_only':True,'device_access':False}
(HERE/'timestamp-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'timestamp-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'relevant_SOURCE_DATE_EPOCH_references':result['SOURCE_DATE_EPOCH_references_in_relevant_callers'],
                  'uts_temporary':result['uts_temporary'],'rejected_outputs':result['rejected_outputs']},indent=2),flush=True)
