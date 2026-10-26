"""Record primary register facts, silicon comparisons and the prefill false-positive correction."""
from pathlib import Path
import hashlib,json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
path='drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe175.h'
source=subprocess.check_output(['git','--git-dir=/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git','show',commit+':'+path])
text=source.decode();color=text.split('color_175_reg = {',1)[1].split('};',1)[0]
assert re.search(r'\.cgc_ovd\s*=\s*0x00000034',color) and re.search(r'\.enable\s*=\s*0x00000048',color)
before=json.loads((ROOT/'gamma-lut-dphy-validation.json').read_text())
after=json.loads((ROOT/'gamma-lut-pattern-validation.json').read_text())
assert before['frames']==3 and all(t['unique_words']==1 for t in before['tables'])
assert after['frames']==3 and all(t['unique_words']==64 for t in after['tables'])
assert all(t['matching_words']==0 for t in after['tables'])
actual=json.loads((ROOT/'gamma-upload-capture-validation.json').read_text())
assert actual['tool_exit']==0 and actual['actual_frames']==9
assert actual['tool_output'].count('matching_words=64 expected=64')==3
assert 'GAMMA_RESTORE registers=1' in actual['tool_output']
report=dict(stage=289,official_kernel_commit=commit,official_path=path,official_file_sha256=hashlib.sha256(source).hexdigest(),
 color_clock_override='0x34',gamma_enable='0x48 bit3',
 cgc_off_indexed_and_sequential_reads_each_return_one_repeated_word=True,
 cgc_on_reads_each_return_64_distinct_words=True,deployed_gamma_tables_do_not_match_requested_curve=True,
 cgc_on_upload_exact_readback_words=192,same_stream_response_changed=True,
 black_white_luma_after=[0,254],black_white_chroma_after=[0,0],color_correctness_still_failed=True,
 internal_tpg_phy_history_failure_reproduced=True,dphy_link_history_control_restored_frames=True,
 no_oem_code_execution=True,no_calibration_writes=True,upstream_acceptance_not_claimed=True)
(ROOT/'clock-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
s=(ROOT/'samurai-dmi-pattern.c').read_text();prefill=re.search(r'static unsigned char prefill\(.*?\n\}',s,re.S)[0]
test='#include <assert.h>\n#include <stddef.h>\n'+prefill+r'''
int main(void){for(unsigned seed=0;seed<3;seed++){
 unsigned hist[256]={0};for(size_t i=0;i<115200;i++)hist[prefill((unsigned char)(0xa5^(seed*0x31)),i)]++;
 for(unsigned value=0;value<256;value++)assert(hist[value]<115200/100);
}return 0;}
'''
p=host.PRIVATE/'prefill-test-private.c';p.write_text(test);binary=host.PRIVATE/'prefill-test-private'
subprocess.run(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p),'-o',str(binary)],check=True,capture_output=True)
subprocess.run([str(binary)],check=True,capture_output=True)
(ROOT/'prefill-validation.json').write_text(json.dumps(dict(stage=289,actual_prefill_function_tested=True,all_256_constant_values_and_three_seeds=True,
 maximum_constant_coincidence_below_one_percent=True,dma_change_threshold_90_percent_retained=True,
 observed_old_false_positive_same_hash_different_constant_prefill=True),indent=2)+'\n')
# Separate restoration writes from readback proof instead of claiming RAM was re-read.
p=ROOT/'gamma-upload-tool-validation.json';r=json.loads(p.read_text());r.pop('register_and_previous_inactive_bank_state_restored',None)
r.update(register_restoration_hardware_verified=True,previous_inactive_bank_restore_writes_issued=True,previous_inactive_bank_restore_readback_verified=False)
p.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(report,indent=2))
