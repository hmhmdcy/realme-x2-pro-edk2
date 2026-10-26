"""Use DMA-BUF imports in the IPE core and standard DMA-SG vb2 queues."""
from pathlib import Path
import difflib,importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;relative=Path('drivers/media/platform/qcom/camss')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
source=mount.mounted_build().parent/'source354'
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-ipe.h','camss-icp-a5-m2m.c','camss-icp-a5-boot-test.c','camss-icp-a5-core.c','Makefile','Kconfig']
before={n:(source/relative/n).read_text() for n in names};after=dict(before)
def edit(name,a,b):
 assert after[name].count(a)==1,(name,a,after[name].count(a));after[name]=after[name].replace(a,b)
edit('camss-icp-a5-boot.h','#include "camss-icp-a5.h"','#include "camss-icp-a5.h"\n#include "camss-icp-a5-dma.h"')
edit('camss-icp-a5-boot.h','struct camss_a5_fw_memory request, image_input, image_output;','struct camss_a5_fw_memory request, image_input, image_output;\n\tstruct camss_a5_dma_image dma_input, dma_output;')
edit('camss-icp-a5-boot.h','u32 frames_submitted, frames_completed, transfer_maps, transfer_unmaps;','u32 frames_submitted, frames_completed, transfer_maps, transfer_unmaps;\n\tu32 direct_frames, copy_frames;')
edit('camss-icp-a5-ipe.h','\tconst void *input;\n\tvoid *output;','\tconst void *input;\n\tvoid *output;\n\tstruct dma_buf *input_dma, *output_dma;\n\tu32 input_offset, output_offset;')
edit('camss-icp-a5-ipe.h',' * The core owns all DMA backing and retains it after',' * Select either CPU pointers (legacy fixture) or two DMA-BUF references.\n * QBUF/DQBUF ownership is explicit; do not access or resubmit live images.\n * The core takes its own import references and retains all backing after')
edit('camss-icp-a5-core.c','MODULE_LICENSE("GPL");','MODULE_LICENSE("GPL");\nMODULE_IMPORT_NS("DMA_BUF");')
name='camss-icp-a5-boot.c'
edit(name,'a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu;','a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu ||\n\t       a5->dma_input.buffer || a5->dma_output.buffer;')
anchor='static int free_memory(struct camss_a5 *a5)'
helper='''static int free_imported_images(struct camss_a5 *a5)
{
 int ret;

 if (a5->ipe_dma_pending || a5->request_fw_mapped)
  return -EBUSY;
 ret = camss_a5_dma_image_release(&a5->dma_output);
 return ret ?: camss_a5_dma_image_release(&a5->dma_input);
}

'''.replace(' ', ' ',1)
edit(name,anchor,helper+anchor)
edit(name,'\tif (a5->cpu_enabled || a5->ipe_dma_pending)\n\t\treturn -EBUSY;\n\tcapture_shared_state(a5);','\tif (a5->cpu_enabled || a5->ipe_dma_pending)\n\t\treturn -EBUSY;\n\tret = free_imported_images(a5);\n\tif (ret)\n\t\treturn ret;\n\tcapture_shared_state(a5);')
edit(name,'\ta5->frames_submitted = a5->frames_completed = 0;','\ta5->frames_submitted = a5->frames_completed = 0;\n\ta5->direct_frames = a5->copy_frames = 0;')
edit(name,'\tif (a5->ipe_dma_pending || a5->request_fw_mapped)\n\t\treturn -EBUSY;\n\tfor (i = 0; i < ARRAY_SIZE(memories); i++) {','\tif (a5->ipe_dma_pending || a5->request_fw_mapped)\n\t\treturn -EBUSY;\n\tret = free_imported_images(a5);\n\tif (ret)\n\t\treturn ret;\n\tfor (i = 0; i < ARRAY_SIZE(memories); i++) {')
edit(name,'\tu32 stripe_bytes, iq_offset, scratch_offset, bl_offset;\n\tint ret, cleanup;','\tu32 stripe_bytes, iq_offset, scratch_offset, bl_offset;\n\tbool direct;\n\tint ret, cleanup;')
edit(name,'''\tif (!a5 || !session || !job ||
\t    !job->input || !job->output ||''','''\tif (!a5 || !session || !job)
\t\treturn -EINVAL;
\tdirect = job->input_dma || job->output_dma;
\tif ((direct && (!job->input_dma || !job->output_dma || job->input || job->output)) ||
\t    (!direct && (!job->input || !job->output || job->input_offset || job->output_offset)) ||''')
edit(name,'\t    a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu) {','\t    a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu ||\n\t    a5->dma_input.buffer || a5->dma_output.buffer) {')
edit(name,'''\tret = transfer_alloc(a5, &a5->image_input, IMAGE_INPUT_IOVA, PAGE_ALIGN(input_bytes));
\tif (ret)
\t\tgoto release;
\tret = transfer_alloc(a5, &a5->image_output, IMAGE_OUTPUT_IOVA, PAGE_ALIGN(output_bytes));
\tif (ret)
\t\tgoto release;''','''\tif (direct) {
\t\tret = camss_a5_dma_image_map(a5->dev, &a5->dma_input, job->input_dma,
\t\t\t\t\t     job->input_offset, input_bytes, DMA_TO_DEVICE);
\t\tif (!ret)
\t\t\tret = camss_a5_dma_image_map(a5->dev, &a5->dma_output, job->output_dma,
\t\t\t\t\t\t     job->output_offset, output_bytes, DMA_FROM_DEVICE);
\t\tif (!ret)
\t\t\tret = camss_a5_dma_images_disjoint(&a5->dma_input, &a5->dma_output);
\t} else {
\t\tret = transfer_alloc(a5, &a5->image_input, IMAGE_INPUT_IOVA, PAGE_ALIGN(input_bytes));
\t\tif (!ret)
\t\t\tret = transfer_alloc(a5, &a5->image_output, IMAGE_OUTPUT_IOVA, PAGE_ALIGN(output_bytes));
\t}
\tif (ret)
\t\tgoto release;''')
edit(name,'\tmemcpy(a5->image_input.cpu, job->input, input_bytes);\n\tmemset(a5->image_output.cpu, 0xa5, output_bytes);','\tif (!direct) {\n\t\tmemcpy(a5->image_input.cpu, job->input, input_bytes);\n\t\tmemset(a5->image_output.cpu, 0xa5, output_bytes);\n\t}')
edit(name,'frame.input = (struct camss_a5_ipe_buffer){ IMAGE_INPUT_IOVA, input_bytes };','frame.input = (struct camss_a5_ipe_buffer){ direct ? a5->dma_input.iova : IMAGE_INPUT_IOVA, input_bytes };')
edit(name,'frame.output = (struct camss_a5_ipe_buffer){ IMAGE_OUTPUT_IOVA, output_bytes };','frame.output = (struct camss_a5_ipe_buffer){ direct ? a5->dma_output.iova : IMAGE_OUTPUT_IOVA, output_bytes };')
edit(name,'\t\tmemcpy(job->output, a5->image_output.cpu, output_bytes);','\t\tif (direct)\n\t\t\ta5->direct_frames++;\n\t\telse {\n\t\t\ta5->copy_frames++;\n\t\t\tmemcpy(job->output, a5->image_output.cpu, output_bytes);\n\t\t}')
name='camss-icp-a5-m2m.c'
edit(name," * Initial unity-scale NV12/NV21 processing uses the core's owned DMA copies."," * Unity-scale NV12/NV21 uses core-owned DMA-BUF imports; no image CPU copy.")
edit(name,'#include <linux/iosys-map.h>','#include <linux/fcntl.h>')
edit(name,'#include <media/videobuf2-vmalloc.h>','#include <media/videobuf2-dma-sg.h>')
edit(name,'u64 jobs, completed, cancelled, failed, starts, stops;','u64 jobs, completed, direct_completed, cancelled, failed, starts, stops;')
a=after[name].index('struct ipe_cpu_buffer {');b=after[name].index('static int ensure_session(',a)
after[name]=after[name][:a]+'''/* An MMAP export pins vb2 backing independently of queue/file lifetime;
 * imported buffers already carry a DMA-BUF. The core takes another reference
 * before starting DMA, including on uncertain completion/reset failure.
 */
static struct dma_buf *image_buffer(struct vb2_buffer *vb)
{
 struct dma_buf *buffer = vb->planes[0].dbuf;

 if (buffer) {
  get_dma_buf(buffer);
  return buffer;
 }
 if (vb->memory != V4L2_MEMORY_MMAP || !vb->vb2_queue->mem_ops->get_dmabuf)
  return ERR_PTR(-EINVAL);
 buffer = vb->vb2_queue->mem_ops->get_dmabuf(vb, vb->planes[0].mem_priv, O_RDWR);
 return buffer ?: ERR_PTR(-ENOMEM);
}

''' +after[name][b:]
edit(name,'\tstruct ipe_cpu_buffer input = {}, output = {};','\tstruct dma_buf *input = NULL, *output = NULL;')
edit(name,'\tint ret = -ECANCELED, end_ret;','\tint ret = -ECANCELED;')
a=after[name].index('\tret = cpu_begin(&src->vb2_buf, &input);');b=after[name].index('\tret = ensure_session(ctx);',a)
after[name]=after[name][:a]+'''\tinput = image_buffer(&src->vb2_buf);
\tif (IS_ERR(input)) {
\t\tret = PTR_ERR(input);
\t\tinput = NULL;
\t\tgoto finish;
\t}
\toutput = image_buffer(&dst->vb2_buf);
\tif (IS_ERR(output)) {
\t\tret = PTR_ERR(output);
\t\toutput = NULL;
\t\tgoto finish;
\t}
\tjob.input_dma = input;
\tjob.output_dma = output;
\tjob.input_offset = src->vb2_buf.planes[0].data_offset;
\tjob.output_offset = dst->vb2_buf.planes[0].data_offset;
''' +after[name][b:]
edit(name,'''\t/* The original input/output are CPU copied by the core, so even a
\t * retained engine transaction owns separate backing, not vb2 memory.
\t */''','''\t/* On uncertain completion the core retains its own attachment and
\t * DMA-BUF reference. Queue teardown cannot free that backing. A failed
\t * quiesce keeps the platform owner and PM pin for explicit cleanup.
\t */''')
a=after[name].index('finish:\n\tend_ret = cpu_end(&output);');b=after[name].index('\tif (!ret && READ_ONCE(ctx->aborting))',a)
after[name]=after[name][:a]+'''finish:
\tif (output)
\t\tdma_buf_put(output);
\tif (input)
\t\tdma_buf_put(input);
''' +after[name][b:]
edit(name,'\telse\n\t\tdev->completed++;','\telse {\n\t\tdev->completed++;\n\t\tdev->direct_completed++;\n\t}')
edit(name,'q->mem_ops = &vb2_vmalloc_memops;','q->mem_ops = &vb2_dma_sg_memops;')
edit(name,'"\\\"cancelled\\\":%llu,\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",','"\\\"direct_completed\\\":%llu,\\\"cancelled\\\":%llu,\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",')
edit(name,'\t\t(unsigned long long)dev->cancelled, (unsigned long long)dev->failed,','\t\t(unsigned long long)dev->direct_completed,\n\t\t(unsigned long long)dev->cancelled, (unsigned long long)dev->failed,')
name='camss-icp-a5-boot-test.c'
edit(name,r'\"image_frames\":%u,\"frames_completed\":%u,',r'\"direct_frames\":%u,\"copy_frames\":%u,\"imported_buffers\":%u,\"imported_bytes\":%llu,\"image_frames\":%u,\"frames_completed\":%u,')
edit(name,'\t\t  a5->frames_submitted, a5->frames_completed, a5->transfer_maps, a5->transfer_unmaps,','\t\t  a5->direct_frames, a5->copy_frames,\n\t\t  !!a5->dma_input.buffer + !!a5->dma_output.buffer,\n\t\t  (unsigned long long)a5->dma_input.bytes + a5->dma_output.bytes,\n\t\t  a5->frames_submitted, a5->frames_completed, a5->transfer_maps, a5->transfer_unmaps,')
after['Makefile']+='\nqcom-camss-icp-a5-core-y += camss-icp-a5-dma.o\n'
edit('Kconfig','config VIDEO_QCOM_CAMSS_ICP_A5_M2M\n\ttristate\n\tdepends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && VIDEO_DEV\n\tselect V4L2_MEM2MEM_DEV\n\tselect VIDEOBUF2_VMALLOC','config VIDEO_QCOM_CAMSS_ICP_A5_M2M\n\ttristate\n\tdepends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && VIDEO_DEV\n\tselect V4L2_MEM2MEM_DEV\n\tselect VIDEOBUF2_DMA_SG')
edit('Kconfig','config VIDEO_QCOM_CAMSS_ICP_A5_CORE\n\ttristate','config VIDEO_QCOM_CAMSS_ICP_A5_CORE\n\ttristate\n\tselect DMA_SHARED_BUFFER')
for leaf in ['camss-icp-a5-dma.c','camss-icp-a5-dma.h']:
 names.append(leaf);before[leaf]='';after[leaf]=(HERE/leaf).read_text()
patch=''
for leaf in names:
 (P/(leaf+'.before')).write_text(before[leaf]);(P/(leaf+'.proposed')).write_text(after[leaf])
 patch+=''.join(difflib.unified_diff(before[leaf].splitlines(True),after[leaf].splitlines(True),fromfile='a/'+str(relative/leaf) if before[leaf] else '/dev/null',tofile='b/'+str(relative/leaf)))
(HERE/'direct-dma.patch').write_text(patch)
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=388,parent='8003933b7e31e4b5f4d27d21789d42da686831ba',changed=names,core_owns_import_lifetime=True,standard_vb2_dma_sg=True,board_and_libcamera_unchanged=True,installed=False),indent=2)+'\n')
print('Prepared native DMA-BUF core and DMA-SG m2m queue proposal.')
