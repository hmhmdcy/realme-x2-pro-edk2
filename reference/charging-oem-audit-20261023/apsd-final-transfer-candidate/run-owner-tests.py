"""Reuse whole real owner/PD/PHY fixture; replace only changed API/owner."""
from pathlib import Path
import ast,hashlib
HERE=Path(__file__).resolve().parent;PRIOR=HERE.parent/'apsd-phy-client-candidate'
source=(PRIOR/'run-tests.py').read_text()
def replace(a,b):
    global source
    assert source.count(a)==1,a;source=source.replace(a,b)
replace("OLD/'samurai-apsd-backend.h'","HERE/'samurai-apsd-backend.h'")
replace("HERE/'phy-qcom-snps-femto-v2-window.h'","PRIOR/'phy-qcom-snps-femto-v2-window.h'")
replace("HERE/'phy-test-boundary.inc'","PRIOR/'phy-test-boundary.inc'")
replace("fixture+='\\n'+(HERE/'test-client.c').read_text()", "fixture+='\\n'+(PRIOR/'test-client.c').read_text().replace(' no_attempts();return 0;', (HERE/'test-owner.inc').read_text()+'\\n no_attempts();return 0;')")
replace("assert len(groups)==12", "assert len(groups)==18")
replace("['samurai-apsd-owner.c','samurai-apsd-owner.h','phy-qcom-snps-femto-v2-window.h','phy-client-functions.inc','phy-test-boundary.inc','test-client.c','run-tests.py','Kconfig.fragment']", "['samurai-apsd-owner.c','samurai-apsd-owner.h','samurai-apsd-backend.h','owner-attempt-functions.inc','test-owner.inc','run-owner-tests.py']")
replace("HERE/'test-result.json'", "HERE/'owner-test-result.json'")
marker="flags=['-std=gnu11'"
position=source.index(marker)
adapt=r"""
fixture=fixture.replace('static int source_error;','static int source_error,boundary_mode;')
fixture=fixture.replace('serial=0;clock_ms=1000;','serial=0;boundary_mode=0;clock_ms=1000;')
old='static int no_rerun(void *ctx,u64 epoch){(void)ctx;(void)epoch;APSD_writes++;assert(!"1341 is prohibited");return -EOPNOTSUPP;}'
new='''static int no_rerun(void *ctx,const struct samurai_apsd_attempt *attempt,struct samurai_apsd_transfer_result *result)
{
 (void)ctx;
 struct samurai_apsd_bus_sample fresh=attempt->expected;fresh.serial++;
 if(boundary_mode==1)return attempt->validate(attempt,&fresh);
 if(boundary_mode==2||boundary_mode==3){
  result->before=fresh;result->after=fresh;result->after.serial++;
  result->after.raw[0]=boundary_mode==2?0:1;result->transfer_attempted=result->post_valid=true;
  serial=result->after.serial;return 0;
 }
 APSD_writes++;assert(!"1341 is prohibited");return -EOPNOTSUPP;
}'''
assert fixture.count(old)==1;fixture=fixture.replace(old,new)
"""
source=source[:position]+adapt+'\n'+source[position:]
source=source.replace('prior_PHY_pthread_suite_reused=True,','prior_PHY_pthread_suite_reused=True,post_write_wire_samples_modeled=True,route_gate_always_closed=True,')
ast.parse(source)
exec(compile(source,'<existing-whole-owner-fixture-final-transfer>','exec'),dict(__file__=str(HERE/'run-owner-tests.py'),__name__='__main__',PRIOR=PRIOR))
