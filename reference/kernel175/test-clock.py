from pathlib import Path
import hashlib, json, re, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
source=(k/'sound/soc/codecs/wcd934x.c').read_text()
manifest=json.loads((ref/'source-validation.json').read_text())
assert hashlib.sha256(source.encode()).hexdigest()==manifest['source_sha256']['sound/soc/codecs/wcd934x.c']
a=source.index('static int wcd934x_register_mclk_output(');b=source.index('static int wcd934x_init_dmic(',a);actual=source[a:b]
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
struct device_node{int x;};struct clk{int x;};
struct device{struct device *parent;struct device_node *of_node;int hw,provider;};
struct clk_init_data{const char *name;void *ops;int flags;const char **parent_names;int num_parents;};
struct clk_hw{struct clk_init_data *init;};
struct wcd934x_codec{struct device *dev;struct clk *extclk;unsigned int rate;struct clk_hw hw;};
static int swclk_gate_ops,mode;static struct device owner,parent;static char trace[8];static int pos;
static int of_property_read_u32(struct device_node *n,const char *s,unsigned int *v){if(mode==1)return -ENOENT;*v=9600000;return 0;}
static const char *__clk_get_name(struct clk *p){return "xo";}
static int of_property_read_string(struct device_node *n,const char *s,const char **v){*v="mclk";return 0;}
static int devm_clk_hw_register(struct device *d,struct clk_hw *hw){assert(d==&owner&&hw->init->num_parents==1&&strcmp(hw->init->name,"mclk")==0);if(mode==2)return -EIO;assert(!d->hw);d->hw=1;return 0;}
static void *of_clk_hw_simple_get;
static int devm_of_clk_add_hw_provider(struct device *d,void *get,struct clk_hw *hw){assert(d==&owner&&d->hw);if(mode==3)return -ENOMEM;d->provider=1;return 0;}
static void release(struct device *d){if(d->provider){d->provider=0;trace[pos++]='p';}if(d->hw){d->hw=0;trace[pos++]='h';}}
'''
tests=r'''
int main(void){struct device_node node={0};parent.of_node=&node;owner.parent=&parent;struct clk clk={0};int cases=0;
 for(mode=0;mode<=3;mode++){owner.hw=owner.provider=0;pos=0;memset(trace,0,sizeof(trace));struct wcd934x_codec w={.dev=&owner,.extclk=&clk};int ret=wcd934x_register_mclk_output(&w);
  assert(ret==(mode==2?-EIO:mode==3?-ENOMEM:0));if(!mode)assert(owner.hw&&owner.provider&&w.rate==9600000);
  assert(!parent.hw&&!parent.provider);release(&owner);assert(!owner.hw&&!owner.provider);if(!mode)assert(strcmp(trace,"ph")==0);cases++;}
 printf("clock_cases=%d\n",cases);return 0;}
'''
def run(label,code,passed):
    p=out/(label+'-private.c');p.write_text(code);exe=out/(label+'-private')
    r=subprocess.run(['gcc','-std=gnu11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined',str(p),'-o',str(exe)],capture_output=True)
    (out/(label+'-compile-private.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
    r=subprocess.run([str(exe)],capture_output=True);(out/(label+'-run-private.log')).write_bytes(r.stdout+r.stderr)
    assert (r.returncode==0)==passed,r.stderr.decode()
    return r.stdout.decode().strip()
result=run('clock-lifetime',prefix+actual+tests,True)
run('negative-clock-parent-owner',prefix+actual.replace('devm_clk_hw_register(dev, hw)','devm_clk_hw_register(dev->parent, hw)')+tests,False)
probe=source[source.index('static int wcd934x_codec_probe('):]
assert 'ret = wcd934x_register_mclk_output(wcd);\n\tif (ret)' in probe
report=json.loads((ref/'host-tests-validation.json').read_text())
report['clock_result']=result;report['clock_probe_errors_propagated_source_check']=True
report['negative_controls_rejected'].append('clock-parent-owner')
for folder in [ref,out]:(folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
