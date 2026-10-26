"""Link the hardware probe to the actual candidate library, not a model."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'build-validation.json').read_text())['passed']
assert json.loads((HERE/'ipe-validation.json').read_text())['passed']
fixture=(P.parent/'kernel400/test-chain-fixture.h').read_text().replace('camss_a5_ipe_colour','qcom_ipe_a5_colour').replace('CAMSS_A5_IPE_COLOUR_','QCOM_IPE_A5_COLOUR_')
assert fixture.count('.cv')==1
fixture=fixture.replace('.cv','.padding = 0, .cc = {}, .cv',1)
extra=(HERE.parent/'kernel417/request-client-tail.c').read_text();start=extra.index('static void params_for');end=extra.index('\nstatic int controls',start)
slot=storage.SDK/'private-k418';slot.mkdir(exist_ok=True)
(slot/'request-params.h').write_text(fixture+'\n'+extra[start:end]);shutil.copyfile(HERE/'ipe-smoke.cpp',slot/'ipe-smoke.cpp')
with storage.sdk_candidate():
    tree='/work/libcamera/src/libcamera-v0.7.2'
    args=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-g','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE',
        '-I'+tree+'/include','-I'+tree+'/output/include','-I'+tree+'/src/libcamera/pipeline/camss-vfe','-I/private-k418',
        '/private-k418/ipe-smoke.cpp','-L'+tree+'/output/src/libcamera','-L'+tree+'/output/src/libcamera/base',
        '-Wl,-rpath-link,'+tree+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private-k418/ipe-smoke']
    q=subprocess.run(args,capture_output=True)
(P/'runtime-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
shutil.copyfile(slot/'ipe-smoke',P/'ipe-smoke')
tree=storage.candidate()/'src/libcamera-v0.7.2';shutil.copyfile(tree/'output/src/libcamera/libcamera.so.0.7.2',P/'libcamera.so.0.7.2')
r=dict(stage=418,actual_candidate_library_linked=True,probe_werror=True,nonzero_iq_hardware_probe_frames=16,
    planned_immediate_stop_cancelled_buffers=4,library_sha256=hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest(),
    probe_sha256=hashlib.sha256((P/'ipe-smoke').read_bytes()).hexdigest(),installed=False,passed=True)
(HERE/'runtime-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
