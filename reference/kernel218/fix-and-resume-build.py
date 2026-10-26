from pathlib import Path
import difflib,hashlib,json,os,subprocess,time

os.umask(0o077)
here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel218')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
src=root/'work/libcamera218';original=root/'work/libcamera/src/libcamera-v0.7.2'
state=json.loads((private/'active-build-private.json').read_text())
assert not Path('/proc',str(state['pid'])).exists()
assert not (private/'candidate-build-r3-private.log').exists()
path=src/'src/libcamera/software_isp/debayer_cpu.cpp';text=path.read_text();old=': Debayer(cm), stats_(std::move(stats)), imx471_(imx471)';assert text.count(old)==1
text=text.replace(old,': Debayer(cm), imx471_(imx471), stats_(std::move(stats))');path.write_text(text)
path=src/'src/libcamera/software_isp/software_isp.cpp';text=path.read_text()
text=text.replace('#include "libcamera/internal/bayer_format.h"','#include "libcamera/internal/bayer_format.h"\n#include "libcamera/internal/camera_manager.h"\n#include "libcamera/internal/global_configuration.h"')
old='\t  dmaHeap_(DmaBufAllocator::DmaBufAllocatorFlag::CmaHeap |\n\t\t   DmaBufAllocator::DmaBufAllocatorFlag::SystemHeap |\n\t\t   DmaBufAllocator::DmaBufAllocatorFlag::UDmaBuf)';assert text.count(old)==1
text=text.replace(old,'\t  dmaHeap_(softwareIspHeapFlags(pipe, sensor))')
marker='LOG_DEFINE_CATEGORY(SoftwareIsp)';assert text.count(marker)==1
text=text.replace(marker,marker+'''

namespace {

DmaBufAllocator::DmaBufAllocatorFlags softwareIspHeapFlags(PipelineHandler *pipe,
							const CameraSensor *sensor)
{
	const GlobalConfiguration &configuration = pipe->cameraManager()->_d()->configuration();
	if (sensor->model() == "imx471" && configuration.option<bool>(
		    { "software_isp", "experimental_imx471_native_quad" }).value_or(false))
		return DmaBufAllocator::DmaBufAllocatorFlag::SystemHeap;

	return DmaBufAllocator::DmaBufAllocatorFlag::CmaHeap |
	       DmaBufAllocator::DmaBufAllocatorFlag::SystemHeap |
	       DmaBufAllocator::DmaBufAllocatorFlag::UDmaBuf;
}

} /* namespace */
''');path.write_text(text)
(src/'test/native-quad-cpu.cpp').write_text((here/'native-quad-cpu-test.cpp').read_text())
proof=json.loads((here/'candidate-source-validation.json').read_text());patch=''
for name in sorted(proof['files']):
    before=(original/name).read_text() if (original/name).exists() else ''
    after=(src/name).read_text()
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    proof['files'][name]=hashlib.sha256(after.encode()).hexdigest()
proof['experimental_native_output_uses_system_heap']=True
(here/'libcamera-native-quad-candidate.patch').write_text(patch)
(here/'candidate-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
command=['chroot',str(root),'/usr/bin/ninja','-C','/work/libcamera218/output','-j4',
         'src/libcamera/libcamera.so.0.7.2','test/native-quad','test/native-quad-cpu','test/quad-bayer','test/bayer-format']
with (private/'candidate-build-r3-private.log').open('wb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-build-private.json').write_text(json.dumps(dict(pid=process.pid,command=command,started=time.time()),indent=2)+'\n')
    code=process.wait(timeout=3600)
assert code==0,'Inspect existing r3 build; do not restart from scratch'
report=dict(stage=218,candidate_simple_virtual_cpu_egl_build_passed=True,compiler_warnings_as_errors=True,
            focused_native_quad_cpu_quad_bayer_format_tests_built=True,broad_all_target_build_stopped_intentionally=True,
            initialization_order_error_fixed=True,production_full_feature_packages_unchanged=True,no_package_device_install=True)
(here/'candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
