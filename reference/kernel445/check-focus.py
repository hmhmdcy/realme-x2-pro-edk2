"""Compare exact production helper text, boundary inputs, and retained real FULLs."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';old=volume/'libcamera444-focused-ipe/src/libcamera-v0.7.2'
name='src/libcamera/pipeline/camss-vfe/hardware_focus.h'
def function(text):
 a=text.index('inline FocusStatistics measureLumaFocus(');z=text.index('\n}\n',a)+3;return text[a:z]
reference=function((old/name).read_text()).replace('measureLumaFocus','referenceLumaFocus',1)
optimized=function((tree/name).read_text())
glue='#pragma once\n#include <array>\n#include <optional>\n#include <vector>\n#include "libcamera/internal/software_isp/focus_stats.h"\nnamespace libcamera {\n'+reference+'\n'+optimized+'\n}\n'
(P/'focus_functions.h').write_text(glue)
source=HERE/'focus-contract.cpp';W='/private/camss445-focus';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
shutil.copyfile(source,work/'contract.cpp');shutil.copyfile(P/'focus_functions.h',work/'focus_functions.h')
fixtures=[];base=P.parent/'kernel442/runtime-collected-r9';state=json.loads((base/'state.json').read_text())
for label,row in state['captures'].items():
 sof=row['trace']['sof'];path=base/label/f'tone-{sof}-full.nv12';text=(base/label/'client.log').read_text()
 scores=re.findall(r'AF frame sof='+str(sof)+r' .* valid=1 score=(\d+) state=',text);assert len(scores)==1
 assert path.stat().st_size==row['width']*row['height']*3//2
 fixtures.append(dict(label=label,width=row['width'],height=row['height'],stride=row['width'],sof=sof,
  path=str(path),phone_path='/var/lib/samurai/k442-callback-timing-r9/'+label+'/'+path.name,
  sha256=hashlib.sha256(path.read_bytes()).hexdigest(),score=int(scores[0])))
(P/'focus-fixtures-private.json').write_text(json.dumps(fixtures,indent=2)+'\n')
q=subprocess.run(['g++','-std=c++20','-Os','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie','-I'+str(P),'-I'+str(tree/'include'),str(source),'-o',str(P/'focus-host')],capture_output=True)
(P/'focus-host-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:]
q=subprocess.run([str(P/'focus-host')],capture_output=True);(P/'focus-host-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:]
cases=json.loads(q.stdout)
for row in fixtures:
 q=subprocess.run([str(P/'focus-host'),row['path'],str(row['width']),str(row['height']),str(row['stride']),'1',str(row['score'])],capture_output=True)
 (P/(row['label']+'-host-focus.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:]
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-Os','-g','-Wall','-Wextra','-Werror','-I'+W,'-I'+T+'/include',W+'/contract.cpp','-o',W+'/focus-bench'],capture_output=True)
 (P/'focus-arm-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:]
 q=subprocess.run(['chroot',str(storage.SDK),W+'/focus-bench'],capture_output=True,timeout=90)
 (P/'focus-arm-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:];assert json.loads(q.stdout)==cases
 for i,row in enumerate(fixtures):
  dest=work/f'fixture-{i}-private.nv12';shutil.copyfile(row['path'],dest)
  q=subprocess.run(['chroot',str(storage.SDK),W+'/focus-bench',W+'/'+dest.name,str(row['width']),str(row['height']),str(row['stride']),'1',str(row['score'])],capture_output=True,timeout=30)
  (P/(row['label']+'-arm-focus.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1800:]
shutil.copyfile(work/'focus-bench',P/'focus-bench')
r=dict(stage=445,actual_reference_and_optimized_helper_text=True,host_asan_ubsan_and_actual_arm64=True,
 valid_cases=cases['valid_cases'],invalid_cases=cases['invalid_cases'],retained_actual_full_fixtures=len(fixtures),
 all_region_energy_sum_sample_counts_and_final_fom_exact=True,real_fixture_fom_matches_original_hardware_af_logs=True,
 compiler_os_werror=True,performance_requires_separate_phone_benchmark=True,benchmark_sha256=hashlib.sha256((P/'focus-bench').read_bytes()).hexdigest(),phone_accessed=False,passed=True)
(HERE/'focus-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
