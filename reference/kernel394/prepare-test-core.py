"""Prepare a temporary, compile-guarded lost-valid-frame-ACK experiment."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='64aaf4f78c05f0912e658780294fbded531d87ce' and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';before=(source/relative).read_text();after=before
declarations='''#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK
/* Temporary experiment only: this code is absent from production builds. */
static unsigned int test_drop_frame_ack;
module_param_named(test_drop_frame_ack, test_drop_frame_ack, uint, 0600);
static unsigned int test_dropped_frame_acks;
module_param_named(test_dropped_frame_acks, test_dropped_frame_acks, uint, 0400);
#endif
'''
a='#include "camss-icp-a5-ipe.h"\n';assert after.count(a)==1;after=after.replace(a,a+'\n'+declarations,1)
drop='''#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK
	/* Tokens, opcode, size and firmware status have already been checked.
	 * Consume one real successful frame ACK but do not wake its waiter.
	 * The unchanged timeout path must retain DMA until reset confirms idle.
	 */
	if (!error && type == IPE_ASYNC_INDIRECT_ACK &&
	    a5->session_opcode == IPE_FRAME_PROCESS &&
	    cmpxchg(&test_drop_frame_ack, 1, 0) == 1) {
		test_dropped_frame_acks++;
		dev_info(a5->dev, "FAULT_TEST dropped validated frame ACK once\\n");
		return;
	}
#endif
'''
a='\t/* A successful packet must not erase a concurrent watchdog/protocol\n';assert after.count(a)==1;after=after.replace(a,drop+a,1)
a='''	ret = quiesce_locked(a5);
	if (ret)
		return ret;
	/* Retire all firmware DMA aliases'''
b='''	ret = quiesce_locked(a5);
	if (ret)
		return ret;
#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK
	if (test_dropped_frame_acks)
		dev_info(a5->dev, "FAULT_TEST before DMA retirement reset_acks=%u,%u pending=%u request_mapped=%u input_ref=%u output_ref=%u\\n",
			 a5->resources.ipe_reset_acks[0], a5->resources.ipe_reset_acks[1],
			 a5->ipe_dma_pending, a5->request_fw_mapped,
			 !!a5->dma_input.buffer, !!a5->dma_output.buffer);
#endif
	/* Retire all firmware DMA aliases'''
assert after.count(a)==1;after=after.replace(a,b,1)
a='''done:
	if (result) {
		if (!ret)'''
b='''done:
#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK
	if (ret && a5->ipe_dma_pending && test_dropped_frame_acks)
		dev_info(a5->dev, "FAULT_TEST retained before reset pending=%u request_mapped=%u input_ref=%u output_ref=%u\\n",
			 a5->ipe_dma_pending, a5->request_fw_mapped,
			 !!a5->dma_input.buffer, !!a5->dma_output.buffer);
#endif
	if (result) {
		if (!ret)'''
assert after.count(a)==1;after=after.replace(a,b,1)
(P/'camss-icp-a5-boot.c.before').write_text(before);(P/'camss-icp-a5-boot.c.test').write_text(after)
(P/'test-declarations.c').write_text(declarations)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative));(HERE/'temporary-ack-loss.patch').write_text(patch)
r=dict(stage=394,base_commit=git('rev-parse','HEAD'),base_branch=git('branch','--show-current'),temporary_test_only=True,permanent_source_unchanged=True,production_macro_undefined=True,only_valid_successful_frame_ack_dropped_once=True,no_irq_mask_or_command_payload_change=True,unchanged_timeout_and_reset_paths=True,test_source_sha256=hashlib.sha256(after.encode()).hexdigest(),normal_source_sha256=hashlib.sha256(before.encode()).hexdigest(),passed=True)
(HERE/'proposal-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
