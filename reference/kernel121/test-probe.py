from pathlib import Path
import runpy,re,subprocess,json,hashlib,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121');out=Path('/mnt/e/edk2-samurai-out/kernel121/probe-test');out.mkdir(exist_ok=True)
root=Path('/home/cy122/pmos-samurai-kernel118')
def extract(path):
    text=path.read_text();return text[text.index('static const struct mfd_cell pm8008_cells[]'):text.index('static const struct of_device_id pm8008_match[]')]
stubs=(ref/'probe-stubs.c').read_text()
main=r'''
int main(void) {
 int cases=0;
 for(int irq=0;irq<=1;irq++) {
  int last=irq?10:6;
  for(int failure=0;failure<=last;failure++) {
   fail_at=failure;stage=allocations=irq_calls=cells_count=release_calls=0;published=NULL;published_domain=NULL;
   struct i2c_client c={.irq=irq?460:0,.addr=8};
   int result=pm8008_probe(&c);
#ifdef BASELINE
   if(!irq && !failure){assert(result==-EIO);assert(cells_count==0);puts("BASELINE_NO_IRQ_FAILURE_REPRODUCED");return 0;}
#endif
   if(failure) { assert(result<0);assert(cells_count==0); }
   else {
    assert(result==0);
    assert(!strcmp(published[0].name,"pm8008-regulator"));
    assert(cells_count==(irq?3:1));assert(published_domain==(irq?&irqdomain:NULL));
    assert(c.dev.data==published_domain);
    if(irq)assert(!strcmp(published[1].name,"qpnp-temp-alarm")&&!strcmp(published[2].name,"pm8008-gpio"));
   }
   if(!irq){assert(allocations==0&&irq_calls==0);}
   if(irq&&failure==8)assert(release_calls==1);
   cases++;
  }
 }
 printf("ACTUAL_PROBE_%d_FAILURE_AND_SUCCESS_CASES_PASS\n",cases);return 0;
}
'''
reports=[]
for label,tree in [('baseline',root/'camera120/kernel'),('candidate',root/'camera121/kernel')]:
    path=tree/'drivers/mfd/qcom-pm8008.c';code=extract(path)
    source=out/(label+'.c');source.write_text(stubs+code+main)
    binary=out/label
    args=['gcc','-std=c17','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-g',str(source),'-o',str(binary)]
    if label=='baseline':args.insert(1,'-DBASELINE')
    subprocess.run(args,check=True,timeout=30)
    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
    assert result.returncode==0 and result.stderr=='';(out/(label+'-result.txt')).write_text(result.stdout)
    reports.append(dict(label=label,actual_probe_sha256=hashlib.sha256(code.encode()).hexdigest(),exit=result.returncode,result=result.stdout.strip(),hardware_calls_stubbed=True))
(ref/'probe-test-validation.json').write_text(json.dumps(dict(actual_c_probe_extracted_without_rewriting=True,sanitizers=['address','undefined'],tests=reports,physical_pmic_not_probed=True),indent=2)+'\n');print(json.dumps(reports))
