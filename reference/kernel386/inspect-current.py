from pathlib import Path
import importlib.util,json,shlex,subprocess,hashlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='6fb4806e219998f5d06919a9b0266ff7b08867b0' and not git('status','--porcelain')
paths=['drivers/media/platform/qcom/camss/'+n for n in ['camss-icp-a5-boot.h','camss-icp-a5-boot.c','camss-icp-a5-ipe.h','camss-icp-a5-boot-test.c','Makefile','Kconfig']]
paths+=['drivers/media/test-drivers/vim2m.c','include/media/v4l2-mem2mem.h','drivers/media/v4l2-core/v4l2-mem2mem.c','drivers/media/common/videobuf2/videobuf2-vmalloc.c']
rows=[]
for relative in paths:
 data=(source/relative).read_bytes();target=P/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 rows.append(dict(path=relative,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
config=[l for l in (build/'.config').read_text().splitlines() if any(k in l for k in ['CONFIG_V4L2_MEM2MEM_DEV','CONFIG_VIDEOBUF2_VMALLOC','CONFIG_VIDEO_V4L2'])]
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 modules=[p.name for p in Path('/sys/module').glob('*icp*')],temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and not d['modules'] and d['temporary_firmware_absent'] and all(v=='suspended' for v in d['camera_pm'].values())
report=dict(stage=386,source=str(source),source_commit=git('rev-parse','HEAD'),source_clean=True,guard378_verified=True,
 sources=rows,relevant_kernel_config=config,phone_mutated=False,**d,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
