"""Original guarded k363 inputs; one private W1/Werror object, no make/link."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
HELPER_SHA='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
SOURCE_SHA='0fdafb8b3924e431efd67a888cbb88b8f5fe6de22dc400b009bf64cba34b7be5'
BASE=Path('/home/cy122/charging-management-20261023/source-float-candidate')
PRIVATE=Path('/home/cy122/charging-management-20261023/usb-input-irq-object-r1')
r={'passed':False,'only_private_object':True,'Image_module_or_firmware_linked':False,
   'phone_SSH_USB_SDK_Git_used':False,'new_anchor_started':False,'unmounted':False}
try:
    assert os.geteuid()==0
    helper=REF/'kernel284/storage.py';assert sha(helper)==HELPER_SHA
    backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
    assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
    assert sha(HERE/'samurai-usb-input.c')==SOURCE_SHA
    tested=json.loads((HERE/'test-result.json').read_bytes())
    assert tested['passed'] and tested['actual_function_result']['actual_function_cases']==16
    assert tested['source_sha256']==SOURCE_SHA
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('usb_irq_original_storage284',helper)
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    shared=storage.mounted_build();original=shared.parent/'source354'
    oldbuild=BASE/'kbuild';oldsource=BASE/'source-view'
    assert (oldbuild/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
    assert sha(oldbuild/'.config')=='7367d3c7c5f1ccca527c67467085f76a9d307f168e6d0f5a9d3954517d0207e5'
    cmdfile=oldbuild/'drivers/power/supply/.samurai-usb-input.o.cmd'
    first=cmdfile.read_text().splitlines()[0]
    assert first.startswith('savedcmd_drivers/power/supply/samurai-usb-input.o := ')
    command=shlex.split(first.split(' := ',1)[1])
    assert command[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in command
    assert not any(v in [';','&&','||'] for v in command)
    oldc=oldsource/'drivers/power/supply/samurai-usb-input.c'
    assert sha(oldc)=='b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098'
    assert command[-1]==str(oldc) and command[-4:-2]==['-c','-o']
    originals=['drivers/of/irq.c','drivers/base/platform.c','drivers/mfd/qcom-spmi-pmic.c',
               'drivers/spmi/spmi-pmic-arb.c','drivers/base/core.c']
    tracked=[helper,shared/'.config',oldbuild/'.config',cmdfile,oldc,oldbuild/'drivers/power/supply/samurai-usb-input.o',
             original/'drivers/power/supply/Makefile',*[original/n for n in originals]]
    before={str(p):sha(p) for p in tracked}
    PRIVATE.mkdir(exist_ok=False)
    source=PRIVATE/'samurai-usb-input.c';header=PRIVATE/'samurai-usb-input-decode.h'
    shutil.copy2(HERE/source.name,source);shutil.copy2(HERE/header.name,header)
    obj=PRIVATE/'samurai-usb-input.o'
    command=[('-Wp,-MMD,'+str(PRIVATE/'.samurai-usb-input.o.d')) if x.startswith('-Wp,-MMD,') else x for x in command]
    command[-1]=str(source);command[-2]=str(obj);command.insert(1,'-Werror')
    log=PRIVATE/'build.log';start=time.monotonic()
    with log.open('xb') as stream:
        child=subprocess.Popen(command,cwd=oldbuild,stdout=stream,stderr=subprocess.STDOUT)
        pid=child.pid;rc=child.wait()
    text=log.read_text();diagnostics=[line for line in text.splitlines() if re.search(r'warning:|error:',line,re.I)]
    assert rc==0 and not diagnostics,text
    raw=obj.read_bytes();assert raw[:4]==b'\x7fELF' and int.from_bytes(raw[18:20],'little')==183
    # Retain small exact source snapshots for the static IRQ-parent/lifecycle review.
    cache=HERE/'source-reference';cache.mkdir(exist_ok=True)
    source_refs={}
    for name in originals:
        p=original/name;dest=cache/name.replace('/','--');dest.write_bytes(p.read_bytes())
        source_refs[name]={'path':str(p),'sha256':sha(p),'snapshot_sha256':sha(dest)}
    unchanged=all(sha(Path(p))==h for p,h in before.items());assert unchanged
    r.update(passed=True,returncode=rc,pid=pid,owned_child_waited=True,seconds=round(time.monotonic()-start,3),
             helper_sha256=HELPER_SHA,fixed_backing=str(backing),source_sha256=SOURCE_SHA,
             decoder_sha256=sha(header),test_receipt_sha256=sha(HERE/'test-result.json'),
             saved_command_sha256=sha(cmdfile),command=command,cwd=str(oldbuild),
             object_path=str(obj),object_sha256=sha(obj),ELF_machine='AArch64',
             private_build_log=str(log),build_log_sha256=sha(log),diagnostics=diagnostics,
             source_references=source_refs,shared_and_original_inputs_before=before,
             shared_and_original_inputs_unchanged=unchanged,config_not_written=True,
             builder_sha256=sha(Path(__file__)))
except Exception as e:
    r.update(error=type(e).__name__,message=str(e))
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r.get(k) for k in ['passed','error','message','returncode','pid','seconds','object_sha256','shared_and_original_inputs_unchanged']},indent=2))
raise SystemExit(0 if r['passed'] else 1)
