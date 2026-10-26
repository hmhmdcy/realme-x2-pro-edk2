"""Reuse the existing owner/PD/PHY fixture and add the actual route provider."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-final-transfer-candidate';ROUTE=HERE.parent/'eud-route-provider-candidate';HANDOFF=HERE.parent/'eud-route-handoff-candidate'
clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
# Build the old fixture string without compiling or replaying its tests.
outer=(OLD/'run-owner-tests.py').read_text();outer=outer[:outer.index('exec(compile(source,')]
scope={'__file__':str(OLD/'run-owner-tests.py'),'__name__':'fixture_only'};exec(compile(outer,'<existing-owner-fixture-generator>','exec'),scope)
builder=scope['source'];scope2={'__file__':str(OLD/'run-owner-tests.py'),'__name__':'fixture_only','PRIOR':scope['PRIOR']}
exec(compile(builder[:builder.index("flags=['-std=gnu11'")],'<existing-whole-owner-fixture>','exec'),scope2)
fixture=scope2['fixture'];fixture=fixture[:fixture.index('static void no_attempts(void)')]
def replace(before,after):
 global fixture
 assert fixture.count(before)==1,(before[:100],fixture.count(before));fixture=fixture.replace(before,after)
replace(clean((OLD/'samurai-apsd-owner.h').read_text()),clean((HERE/'samurai-apsd-owner.h').read_text()))
old_owner=clean((OLD/'samurai-apsd-owner.c').read_text())
replace('struct device_node { int id; };','struct device_node {int id;const char*compatible;bool available,stdout,linux_stdout;unsigned long long start,bytes;};\nstatic struct device_node route_node,hardware_node,chosen_node;')
for i,name in [(1,'supply_node'),(2,'other_node'),(3,'phy_node')]:fixture=fixture.replace(name+'={'+str(i)+'}',name+'={.id='+str(i)+'}')
replace('void*cleanup_data; };','void*cleanup_data;bool registered; };')
replace('struct platform_device {struct device dev;};','struct resource {unsigned long long start,end;unsigned long flags;};\nstruct platform_device {struct device dev;struct resource resource;bool has_resource;};')
replace('static struct platform_device tcpc;','static struct platform_device tcpc,route_platform;')
replace('static bool config_client=true,config_builtin=true;','static bool config_client=true,config_builtin=true,config_route_client=true;')
replace('#define CONFIG_USB_DWC3_SAMURAI_APSD_OWNER 3','#define CONFIG_USB_DWC3_SAMURAI_APSD_OWNER 3\n#define CONFIG_QCOM_SAMURAI_EUD_ROUTE 4\n#define CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT 5')
replace('#define IS_ENABLED(x) ((x)==CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT?config_client:true)',
 '#define IS_ENABLED(x) ((x)==CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT?config_client:((x)==CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT?config_route_client:true))')
replace(' if(!strcmp(s,"samurai,apsd-typec"))',
 ' if(!strcmp(s,"samurai,apsd-eud-route"))return &route_node;\n if(!strcmp(s,"realme,eud-hardware"))return &hardware_node;\n if(!strcmp(s,"realme,usb-controller"))return &phy_node;\n if(!strcmp(s,"samurai,apsd-typec"))')
replace('{assert(n==tcpc.dev.of_node);if(!platform_present)',
 '{if(n==&route_node){get_device(&route_platform.dev);return &route_platform;}assert(n==tcpc.dev.of_node);if(!platform_present)')
boundary=(HERE/'route-test-boundary.inc').read_text()
for marker,code in [('ACTUAL_WIRE_HEADER',clean((HANDOFF/'samurai-eud-handoff-wire.h').read_text())),('ACTUAL_NEXT_ARG',(ROUTE/'next-arg.actual.c.inc').read_text()),('ACTUAL_ROUTE_API',clean((ROUTE/'samurai-eud-route.h').read_text())),('ACTUAL_ROUTE_PROVIDER',clean((ROUTE/'samurai-eud-route.c').read_text()))]:boundary=boundary.replace('/* '+marker+' */',code)
replace(old_owner,boundary+'\n'+clean((HERE/'samurai-apsd-owner.c').read_text()))
replace('static void context_unlock_hook(struct mutex *m)\n{','''static void context_unlock_hook(struct mutex *m)
{
 if(unbind_on_route_unlock && route_provider && m==&route_provider->lock && route_provider->joining){
  unbind_on_route_unlock=false;dwc3_apsd_owner_unbind(&dwc);
 }
''')
replace(' publish_phy();dwc.usb2_generic_phy[0]=&phy_hw;',' publish_phy();dwc.usb2_generic_phy[0]=&phy_hw;host.registered=true;config_route_client=true;publish_route_test();')
replace(' release_phy();samurai_apsd_bus_unregister',' if(route_platform.dev.driverdata)route_remove(&route_platform);\n assert(!route_provider&&!producer&&!route_platform.dev.refs&&!host.refs);\n release_phy();samurai_apsd_bus_unregister')
start=fixture.index('static int no_rerun(');end=fixture.index('static const struct samurai_apsd_bus_ops bus=',start)
fixture=fixture[:start]+'''static int no_rerun(void*context,const struct samurai_apsd_attempt*attempt,struct samurai_apsd_transfer_result*result)
{
 struct samurai_apsd_bus_sample fresh;
 int ret=source_sample(context,&fresh);if(ret)return ret;
 if(boundary_mode==1)route_evidence_error=-EBADMSG;
 ret=attempt->validate(attempt,&fresh);if(ret)return ret;
 mock_apsd_writes++;result->transfer_attempted=true;result->before=fresh;result->after=fresh;result->after.serial=++serial;
 result->after.raw[0]=0;result->post_valid=true;return 0;
}
'''+fixture[end:]
# No debug FIFO or CSR access is allowed in this profile.
replace('analog_calls++;r->cookie=1;return 0;','assert(!"legacy EUD quiet begin called");(void)r;return -EIO;')
fixture+='\n'+(HERE/'test-client.c').read_text()
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/apsd-route-client-test-private-05');assert not private.exists();private.mkdir()
(private/'actual-combined.c').write_text(fixture)
build=subprocess.run(['gcc',*flags,str(private/'actual-combined.c'),'-o',str(private/'test')],capture_output=True,text=True)
(private/'compile.stdout').write_text(build.stdout);(private/'compile.stderr').write_text(build.stderr)
assert build.returncode==0,build.stderr
run=subprocess.run([str(private/'test')],capture_output=True,text=True,timeout=30)
(private/'run.stdout').write_text(run.stdout);(private/'run.stderr').write_text(run.stderr)
assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
groups=run.stdout.splitlines();assert len(groups)==9 and not run.stderr
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,actual_whole_owner_PD_PHY_and_route_provider=True,
    EFI_copy_and_kernel_work_DWC_MMIO_edges_modeled=True,real_concurrency_in_prior_provider_suite_only=True,
    simulated_bus_attempts_only=True,phone_accessed=False,installed=False,PM_route_retention_proved=False,
    fixture_sha256=hashlib.sha256(fixture.encode()).hexdigest(),files={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','route-client-functions.inc','route-test-boundary.inc','test-client.c','run-tests.py']})
with (HERE/'test-r2-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,groups=len(groups),phone_accessed=False)))
