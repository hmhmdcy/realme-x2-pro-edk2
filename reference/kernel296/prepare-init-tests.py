"""Extend the actual-function harness with an independent BHIST SRAM/DMI model."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel295/test-stats.py').read_text().replace('stage=295','stage=296')
s=s.replace("stats=(D/'camss-vfe-175-stats.c').read_text();", "stats=subprocess.check_output(['git','-C',str(D.parents[5]),'show','d249946aefa1a01d99fd5484825a4458423b7348:drivers/media/platform/qcom/camss/camss-vfe-175-stats.c'],text=True) if '--parent' in sys.argv else (D/'camss-vfe-175-stats.c').read_text();")
# D is tree/drivers/media/platform/qcom/camss, so parents[4] is the kernel tree.
s=s.replace('str(D.parents[5])','str(D.parents[4])')
needle='static u32 readl_relaxed(void*p){return *(u32*)p;}'
model=r'''
static u32 bhist_sram[1024];static unsigned sram_writes;
static __attribute__((unused)) void writel(u32 value,void*p){
 size_t offset=(unsigned char*)p-(unsigned char*)memory;
 if(offset==0xc30){
  assert((memory[0xc24/4]&0x7f)==0x3a);
  assert(!(memory[0xc24/4]&0x1100));
  assert(memory[0x30/4]&0x10);
  unsigned address=memory[0xc28/4];assert(address<1024&&address==sram_writes%1024);
  assert(value==0);bhist_sram[address]=value;sram_writes++;
 }
 writel_relaxed(value,p);
}
'''
assert needle in s;s=s.replace(needle,model+'\n'+needle,1)
needle='int main(void){';assert needle in s
s=s.replace(needle,needle+'\n for(unsigned i=0;i<1024;i++)bhist_sram[i]=0x6bad0000U+i;',1)
needle=' assert((memory[0x44/4]&BIT(5))=='
assert needle in s
checks=''' assert(sram_writes==1024);
 for(unsigned i=0;i<1024;i++)assert(!bhist_sram[i]);
 assert(memory[0xc24/4]==0xa5a5a5a5U&&memory[0xc28/4]==0xa5a5a5a5U&&memory[0x30/4]==0xa5a5a5a5U);
'''
s=s.replace(needle,checks+needle,1)
s=s.replace("source=prefix+'\\n'+'\\n'.join(parts)+main;p=host.PRIVATE/'stats-tests-private.c';", "source=prefix+'\\n'+'\\n'.join(parts)+main;p=host.PRIVATE/('parent-init-stats-tests-private.c' if '--parent' in sys.argv else 'stats-tests-private.c');")
s=s.replace("'parent-enable-validation.json'","'parent-init-validation.json'").replace('independent_port_bit_contract=True','independent_sram_initialization_contract=True').replace('Pinned bit4 contract rejects the actual k294 implementation.','Pinned SRAM initialization contract rejects the actual k295 implementation.')
s=s.replace('report=dict(stage=296,asan_ubsan=True','report=dict(stage=296,bhist_all_1024_sram_words_cleared=True,dmi_cgc_config_address_restored=True,explicit_indices_and_mode_checked=True,asan_ubsan=True')
p=ROOT/'test-stats.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared SRAM-clock/selector/mode/index/reset checks, including actual parent negative control.')
