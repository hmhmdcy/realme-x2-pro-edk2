"""Reuse the validated one-shot ACK filter on the actual current kernel."""
from pathlib import Path
import ast,importlib.util,json
import host
HERE=Path(__file__).resolve().parent
state=json.loads((HERE.parent/'kernel417/source-state.json').read_text())
state.update(stage=419,phone_accessed=False,installed=False,kernel_unchanged_from417=True,
    actual_libcamera_stage=418,source_preparation_only=True,last_device_evidence_stage=418)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
code=(HERE.parent/'kernel395/prepare-test-core.py').read_text().replace('stage=395','stage=419')
old='a5->ipe_dma_pending, a5->request_fw_mapped,\n\t\t\t !!a5->dma_input.buffer, !!a5->dma_output.buffer);'
new='a5->ipe_dma_pending, a5->request_fw_mapped,\n\t\t\t !!a5->dma_input.buffer, !!a5->dma_output.buffer);'
assert old in code # Preserve the ACK parser hook and original two lifetime probes.
(HERE/'prepare-test-core.py').write_text(code)
spec=importlib.util.spec_from_file_location('prepare419',HERE/'prepare-test-core.py');prepared=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepared)
# Supplement only test logs: prove the whole typed IQ parcel is still backed.
path=host.PRIVATE/'camss-icp-a5-boot.c.test';text=path.read_text()
needle='''	if (ret && a5->ipe_dma_pending && test_dropped_frame_acks)
		dev_info(a5->dev, "FAULT_TEST retained before reset pending=%u request_mapped=%u input_ref=%u output_ref=%u\\n",
			 a5->ipe_dma_pending, a5->request_fw_mapped,
			 !!a5->dma_input.buffer, !!a5->dma_output.buffer);'''
replacement=needle+'''
	if (ret && a5->ipe_dma_pending && test_dropped_frame_acks)
		dev_info(a5->dev, "FAULT_TEST typed IQ retained iq_bytes=%u parcel_bytes=%u parcel_present=%u gamma=%u ltm=%u\\n",
			 iq_bytes, a5->request.bytes, !!a5->request.cpu,
			 !!gamma_copy, !!ltm_copy);'''
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle='''	/* Retire all firmware DMA aliases'''
replacement='''#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK
	if (test_dropped_frame_acks)
		dev_info(a5->dev, "FAULT_TEST parcel before retirement bytes=%u present=%u\\n",
			 a5->request.bytes, !!a5->request.cpu);
#endif
'''+needle
assert text.count(needle)==1;text=text.replace(needle,replacement)
path.write_text(text)
import difflib,hashlib
before=(host.PRIVATE/'camss-icp-a5-boot.c.normal').read_text();relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'
(HERE/'temporary-ack-loss.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
proposal=json.loads((HERE/'test-proposal-validation.json').read_text());proposal.update(test_source_sha256=hashlib.sha256(text.encode()).hexdigest(),typed_parcel_retention_logs_added=True)
(HERE/'test-proposal-validation.json').write_text(json.dumps(proposal,indent=2)+'\n')
for src,dest in [('check-hook.py','check-hook.py'),('build-test-core.py','build-test-core.py')]:
    script=(HERE.parent/'kernel395'/src).read_text().replace('stage=395','stage=419').replace('source_restored_to_normal395=True','source_restored_to_normal417=True')
    ast.parse(script);(HERE/dest).write_text(script)
print('Prepared one-shot validated ACK filter plus IQ backing lifetime logs; maintained source unchanged.')
