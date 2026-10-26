"""Add explicit CameraLens lifetime controls and apply them to the generic Simple pipeline."""
from pathlib import Path
import difflib,hashlib,json
import host
R=Path(__file__).resolve().parent
S=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera273-r21-built/src/libcamera-v0.7.2')
paths=['include/libcamera/internal/camera_lens.h','src/libcamera/camera_lens.cpp','src/libcamera/pipeline/simple/simple.cpp']
before={n:(S/n).read_text() for n in paths};after=dict(before)
def change(name,old,new):
 assert after[name].count(old)==1,(name,old);after[name]=after[name].replace(old,new)
change(paths[0],'\tint init();\n\tint setFocusPosition','\tint init();\n\tint open();\n\tvoid close();\n\tint setFocusPosition')
anchor='/**\n * \\brief This function sets the focal point of the lens to a specific position.'
addition='''/**
 * \\brief Open the lens subdevice for camera operation
 *
 * Opening an already open lens succeeds without acquiring another descriptor.
 * \\return 0 on success or a negative error code otherwise
 */
int CameraLens::open()
{
\treturn subdev_->isOpen() ? 0 : subdev_->open();
}

/**
 * \\brief Close the lens subdevice when camera operation ends
 *
 * This permits the kernel lens driver to release its power reference while the
 * CameraLens instance and its model information remain available.
 */
void CameraLens::close()
{
\tsubdev_->close();
}

'''
change(paths[1],anchor,addition+anchor)
anchor='#include "libcamera/internal/camera_sensor.h"';assert anchor in after[paths[2]]
change(paths[2],anchor,'#include "libcamera/internal/camera_lens.h"\n'+anchor)
anchor='''int SimpleCameraData::init()
{
\tSimplePipelineHandler *pipe = SimpleCameraData::pipe();
\tint ret;
'''
replacement=anchor+'''
\t/* Keep discovery separate from the operational lens power lifetime. */
\tif (CameraLens *lens = sensor_->focusLens())
\t\tlens->close();
'''
change(paths[2],anchor,replacement)
anchor='''\tret = video->streamOn();
\tif (ret < 0) {
\t\tstop(camera);
\t\treturn ret;
\t}

\tif (data->useConversion_) {'''
replacement='''\tret = video->streamOn();
\tif (ret < 0) {
\t\tstop(camera);
\t\treturn ret;
\t}

\t/* Sensor streaming establishes shared camera I/O supplies first. */
\tif (CameraLens *lens = data->sensor_->focusLens()) {
\t\tret = lens->open();
\t\tif (ret) {
\t\t\tstop(camera);
\t\t\treturn ret;
\t\t}
\t}

\tif (data->useConversion_) {'''
change(paths[2],anchor,replacement)
anchor='''\tdata->clearIncompleteRequests();
\tdata->conversionBuffers_.clear();

\treleasePipeline(data);'''
replacement='''\tdata->clearIncompleteRequests();
\tdata->conversionBuffers_.clear();

\tif (CameraLens *lens = data->sensor_->focusLens())
\t\tlens->close();

\treleasePipeline(data);'''
change(paths[2],anchor,replacement)
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in paths)
header='''Subject: [PATCH] libcamera: simple: scope lens device ownership to streaming

A lens subdevice opened during discovery may keep its regulator enabled for
the entire CameraManager lifetime. Give CameraLens explicit descriptor lifetime
operations and release the descriptor after Simple camera discovery. Reopen it
after sensor streaming has established shared I/O power and close it on every
normal or failed start/stop path. Existing pipeline handlers retain their
previous lifetime until they explicitly opt in.

This does not implement an autofocus algorithm or map lens codes to dioptres.
---
'''
name='0026-simple-lens-stream-lifetime.patch';(R/name).write_text(header+patch)
out=host.PRIVATE/'lifecycle-source-candidate';out.mkdir(mode=0o700,exist_ok=True)
for name,text in after.items():p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
report=dict(stage=275,patch_count=26,source_before_files={n:hashlib.sha256(before[n].encode()).hexdigest() for n in paths},source_files={n:hashlib.sha256(after[n].encode()).hexdigest() for n in paths},
 explicit_lens_lifetime=True,simple_only_opt_in=True,sensor_stream_before_lens_open=True,no_model_board_or_application_conditionals=True,no_af_or_dioptre_mapping_implemented=True,not_built_or_deployed=True)
(R/'lifecycle-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
