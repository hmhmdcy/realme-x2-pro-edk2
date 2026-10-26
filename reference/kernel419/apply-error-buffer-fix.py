"""Keep completed ERROR buffers dequeueable, preserving unsafe-DMA poison."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a])
state=json.loads((HERE/'source-state.json').read_text());assert git('rev-parse','HEAD').decode().strip()==state['commit']
assert not git('status','--porcelain');git('checkout','-b','samurai-ipe-error-buffer419')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c';path=source/relative;before=path.read_text();after=before
needle='static void device_work(struct work_struct *work)';assert after.count(needle)==1
after=after.replace(needle,(HERE/'error-buffer-tail.c').read_text()+'\n'+needle)
needle='struct qcom_ipe_a5_frame_params *params = NULL;';assert after.count(needle)==1
after=after.replace(needle,needle+'\n\tbool queue_error = false;')
needle='''	mutex_unlock(&dev->hw_lock);
	if (ret && ret != -ECANCELED) {
		vb2_queue_error'''
replacement='''	/* ERROR buffers must remain dequeueable after a local rejection or
	 * proven quiesce. Queue poison hides even the done list from DQBUF.
	 * Preserve it only while per-frame DMA/backing ownership is unresolved.
	 */
	if (ret && ret != -ECANCELED)
		queue_error = image_transfer_owned(dev->a5);
	mutex_unlock(&dev->hw_lock);
	if (queue_error) {
		vb2_queue_error'''
assert after.count(needle)==1;after=after.replace(needle,replacement)
path.write_text(after);subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
(P/'camss-icp-a5-m2m.c.before').write_text(before);(P/'camss-icp-a5-m2m.c.proposed').write_text(after)
(P/'camss-icp-a5-ipe.h.proposed').write_bytes((source/'drivers/media/platform/qcom/camss/camss-icp-a5-ipe.h').read_bytes())
(HERE/'error-buffer-fix.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
state.update(parent=state['commit'],branch='samurai-ipe-error-buffer419',adapter_prepared=True,adapter_committed=False,
    quiesced_error_buffers_dequeueable=True,unresolved_transfer_queue_poison_kept=True,
    userspace_library_unchanged_from418=True,phone_accessed=True,last_device_evidence_stage=419,
    adapter_source_sha256=hashlib.sha256(after.encode()).hexdigest())
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
