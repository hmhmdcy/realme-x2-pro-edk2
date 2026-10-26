"""Only new bridge/metadata functions, actual full production bodies."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PD=REF/'charging-oem-audit-20261023/pd5v-owner-context-r2'
OLD=REF/'charging-session-20261023/apsd-session-owner-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
clean=lambda s:'\n'.join(line for line in s.splitlines() if not line.startswith('#include'))+'\n'
boundary=(PD/'kernel-boundary-fixture.inc').read_text().split('#include "qcom_pmic_typec_5v.h"')[0]
boundary=boundary.replace('struct device { struct device_node *of_node; int refs;struct device *parent;void *driverdata; };',
 'struct regmap;\nstruct device { struct device_node *of_node; int refs;struct device *parent;void *driverdata;bool optin,bridge,suspended;int pm_refs;struct regmap *map; };')
boundary=boundary.replace(' if(!strcmp(s,"vdd-pdphy-supply"))',
 ' if(!strcmp(s,"samurai,apsd-typec"))return phandle_present?&other_node:NULL;\n if(!strcmp(s,"vdd-pdphy-supply"))')
# Boundary declaration must precede the original OF fake.
boundary=boundary.replace('static bool wrong_supply;', 'static bool wrong_supply;\nstatic bool phandle_present,platform_present;')
headers='\n'.join(clean(p.read_text()) for p in [HERE/'samurai-apsd-backend.h',HERE/'samurai-apsd-owner.h',HERE/'samurai-apsd-once.h',HERE/'samurai-usb-input-decode.h',HERE/'qcom_pmic_typec_5v.h',
 REF/'charging-session-20261023/eud-runtime-window-candidate/eud-com-window.h',
 REF/'charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h'])
ch=(HERE/'core.h').read_text();windows=ch[ch.index('enum dwc3_gadget_window_state {'):ch.index('/**\n * struct dwc3 -')]
fixture=(HERE/'test-bridge.c').read_text().replace('static bool phandle_present=true,platform_present=true;', '')
fixture=fixture.replace('/* PD_BOUNDARY */',boundary).replace('/* ACTUAL_HEADERS */',headers).replace('/* WINDOW_TYPES */',windows)
fixture=fixture.replace('/* ACTUAL_PD */',clean((HERE/'qcom_pmic_typec_5v.c').read_text())).replace('/* ACTUAL_OWNER */',clean((HERE/'samurai-apsd-owner.c').read_text()))
out=HERE/'test-private';out.mkdir(exist_ok=True);(out/'actual-bridge.c').write_text(fixture)
cmd=['gcc','-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'actual-bridge.c'),'-o',str(out/'test-bridge')]
p=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.txt').write_text(p.stdout+p.stderr)
if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
p=subprocess.run([str(out/'test-bridge')],capture_output=True,text=True);(out/'run.txt').write_text(p.stdout+p.stderr);print(p.stdout+p.stderr)
r=dict(passed=p.returncode==0,affected_groups=len(p.stdout.splitlines()),groups=p.stdout.splitlines(),exit_code=p.returncode,
 tested_files={n:sha(HERE/n) for n in ['samurai-apsd-owner.c','samurai-apsd-owner.h','qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','bridge-functions.inc','test-bridge.c','run-tests.py','Kconfig.fragment']},
 actual_fixture_sha256=sha(out/'actual-bridge.c'),compile_command=cmd,source_bodies='whole actual owner and PD5V candidate C, unchanged once/decoder headers',
 original_owner_13_groups_rerun=False,original_PD_R2_8_groups_rerun=False,old_component_suites_rerun=False,
 boundaries='fake kernel/OF/regmap/work scheduling; genuine heap owner lifetime under ASan/UBSan; deterministic interleave, not a full concurrency or hardware proof',device_accessed=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(p.returncode)
