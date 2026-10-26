"""Build against the actual retained r24 libipa helper and shared libcamera base."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
REPO=Path('/home/cy122/x2pro-linux/libcamera-camss299-reference');commit='fda77c39097fa97c7ece76f48dd68eede1877501'
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==commit
source=subprocess.check_output(['git','-C',str(REPO),'show','HEAD:src/libcamera/pipeline/camss/camss_params.h']).decode()
before=source
source=source.replace('#include <linux/camss-config.h>','#include <linux/qcom-camss-config.h>')
source=source.replace('#include "../../../ipa/libipa/v4l2_params.h"','#include "v4l2_params.h"')
source=source.replace('\tColorCorrect,','\tColorCorrect,\n\tAecBhist,')
needle='CAMSS_DEFINE_BLOCK_TYPE(ColorCorrect, color_correct, COLOR_CORRECT);';assert needle in source
source=source.replace(needle,needle+'\nCAMSS_DEFINE_BLOCK_TYPE(AecBhist, aec_bhist, AEC_BHIST);')
retry='--retry' in sys.argv
p=HERE/'ipa/params.h'
if retry:assert p.read_text()==source
else:assert not p.exists();p.write_text(source)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss299-encoder'
if retry:assert stage.is_dir()
else:assert not stage.exists();stage.mkdir()
for name in ['params.h','parameter_encoder.h','parameter_encoder.cpp','encoder_contract.cpp']:shutil.copyfile(HERE/'ipa'/name,stage/name)
uapi=stage/'uapi/linux';uapi.mkdir(parents=True,exist_ok=retry);(uapi/'media').mkdir(exist_ok=retry)
KERNEL=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
for name in ['qcom-camss-config.h','media/v4l2-isp.h']:shutil.copyfile(KERNEL/'include/uapi/linux'/name,uapi/name)
tree='/work/libcamera278-r24-r3-built/src/libcamera-v0.7.2';prefix='/candidate278-r24';work='/private/camss299-encoder'
args=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-DLIBCAMERA_BASE_PRIVATE',
 '-I'+work+'/uapi','-I'+tree+'/include','-I'+tree+'/output/include','-I'+prefix+'/usr/include/libcamera','-I'+tree+'/src/ipa/libipa','-I'+work,
 work+'/parameter_encoder.cpp',work+'/encoder_contract.cpp',tree+'/src/ipa/libipa/v4l2_params.cpp',
 '-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera-base','-o',work+'/encoder-contract']
q=subprocess.run(args,capture_output=True,timeout=180);(P/('ipa-encoder-build-r2-private.log' if retry else 'ipa-encoder-build-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+prefix+'/usr/lib',work+'/encoder-contract',work+'/packet-private.bin'],capture_output=True,timeout=30)
(P/'ipa-encoder-contract-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
packet=(stage/'packet-private.bin').read_bytes();assert len(packet)==56
shutil.copyfile(stage/'encoder-contract',P/'ipa-encoder-contract-aarch64-private');(P/'ipa-encoder-packet-private.bin').write_bytes(packet)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(stage=299,build_attempt=2 if retry else 1,upstream_camss_repository='jwrdegoede/libcamera',upstream_commit=commit,
 reused_camss_params_header_sha256=hashlib.sha256(before.encode()).hexdigest(),adaptations=['existing qcom-camss-config.h include','existing libipa helper include','typed BHIST trait'],
 actual_r24_libipa_v4l2_params_used=True,actual_r24_libcamera_base_linked=True,aarch64_werror_compile_pass=True,
 native_contract_exit=q.returncode,packet_bytes=len(packet),packet_sha256=sha(P/'ipa-encoder-packet-private.bin'),
 wire_matches_independent_c_structures=True,invalid_capacity_alignment_roi_nonfinite_and_overflow_inputs_rejected=True,
 rejected_inputs_do_not_mutate_buffer=True,source_files={p.name:sha(p) for p in (HERE/'ipa').glob('*')},
 source_helper_sha256=sha(SDK/tree.lstrip('/')/'src/ipa/libipa/v4l2_params.cpp'),
 kernel_uapi_unchanged=True,encoder_staging_only=True,pipeline_and_ipa_module_not_yet_integrated=True,not_installed=True)
(HERE/'ipa-encoder-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
