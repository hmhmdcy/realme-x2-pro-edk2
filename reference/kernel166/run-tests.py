from pathlib import Path
import hashlib, json, re, subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel166')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
def function(s,name):
    hit=re.search(r'^(?:static (?:inline )?)?(?:int |void |bool |u32 \*)(?:__maybe_unused )?'+name+r'\([^;{]*\)\n\{',s,re.M)
    assert hit,name
    start=hit.start();a=s.index('{',start);depth=1;b=a+1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[start:b]+'\n'
def run(label,source,expected=0):
    path=out/(label+'-private.c');path.write_text(source)
    binary=out/(label+'-private')
    build=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Wno-unused-variable','-Wno-unused-function','-Wno-unused-parameter','-Werror','-g','-fsanitize=address,undefined',str(path),'-o',str(binary)],capture_output=True)
    (out/(label+'-build-private.log')).write_bytes(build.stdout+build.stderr)
    assert build.returncode==0,(label,build.stderr.decode())
    result=subprocess.run([str(binary)],capture_output=True)
    (out/(label+'-run-private.log')).write_bytes(result.stdout+result.stderr)
    assert result.returncode==expected,(label,result.stdout.decode(),result.stderr.decode())
    assert not result.stderr,label
    return result.stdout.decode().strip()
ngd=(k/'drivers/slimbus/qcom-ngd-ctrl.c').read_text()
before=(out/'qcom-ngd-ctrl.c.163-before-private').read_text()
names=['qcom_slim_ngd_exit_dma','qcom_slim_ngd_init_dma','qcom_slim_ngd_runtime_resume','qcom_slim_ngd_runtime_suspend','qcom_slim_ngd_setup']
common=(ref/'test-pm-stubs.h').read_text()
negative=run('pm-baseline',common+''.join(function(before,n) for n in names if n!='qcom_slim_ngd_setup')+(ref/'test-pm-main.c').read_text().split('int main(void)')[0]+'''
int main(void) {
 struct qcom_slim_ngd_ctrl c; struct device d; reset(&c,&d);
 assert(qcom_slim_ngd_init_dma(&c)==0); power_ret=-EBUSY;
 assert(qcom_slim_ngd_runtime_suspend(&d)==-EBUSY);
 if (!c.dma_rx_channel || !c.dma_tx_channel) {
   free(c.rx_base); free(c.tx_base);
   puts("BASELINE_REJECTED_SUSPEND_INVALIDATES_DMA"); return 2;
 } return 0;
}
''',2)
pm=run('pm-candidate',common+''.join(function(ngd,n) for n in names)+(ref/'test-pm-main.c').read_text())
codec=(k/'sound/soc/codecs/wcd934x.c').read_text()
headers=(k/'include/linux/mfd/wcd934x/registers.h').read_text()+(k/'sound/soc/codecs/wcd-common.h').read_text()+codec
macros=[]
for line in headers.splitlines(True):
    if re.match(r'#define\s+(?:WCD934X_\w+|WCD_VERSION_\w+|DSD_DISABLED\w*|SLNQ_DISABLED\w*)\s+[^\\\n]+$',line):
        macros.append(line)
src=(ref/'test-codec-stubs.h').read_text()+''.join(macros)+'\n#define SIDO_SOURCE_RCO_BG 0\n'
src+=''.join(function(codec,n) for n in ['wcd934x_hw_init','wcd934x_enable_efuse_sensing','wcd934x_get_version','wcd934x_comp_init'])
src+='''
int main(void) {
 struct snd_soc_component comp={0};
 for(int i=1;i<=10;i++) {
  io_call=0;fail_at=i;clk_users=0;fail_clock=0;
  assert(wcd934x_comp_init(&comp)==-EREMOTEIO);
  assert(io_call==i && clk_users==0);
 }
 io_call=0;fail_at=0;clk_users=0;fail_clock=1;
 assert(wcd934x_comp_init(&comp)==-EIO && clk_users==0);
 io_call=0;fail_at=0;clk_users=0;fail_clock=0;
 assert(wcd934x_comp_init(&comp)==0 && clk_users==0);
 puts("{\\"cases\\":12}"); return 0;
}
'''
codec_result=run('codec-candidate',src)
report=dict(stage=166, driver_functions_extracted_verbatim=True, hardware_primitives_stubbed=True,
            baseline_suspend_failure_negative_control=negative, pm=json.loads(pm), codec=json.loads(codec_result),
            address_undefined_sanitizers_clean=True, physical_dma_and_pm_not_proven_by_host_tests=True,
            extracted_functions_sha256=hashlib.sha256(''.join(function(ngd,n) for n in names).encode()).hexdigest())
for folder in [ref,out]:
    (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
