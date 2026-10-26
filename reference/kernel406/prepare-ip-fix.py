"""Prepare the explicit full-pass IP enable correction; not yet submitted."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'current-state-validation-r1.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
base=source/'drivers/media/platform/qcom/camss';text=(base/'camss-icp-a5-ipe.c').read_text();(P/'camss-icp-a5-ipe.c.before').write_text(text)
old='''\t/* DC full-pass input inherits IP only with a valid quarter pass. */
	put_unaligned_le32(ltm->data_collection && ltm->image_processing &&
			   (((width + 7) / 4) & ~1U) >= 72 &&
			   (((height + 7) / 4) & ~1U) >= 54, output + 416);'''
new='''\t/* This full-pass field drives the physical IP_EN bit, not DC.
	 * Honour the explicit request; DC/coarse-pass policy belongs upstream.
	 */
	put_unaligned_le32(ltm->image_processing, output + 416);'''
assert text.count(old)==1;proposal=text.replace(old,new);(P/'camss-icp-a5-ipe.c.proposed').write_text(proposal)
(HERE/'ltm-ip-enable.patch').write_text(''.join(difflib.unified_diff(text.splitlines(True),proposal.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c',tofile='b/drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c')))
print('Prepared explicit full-pass IP enable; bypass, partitions and crops unchanged.')
