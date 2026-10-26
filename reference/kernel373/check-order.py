from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'order-regression';work.mkdir(exist_ok=True)
s=(HERE.parent/'kernel370/start-regression.c').read_text();s=s.replace('#define dev_info(...) ((void)0)','#define dev_info(...) ((void)0)\n#define dev_err(...) ((void)0)\n#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))')
s=s.replace('struct camss_a5 {','struct camss_a5 {\n void (*failure_snapshot)(struct camss_a5 *a);',1)
s=s.replace('static bool backing;','static bool backing;\nstatic unsigned order,reset_at,wake_at,request_at,last_parameter_at;static bool corrupt_readback;')
s=s.replace('static u32 readl(void *p) {','static u32 readl(void *p) {\n if(corrupt_readback && p==registers+A5_SHARED_PTR/4)return 0;')
s=s.replace('static void writel(u32 value,void *p) {*(u32 *)p=value;}', '''static void writel(u32 value,void *p) {
 ++order;if(p==registers+A5_RESET/4 && value==0x10)reset_at=order;
 if(p==registers+A5_CONTROL/4 && value==(A5_ENABLE|A5_WAKE|A5_WFI_GATE))wake_at=order;
 if(p==registers+A5_SHARED_PTR/4)last_parameter_at=order;
 if(p==registers+A5_INIT_REQUEST/4 && value==1)request_at=order;
 *(u32 *)p=value;
}''')
a=s.index('int main(');s=s[:a]+'''int main(int argc,char **argv) {
 assert(argc==2);int which=atoi(argv[1]);struct camss_a5 a={0};struct firmware fw={0};active=&a;a.resources.sierra=registers;
 response_count=1;responses[0]=1;if(which)corrupt_readback=true;
 int ret=camss_a5_start(&a,&fw);assert(!a.lock && !a.boot_timer);
 assert(reset_at && wake_at>reset_at && last_parameter_at>wake_at);
 if(which){assert(ret==-EIO && !request_at && !sends && backing && a.power_held && !a.cpu_enabled);}
 else {assert(ret==0 && request_at>last_parameter_at && sends==1 && a.initialized);}
 return 0;
}
'''
rows=[]
for label,path,cases,expected in [('before',P/'boot-before.c',[0],False),('after',P/'boot-proposed.c',[0,1],True)]:
 text=path.read_text();a=text.index('static int program_hfi_parameters(') if label=='after' else text.index('int camss_a5_start(');b=text.index('EXPORT_SYMBOL_GPL(camss_a5_start)',a)
 (work/'body.inc').write_text(text[a:b]);(work/'probe.c').write_text(s)
 q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(label+'-'+str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==expected,(label,case,q.stderr.decode());rows.append(dict(source=label,case=case,expected_pass=expected,matched=True))
report=dict(stage=373,actual_programming_helper_and_start_bodies=True,tests=rows,asan_ubsan=True,mmio_pm_and_firmware_response_providers_mocked=True,
 parameters_programmed_after_cpu_reset_before_init_request=True,readback_mismatch_never_requests_initialization=True,
 no_claim_that_real_reset_clears_parameters=True,no_hardware_boot_claim=True,phone_operations=False,passed=True)
(HERE/'order-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
