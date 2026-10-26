"""Affected measured-start/helper/supplier cases only; frozen owner not rerun."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
OLD=HERE.parent
BUILD=HERE/'test-build';BUILD.mkdir(exist_ok=True)
INC=BUILD/'include';(INC/'linux/usb').mkdir(parents=True,exist_ok=True)
# Reuse the existing high-quality host kernel shim, without executing/writing
# the preceding revision's test outputs or rerunning its unchanged owner tests.
old=(OLD/'test.py').read_text()
kernel=re.search(r"kernel='''(.*?)'''",old,re.S).group(1)
kernel=kernel.replace('struct device { int unused; };',
    'struct device { int unused; };\nstruct tcpc_dev { int unused; };\n#define dev_err(...) ((void)0)')
(INC/'test-kernel.h').write_text(kernel)
for h in ['bitops','delay','device','err','ktime','mutex','regmap','slab','string','kconfig']:
    (INC/f'linux/{h}.h').write_text('#include "test-kernel.h"\n')
(INC/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
(INC/'linux/usb/samurai-tcpm-apsd.h').write_bytes((OLD/'samurai-tcpm-apsd.h').read_bytes())

def function(text,name):
    m=re.search(r'^(?:static\s+)?(?:int|bool|void)\s+'+re.escape(name)+r'\([^;]+?\)\n\{',text,re.M)
    assert m,name
    pos=m.end();depth=1
    while depth:
        if text[pos]=='{':depth+=1
        elif text[pos]=='}':depth-=1
        pos+=1
    return text[m.start():pos]+'\n'

phy=(HERE/'qcom_pmic_typec_pdphy.c').read_text()
structs=[]
for n in ['pmic_typec_pdphy_irq_data','pmic_typec_pdphy']:
    s=re.search(r'^struct '+n+r' \{.*?^\};',phy,re.M|re.S)
    assert s,n
    structs.append(s.group(0))
(BUILD/'phy-structs.inc').write_text('\n'.join(structs)+'\n')
names=['qcom_pmic_typec_pdphy_handoff_quiet','qcom_pmic_typec_pdphy_apsd_verify',
       'qcom_pmic_typec_pdphy_apsd_release','qcom_pmic_typec_pdphy_apsd_begin',
       'qcom_pmic_typec_pdphy_apsd_cleanup','qcom_pmic_typec_pdphy_start',
       'qcom_pmic_typec_pdphy_quiesce_5v','qcom_pmic_typec_pdphy_finish_5v']
(BUILD/'phy-functions.inc').write_text('\n'.join(function(phy,n) for n in names))
exe=BUILD/'test-measured'
argv=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
      '-Wno-sign-compare','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
      '-pthread','-I'+str(INC),'-I'+str(HERE),'-I'+str(BUILD),str(HERE/'test-measured.c'),'-o',str(exe)]
compile=subprocess.run(argv,text=True,capture_output=True)
assert compile.returncode==0,compile.stderr
run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=20)
assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
probe=function(phy,'qcom_pmic_typec_pdphy_probe')
assert probe.index('tcpm->pmic_typec_pdphy =') < probe.index('devm_add_action_or_reset')
start=function(phy,'qcom_pmic_typec_pdphy_start')
assert start.index('qcom_pmic_typec_apsd_verify') < start.index('handoff_powered')
assert start.index('qcom_pmic_typec_pdphy_handoff_quiet') < start.index('handoff_powered = false')
assert 'samurai_contract_shutdown' in start
assert 'regmap_write' not in function(phy,'qcom_pmic_typec_pdphy_handoff_quiet')
manifest=json.loads((HERE/'source.json').read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(OLD/'delivery.json')==manifest['frozen_parent_delivery_sha256']
for name,pin in manifest['frozen_parent_sources'].items():assert sha(OLD/name)==pin
for row in manifest['sources'].values():assert sha(HERE/row['file'])==row['sha256']
result={'passed':True,'phone_accessed':False,'full_probe_integration':False,
 'production_helper':sha(HERE/'qcom_pmic_typec_apsd.c'),
 'production_supplier':sha(HERE/'qcom_pmic_typec_pdphy.c'),
 'actual_extracted_phy_functions':names,'sanitizers':['ASan','UBSan'],
 'compiler_diagnostics':compile.stderr,'stdout':run.stdout.strip(),
 'provider_lifecycle_static_checks':5,'frozen_parent_exact':True,
 'ADC_unit_and_DTB_tests_reused_not_rerun':True}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
