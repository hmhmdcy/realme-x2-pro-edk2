"""Pin the real export's owner instead of layering another DMA-BUF file."""
from pathlib import Path
import difflib,importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;relative=Path('drivers/media/platform/qcom/camss')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
source=mount.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='c0fc6e1648f38ebac807a38af8ad3c4dcfeb447c' and not git('status','--porcelain')
# The uninstalled wrapper cannot order a deferred base-file release. Preserve
# its commit and revert it before adding the allocator's ownership parameter.
git('revert','--no-edit','c0fc6e1648f38ebac807a38af8ad3c4dcfeb447c')
state['changed'].remove('camss-icp-a5-m2m-export.h')
state['export_wrapper_prototype_commit']='c0fc6e1648f38ebac807a38af8ad3c4dcfeb447c'
state['export_wrapper_prototype_reverted_commit']=git('rev-parse','HEAD')
for leaf in ['camss-icp-a5-m2m-export.h','fix-export-owner.py']:
 shutil.copyfile(HERE/leaf,P/('unused-'+leaf));(HERE/leaf).unlink()
framework=['drivers/media/common/videobuf2/videobuf2-dma-sg.c','include/media/videobuf2-dma-sg.h']
for name in framework:(P/(Path(name).name+'.before')).write_bytes((source/name).read_bytes())
p=source/framework[0];s=p.read_text()
needle='''static struct dma_buf *vb2_dma_sg_get_dmabuf(struct vb2_buffer *vb,
\t\t\t\t\t     void *buf_priv,
\t\t\t\t\t     unsigned long flags)'''
replacement='''struct dma_buf *vb2_dma_sg_get_dmabuf_owner(struct vb2_buffer *vb,
\t\t\t\t\t void *buf_priv, unsigned long flags,
\t\t\t\t\t struct module *owner)'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='\texp_info.ops = &vb2_dma_sg_dmabuf_ops;';assert s.count(needle)==1;s=s.replace(needle,needle+'\n\texp_info.owner = owner;')
needle='''/*********************************************/
/*       callbacks for DMABUF buffers        */'''
wrapper='''/* The caller's owner must keep the allocation device and this allocator
 * valid through the exported file's release. A modular caller already has
 * an allocator dependency; use its bound owner, including for deferred fput.
 */
EXPORT_SYMBOL_GPL(vb2_dma_sg_get_dmabuf_owner);

static struct dma_buf *vb2_dma_sg_get_dmabuf(struct vb2_buffer *vb,
\t\t\t\t\t     void *buf_priv,
\t\t\t\t\t     unsigned long flags)
{
\treturn vb2_dma_sg_get_dmabuf_owner(vb, buf_priv, flags, THIS_MODULE);
}

'''
assert s.count(needle)==1;s=s.replace(needle,wrapper+needle);p.write_text(s)
p=source/framework[1];s=p.read_text();needle='extern const struct vb2_mem_ops vb2_dma_sg_memops;';assert s.count(needle)==1
s=s.replace(needle,'''struct dma_buf;
struct module;

/* The owner must retain the DMA allocation device and the allocator module. */
struct dma_buf *vb2_dma_sg_get_dmabuf_owner(struct vb2_buffer *vb, void *buf_priv,
\t\t\t\t\t unsigned long flags, struct module *owner);

'''+needle);p.write_text(s)
name='camss-icp-a5-m2m.c';p=source/relative/name;s=p.read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('\tu32 users;','\tu32 users;\n\tstruct vb2_mem_ops memory_ops;')
needle='static struct ipe_context *file_context('
callback='''/* Export the original SG buffer with the platform owner pinned. The owner
 * depends on this adapter, which depends on DMA-SG; the DMA-BUF core drops
 * that pin only after allocator release, including delayed fput and VMAs.
 */
static struct dma_buf *owned_export_buffer(struct vb2_buffer *vb, void *private,
\t\t\t\t\t  unsigned long flags)
{
\tstruct ipe_context *ctx = vb2_get_drv_priv(vb->vb2_queue);

\treturn vb2_dma_sg_get_dmabuf_owner(vb, private, flags, ctx->dev->owner);
}

'''
replace(needle,callback+needle)
replace('q->mem_ops = &vb2_dma_sg_memops;','q->mem_ops = &ctx->dev->memory_ops;')
replace('INIT_LIST_HEAD(&dev->contexts);','INIT_LIST_HEAD(&dev->contexts);\n\tdev->memory_ops = vb2_dma_sg_memops;\n\tdev->memory_ops.get_dmabuf = owned_export_buffer;')
replace('"\\\"first_error\\\":%d,\\\"direct_completed\\\":%llu,','"\\\"owner_refs\\\":%d,\\\"first_error\\\":%d,\\\"direct_completed\\\":%llu,')
replace('\t\tdev->first_error, (unsigned long long)dev->direct_completed,','\t\tmodule_refcount(dev->owner), dev->first_error,\n\t\t(unsigned long long)dev->direct_completed,')
p.write_text(s);(P/(name+'.proposed')).write_text(s)
for name in framework:(P/(Path(name).name+'.proposed')).write_bytes((source/name).read_bytes())
git('diff','--check');git('add','--',str(relative/'camss-icp-a5-m2m.c'),*framework)
git('commit','-m','media: vb2 dma-sg: allow an exported buffer to retain its DMA-domain owner')
state.update(commit=git('rev-parse','HEAD'),framework_changed=framework,exported_buffer_owner_pins=True,additive_sg_export_owner_api=True,common_vb2_struct_abi_unchanged=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
patch=''
for name,leaf in [(str(relative/n),n) for n in state['changed']]+[(n,Path(n).name) for n in framework]:
 a=(P/(leaf+'.before')).read_text();b=(P/(leaf+'.proposed')).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
(HERE/'direct-dma.patch').write_text(patch)
p=HERE/'build-intree.py';s=p.read_text().replace('runtime_modules=set(modules)',"runtime_modules=set(modules)|{vb2/'videobuf2-dma-sg.ko'}");p.write_text(s)
(HERE/'export-owner-design.json').write_text(json.dumps(dict(stage=388,additive_dma_sg_owner_parameter=True,standard_get_dmabuf_behavior_unchanged=True,public_vb2_struct_abi_unchanged=True,real_export_file_pins_owner_until_allocator_release=True,wrapper_not_used_due_to_deferred_base_fput_and_global_observer_refs=True,temporary_standard_sg_module_replacement_required=True,not_yet_runtime_verified=True),indent=2)+'\n')
print(json.dumps(state,indent=2))
