"""Compile staged CAMSS files using saved kernel commands, leaving builds intact."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel283')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
OLD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
STAGE = PRIVATE/'wb-candidate'
OUT = PRIVATE/'wb-final-objects'
assert not OUT.exists(), 'Inspect original overlay compilation instead of replaying it'
OUT.mkdir()
source_dir = 'drivers/media/platform/qcom/camss'
prefix = TREE/source_dir
objects = sorted(p for p in STAGE.glob('*.c') if (OLD/source_dir/('.'+p.stem+'.o.cmd')).exists())
assert len(objects) == 32, len(objects)
objects.append(STAGE/'camss-vfe-175-pixel.c')
before = {n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in
          [source_dir+'/camss-vfe.h',source_dir+'/camss-vfe-17x.c','include/uapi/linux/qcom-camss-config.h']}
env = dict(os.environ, TMPDIR=str(PRIVATE))
results=[]
start=time.monotonic()
with (PRIVATE/'wb-final-overlay-build-private.log').open('x') as log:
    for source in objects:
        template = source.stem if source.stem != 'camss-vfe-175-pixel' else 'camss-vfe-175-camif'
        command_file = OLD/source_dir/('.'+template+'.o.cmd')
        line=command_file.read_text().splitlines()[0].split(' := ',1)[1]
        args=shlex.split(line)
        assert args[0]=='aarch64-linux-gnu-gcc' and args[-1]==str(prefix/(template+'.c'))
        args[1:1]=['-I'+str(PRIVATE/'wb-uapi'),'-I'+str(STAGE)]
        for i,arg in enumerate(args):
            if arg.startswith('-Wp,-MMD,'):args[i]='-Wp,-MMD,'+str(OUT/(source.stem+'.d'))
            elif arg.startswith('-DKBUILD_BASENAME='):args[i]='-DKBUILD_BASENAME="'+source.stem.replace('-','_')+'"'
        args[args.index('-o')+1]=str(OUT/(source.stem+'.o'))
        args[-1]=str(source)
        assert '-Werror' in args
        result=subprocess.run(args,cwd=OLD,env=env,stdout=log,stderr=subprocess.STDOUT)
        log.flush()
        assert result.returncode==0, (source.name,result.returncode)
        obj=OUT/(source.stem+'.o')
        results.append(dict(source=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                            command_sha256=hashlib.sha256(json.dumps(args).encode()).hexdigest(),
                            object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest()))
    linked=OUT/'qcom-camss.o'
    subprocess.run(['aarch64-linux-gnu-ld','-EL','-maarch64elf','-r','-o',str(linked)]+
                   [str(OUT/(p.stem+'.o')) for p in objects],check=True,cwd=OLD,stdout=log,stderr=subprocess.STDOUT)
assert not (PRIVATE/'wb-final-overlay-build-private.log').read_text(), 'Inspect compiler diagnostics'
assert all(hashlib.sha256((TREE/n).read_bytes()).hexdigest()==h for n,h in before.items())
report=dict(stage=283,exit=0,seconds=round(time.monotonic()-start,2),objects=results,
            aggregate_sha256=hashlib.sha256(linked.read_bytes()).hexdigest(),w1_werror=True,
            source_tree_and_original_build_objects_not_modified=True,
            method='Saved GCC W=1/-Werror kernel object commands, staged CAMSS headers and UAPI; independent relocatable link',
            not_a_full_kernel_or_module_link=True,not_deployed=True)
(ROOT/'wb-overlay-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='objects'},indent=2),flush=True)
