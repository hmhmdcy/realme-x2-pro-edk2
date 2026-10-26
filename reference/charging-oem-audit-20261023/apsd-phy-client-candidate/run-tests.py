"""Whole actual DWC owner, PD5V and PHY provider/window bodies together."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-pd5v-client-bridge-candidate';PHY=HERE.parent/'apsd-phy-withdrawal-candidate';PD=HERE.parent/'pd5v-owner-context-r2'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
clean=lambda s:'\n'.join(line for line in s.splitlines() if not line.startswith('#include'))+'\n'
boundary=(PD/'kernel-boundary-fixture.inc').read_text().split('#include "qcom_pmic_typec_5v.h"')[0]
boundary=boundary.replace('struct device { struct device_node *of_node; int refs;struct device *parent;void *driverdata; };',
 'struct regmap;\nstruct device { struct device_node *of_node; int refs;struct device *parent;void *driverdata;bool optin,bridge,suspended;int pm_refs;struct regmap *map;void(*cleanup)(void*);void*cleanup_data; };')
boundary=boundary.replace(' if(!strcmp(s,"vdd-pdphy-supply"))',' if(!strcmp(s,"samurai,apsd-typec"))return phandle_present?&other_node:NULL;\n if(!strcmp(s,"vdd-pdphy-supply"))')
boundary=boundary.replace('static bool wrong_supply;','static bool wrong_supply;\nstatic bool phandle_present,platform_present;')
headers='\n'.join(clean(p.read_text()) for p in [OLD/'samurai-apsd-backend.h',HERE/'samurai-apsd-owner.h',OLD/'samurai-apsd-once.h',OLD/'samurai-usb-input-decode.h',OLD/'qcom_pmic_typec_5v.h',
 HERE.parents[1]/'charging-session-20261023/eud-runtime-window-candidate/eud-com-window.h',HERE/'phy-qcom-snps-femto-v2-window.h'])
ch=(OLD/'core.h').read_text();windows=ch[ch.index('enum dwc3_gadget_window_state {'):ch.index('/**\n * struct dwc3 -')]
phy_source=(PHY/'phy-qcom-snps-femto-v2.c').read_text()
def function(name):
    match=re.search(r'^(?:static\s+)?(?:int|bool|void)\s+'+name+r'\([^;]*?\)\s*\{',phy_source,re.M);assert match,name
    i=phy_source.index('{',match.start())+1;depth=1
    while depth:depth+=(phy_source[i]=='{')-(phy_source[i]=='}');i+=1
    return phy_source[match.start():i]
macros='\n'.join(line for line in phy_source.splitlines() if line.startswith('#define ') and not line.startswith('#define SNPS_HS_NUM_VREGS'))
structure=re.search(r'^struct qcom_snps_hsphy \{.*?^\};',phy_source,re.M|re.S).group()
arrays='\n'.join(re.search(r'static const u32 '+name+r'\[\] = \{.*?\};',phy_source,re.S).group() for name in ['qcom_snps_hsphy_window_offsets','qcom_snps_hsphy_window_masks','qcom_snps_hsphy_window_values'])
names=['qcom_snps_hsphy_window_busy','qcom_snps_hsphy_window_write','qcom_snps_hsphy_window_bound_begin','qcom_snps_hsphy_window_bound_end']
phy_functions='static const struct phy_ops qcom_snps_hsphy_gen_ops;\n'+arrays+'\n'+'\n\n'.join(function(n) for n in names)+'\n'+(PHY/'provider-lifetime.inc').read_text()
pb=(HERE/'phy-test-boundary.inc').read_text().replace('/* ACTUAL_PHY_TYPES */','struct qcom_hsphy_window_provider;\n'+macros+'\n#define SNPS_HS_NUM_VREGS 3\n'+structure)
pb=pb.replace('/* ACTUAL_PHY_FUNCTIONS */',phy_functions)
fixture=(OLD/'test-bridge.c').read_text().split('int main(void)')[0].replace('static bool phandle_present=true,platform_present=true;','')
fixture=fixture.replace('/* PD_BOUNDARY */',boundary).replace('/* ACTUAL_HEADERS */',headers).replace('/* WINDOW_TYPES */',windows)
fixture=fixture.replace('struct phy {int unused;};','/* REAL_PHY_STRUCT_WILL_FOLLOW */')
start=fixture.index('int qcom_snps_hsphy_window_begin(struct phy *p,');end=fixture.index('/* ACTUAL_PD */',start)
fixture=fixture[:start]+pb+'\n'+fixture[end:]
fixture=fixture.replace('/* ACTUAL_PD */',clean((OLD/'qcom_pmic_typec_5v.c').read_text())).replace('/* ACTUAL_OWNER */',clean((HERE/'samurai-apsd-owner.c').read_text()))
# Declarations needed by DWC/EUD edge functions before the PHY fixture.
fixture=fixture.replace('static int analog_calls,APSD_writes,restore_error;','static int analog_calls,APSD_writes,restore_error;\nstatic int dwc_ends,dwc_cancels,eud_ends;')
fixture=fixture.replace('static int phy_reads,phy_writes,drop_phy_write,dwc_ends,dwc_cancels,eud_ends;','static int phy_reads,phy_writes,drop_phy_write;')
fixture=fixture.replace('(void)c;r->restored=true;return 0;','(void)c;eud_ends++;r->restored=true;return 0;')
fixture=fixture.replace('(void)d;(void)c;(void)r;return 0;}','(void)d;(void)c;(void)r;dwc_cancels++;return 0;}',1)
mark='int dwc3_gadget_window_end(';pos=fixture.index(mark);tail=fixture[pos:];tail=tail.replace('(void)d;(void)c;(void)r;return 0;}','(void)d;(void)c;(void)r;dwc_ends++;return 0;}',1);fixture=fixture[:pos]+tail
fixture=fixture.replace('static void context_unlock_hook(struct mutex *m)\n{','''static void context_unlock_hook(struct mutex *m)
{
 if(unbind_on_phy_unlock && phy_shadow.window_provider && m==&phy_shadow.window_provider->lock && phy_shadow.window_provider->withdrawing){
  unbind_on_phy_unlock=false;dwc3_apsd_owner_unbind(&dwc);
 }
''')
fixture=fixture.replace(' dwc3_apsd_owner_bind(&dwc);assert(bound_owner);',' publish_phy();dwc.usb2_generic_phy[0]=&phy_hw;\n dwc3_apsd_owner_bind(&dwc);assert(bound_owner);')
fixture=fixture.replace(' serial=0;clock_ms=1000;',' phy_reads=phy_writes=drop_phy_write=dwc_ends=dwc_cancels=eud_ends=0;unbind_on_phy_unlock=false;\n serial=0;clock_ms=1000;')
fixture=fixture.replace(' samurai_apsd_bus_unregister(&source,&source);samurai_pd5v_destroy(pd);pd=NULL;',' release_phy();samurai_apsd_bus_unregister(&source,&source);samurai_pd5v_destroy(pd);pd=NULL;')
fixture=fixture.replace(' assert(!APSD_writes&&!analog_calls);',' assert(!APSD_writes&&!phy_platform.dev.pm_refs);')
fixture=fixture.replace('bound_owner->ref.refs==2);assert(writes==4);','bound_owner->ref.refs==3);assert(writes==4);')
fixture+='\n'+(HERE/'test-client.c').read_text()
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-phy-client-') as name:
    root=Path(name);code=root/'actual-client.c';code.write_text(fixture);binary=root/'test'
    build=subprocess.run(['gcc',*flags,str(code),'-o',str(binary)],capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    groups=run.stdout.splitlines();assert len(groups)==12 and not run.stderr
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,fixture_sha256=sha(fixture.encode()),
    actual_whole_owner_PD5V_and_PHY_provider=True,actual_four_bound_PHY_functions=names,prior_PHY_pthread_suite_reused=True,
    fake_kernel_work_PM_MMIO_edges=True,revocation_metadata_scheduling_cut_modeled=True,faulted_orphan_fixture_disposal_not_implementation=True,
    files={n:sha((HERE/n).read_bytes()) for n in ['samurai-apsd-owner.c','samurai-apsd-owner.h','phy-qcom-snps-femto-v2-window.h','phy-client-functions.inc','phy-test-boundary.inc','test-client.c','run-tests.py','Kconfig.fragment']},
    prior_full_bridge_14_groups_rerun=False,phone_accessed=False,attempt_gate_enabled=False)
with (HERE/'test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,groups=len(groups),phone_accessed=False)))
