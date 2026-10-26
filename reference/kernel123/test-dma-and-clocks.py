from pathlib import Path
import runpy,re,subprocess,json,os
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel123';out=Path('/mnt/e/edk2-samurai-out/kernel123')
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel')
text=(k/'drivers/media/platform/qcom/camss/camss.c').read_text()
clause=re.search(r'\tif \(camss->res->version == CAMSS_8150\)\n\t\tret = dma_set_mask_and_coherent\(dev, DMA_BIT_MASK\(31\)\);\n\telse\n\t\tret = dma_set_mask_and_coherent\(dev, 0xffffffff\);',text)
assert clause
source='''#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#define CAMSS_8150 8150
#define DMA_BIT_MASK(n) ((UINT64_C(1) << (n))-1)
struct resource { int version; };
struct camss_device { struct resource *res; };
static uint64_t mask_seen;
static int return_code;
static int dma_set_mask_and_coherent(void *dev, uint64_t mask) { assert(dev); mask_seen=mask; return return_code; }
static int actual_clause(int version) {
    struct resource r={version}; struct camss_device c={&r};
    struct camss_device *camss=&c; void *dev=&c; int ret;
'''+clause.group(0)+'''
    return ret;
}
int main(void) {
    int versions[]={8150,845,8250,0}; int errors[]={0,-5,-12};
    for (unsigned i=0;i<4;i++) for (unsigned j=0;j<3;j++) {
        return_code=errors[j]; mask_seen=0;
        assert(actual_clause(versions[i])==return_code);
        assert(mask_seen==(versions[i]==8150?UINT64_C(0x7fffffff):UINT64_C(0xffffffff)));
        if(versions[i]==8150) assert(mask_seen < UINT64_C(0xe0000000));
    }
    puts("ACTUAL_DMA_C_CLAUSE_12_CASES_PASS");
}
'''
testdir=k.parent/'dma-test';testdir.mkdir(exist_ok=True);p=testdir/'dma.c';p.write_text(source)
subprocess.run(['gcc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g',str(p),'-o',str(testdir/'dma-test')],check=True,timeout=30)
proc=subprocess.run([str(testdir/'dma-test')],capture_output=True,text=True,check=True,timeout=10,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'));(out/'dma-test-private.txt').write_text(proc.stdout+proc.stderr)
port=json.loads((ref/'camss-path-port-validation.json').read_text());dt_names=set(port['clock_names']);tables=[]
for label,next_label in [('csiphy_res_8150','csid_res_8150'),('csid_res_8150','vfe_res_8150'),('vfe_res_8150','csiphy_res_8250')]:
    block=text[text.index('static const struct camss_subdev_resources '+label):text.index('static const struct camss_subdev_resources '+next_label)]
    clocks=re.findall(r'\.clock = \{([^}]+)\}',block);rates=re.findall(r'\.clock_rate = \{(.*?)\},\n\t\t\.reg',block,re.S)
    assert len(clocks)==len(rates)
    for clk,rate in zip(clocks,rates):
        names=re.findall('"([^\"]+)"',clk);entries=re.findall(r'\{[^{}]*\}',rate)
        assert len(names)==len(entries) and all(n in dt_names for n in names)
        tables.append(dict(table=label,clocks=len(names),rates_aligned=True))
a=text.index('static const struct resources_icc icc_res_8150[]');b=text.index('static const struct camss_resources sm8150_resources',a)
icc_names=re.findall(r'\.name = "([^\"]+)"',text[a:b]);assert icc_names==['cam_ahb','cam_hf_0_mnoc','cam_sf_0_mnoc','cam_hf_0_camnoc']
report=dict(actual_driver_c_clause_extracted_without_rewrite=True,dma_success_and_error_cases=12,asan_ubsan_pass=True,other_soc_dma_mask_unchanged=True,clock_rate_arrays_aligned=tables,clock_names_all_in_dtb=True,icc_table_four_paths_match=True,lower_iova_reserved_boundary_not_encoded=True,hardware_dma_capture_not_tested=True,phone_unchanged=True)
(ref/'dma-clock-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(proc.stdout.strip());print(json.dumps(report))
