"""Compile complete candidate/default functions with explicit kernel boundaries."""
from pathlib import Path
import hashlib, json, re, subprocess, tempfile
HERE = Path(__file__).resolve().parent
texts = {n:(HERE/n).read_text() for n in ['qcom_pmic_typec.c','qcom_pmic_typec_port.c','qcom_pmic_typec_pdphy.c']}

def function(source, name):
    m = re.search(r'^(?:static )?(?:int|void|bool) '+name+r'\([^;]*?\)\n\{',source,re.M)
    assert m, name
    end, depth = m.end(), 1
    while depth:
        if source[end] == '{': depth += 1
        elif source[end] == '}': depth -= 1
        end += 1
    return source[m.start():end]+'\n'

port, pd, main = texts['qcom_pmic_typec_port.c'],texts['qcom_pmic_typec_pdphy.c'],texts['qcom_pmic_typec.c']
types = (HERE/'qcom_pmic_typec.h').read_text()
types += port[port.index('#define TYPEC_SNK_STATUS_REG'):port.index('static const char * const typec_cc_status_name')]
types += pd[pd.index('/* PD PHY register offsets'):pd.index('static void qcom_pmic_typec_pdphy_reset_on')]
selected = [
    (port,['qcom_pmic_typec_port_stop','qcom_pmic_typec_port_finish_5v']),
    (pd,['qcom_pmic_typec_pdphy_reset_on','qcom_pmic_typec_pdphy_reset_off','qcom_pmic_typec_pdphy_enable','qcom_pmic_typec_pdphy_disable','pmic_typec_pdphy_reset','qcom_pmic_typec_pdphy_start','qcom_pmic_typec_pdphy_quiesce_5v','qcom_pmic_typec_pdphy_finish_5v','qcom_pmic_typec_pdphy_stop']),
    (main,['qcom_pmic_typec_samurai_fixed_5v','qcom_pmic_typec_stop_samurai_5v','qcom_pmic_typec_remove','qcom_pmic_typec_shutdown']),
]
functions = ''.join(function(s,n) for s,names in selected for n in names)
with tempfile.TemporaryDirectory(prefix='sink-shutdown-') as name:
    out = Path(name)
    (out/'actual-types.inc').write_text(types)
    (out/'actual-functions.inc').write_text(functions)
    binary = out/'test'
    cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I',str(out),str(HERE/'test-shutdown.c'),'-o',str(binary)]
    built=subprocess.run(cmd,capture_output=True,text=True)
    print(built.stdout+built.stderr,end='');assert built.returncode==0
    run=subprocess.run([str(binary)],capture_output=True,text=True)
    print(run.stdout+run.stderr,end='');assert run.returncode==0
result=dict(passed=True,functions=[n for _,names in selected for n in names],groups=run.stdout.splitlines(),
            production_functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),
            source_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in texts.items()},
            kernel_device_IRQ_work_TCPM_and_regmap_boundaries_mocked=True,phone_test=False)
(HERE/'shutdown-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
