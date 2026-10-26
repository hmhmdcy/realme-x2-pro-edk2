from pathlib import Path
import difflib,hashlib,json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');base=sdk/'work/libcamera224-r10-built/src/libcamera-v0.7.2'
failed=json.loads((private/'lifecycle-r10-candidate-threaded-host-private.log').read_text());assert failed['program_exit']==1 and failed['sensor_controls_restored'] and failed['all_formats_restored'] and failed['media_graph_restored']
r=dict(stage=224,rejected_candidate='99990.7.2-r10',client_exit=1,raw_stop_reconfiguration_to_rgb_observed=True,rgb_cancel_test_failed=True,
 root_cause='Unconverted output buffers were completed without inheriting the captured input cancellation status.',
 correction='Copy the input error/cancellation status to each pending converted output before completeBuffer.',
 controls_formats_graph_pm_restored=True,taint=0,fault_delta=failed['fault_delta'],r10_not_deployed=True,unchanged_lifecycle_program_and_assertions=True)
(here/'lifecycle-r10-cancellation-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n')
name='src/libcamera/pipeline/simple/simple.cpp';original=(base/name).read_text();text=original
old='#include "libcamera/internal/formats.h"';assert text.count(old)==1;text=text.replace(old,old+'\n#include "libcamera/internal/framebuffer.h"')
old='''\t\tfor (auto &[stream, buf] : outputs.outputs)
\t\t\tpipe->completeBuffer(outputs.request, buf);'''
new='''\t\tfor (auto &[stream, buf] : outputs.outputs) {
\t\t\tbuf->_d()->metadata().status = buffer->metadata().status;
\t\t\tpipe->completeBuffer(outputs.request, buf);
\t\t}'''
assert text.count(old)==1;text=text.replace(old,new)
patch='''Subject: [PATCH] simple: propagate capture cancellation to output buffers

When stream-off cancels an internal capture buffer, its unprocessed user
outputs must be cancelled too. Preserve the capture error/cancellation
status when completing them so a stopped request is not reported as a
successful frame without metadata or processed pixels.

---
'''
patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-capture-cancel-status.patch').write_text(patch)
p=private/'cancel-status-source'/name;assert not p.exists();p.parent.mkdir(parents=True);p.write_text(text)
recipe=sdk/'work/libcamera224-r11';assert not recipe.exists();recipe.mkdir()
for p in (sdk/'work/libcamera224-r10').iterdir():
 if p.is_file() and not p.is_symlink():shutil.copyfile(p,recipe/p.name)
patchname='0017-simple-capture-cancel-status.patch';(recipe/patchname).write_text(patch)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=10')==1;apk=apk.replace('pkgrel=10','pkgrel=11');marker='\t0016-simple-stop-live-requests.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+patchname+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0016-simple-stop-live-requests.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+'\n');(recipe/'APKBUILD').write_text(apk)
config=sdk/'work/samurai-camera-config224-r11';assert not config.exists();config.mkdir()
for n in ['APKBUILD','configuration.yaml','70-samurai-camera-heaps.rules','samurai-camera-heaps.conf','README.md']:shutil.copyfile(sdk/'work/samurai-camera-config224-r10'/n,config/n)
apk=(config/'APKBUILD').read_text();assert apk.count('pkgrel=5')==1;apk=apk.replace('pkgrel=5','pkgrel=6').replace('99990.7.2-r10','99990.7.2-r11');(config/'APKBUILD').write_text(apk)
proof=dict(stage=224,candidate_framework='99990.7.2-r11',candidate_config_stack='0.1.0-r6',patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),original_sources_sha256={name:hashlib.sha256(original.encode()).hexdigest()},source_files={name:hashlib.sha256(text.encode()).hexdigest()},capture_status_propagated_to_unprocessed_outputs=True,r9_r10_failed_candidates_preserved=True,phone_still_r8_r3=True)
(here/'cancel-status-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
build=(here/'build-r10-candidate.py').read_text().replace('r10','r11').replace('r5','r6').replace("cache=root/'work/libcamera224-built'","cache=root/'work/libcamera224-r10-built'").replace('r9_object_cache_preserved','r10_object_cache_preserved').replace('prior15','prior16').replace('0016-simple-stop-live-requests.patch','0017-simple-capture-cancel-status.patch').replace('stop-fix-source-validation.json','cancel-status-source-validation.json').replace('retained-r8-cache-copy-live','retained-r10-cache-copy-live')
compile(build,'full-r11-build224','exec');(here/'build-r11-candidate.py').write_text(build)
print(json.dumps(proof))
