"""Extend the existing exact-function shutdown harness without changing its files."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "tcpm-sink-shutdown-candidate"


def function(source, name):
    m = re.search(r"^(?:static )?(?:int|void|bool) " + name + r"\([^;]*?\)\n\{", source, re.M)
    assert m, name
    end, depth = m.end(), 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[m.start():end] + "\n"


port = (HERE / "qcom_pmic_typec_port.c").read_text()
pd = (HERE / "qcom_pmic_typec_pdphy.c").read_text()
main = (HERE / "qcom_pmic_typec.c").read_text()
types = (HERE / "qcom_pmic_typec.h").read_text()
types += port[port.index("#define TYPEC_SNK_STATUS_REG"):port.index("static const char * const typec_cc_status_name")]
types += pd[pd.index("/* PD PHY register offsets"):pd.index("static void qcom_pmic_typec_pdphy_reset_on")]
selected = [
    (port, ["qcom_pmic_typec_port_stop", "qcom_pmic_typec_port_finish_5v"]),
    (pd, ["qcom_pmic_typec_pdphy_reset_on", "qcom_pmic_typec_pdphy_reset_off",
          "qcom_pmic_typec_pdphy_enable", "qcom_pmic_typec_pdphy_disable", "pmic_typec_pdphy_reset",
          "qcom_pmic_typec_pdphy_start", "qcom_pmic_typec_pdphy_quiesce_5v",
          "qcom_pmic_typec_pdphy_finish_5v", "qcom_pmic_typec_pdphy_stop"]),
    (main, ["qcom_pmic_typec_samurai_fixed_5v", "qcom_pmic_typec_samurai_sink",
            "qcom_pmic_typec_stop_samurai_5v", "qcom_pmic_typec_stop_samurai_contract", "qcom_pmic_typec_abort_samurai",
            "qcom_pmic_typec_remove", "qcom_pmic_typec_shutdown"]),
]
functions = "".join(function(s, n) for s, names in selected for n in names)
fixture = (OLD / "test-shutdown.c").read_text()
fixture = fixture.replace('static bool board_ok, pmic_ok, core_joined;',
                          'static bool board_ok, pmic_ok, core_joined;\nstatic int prepare_error, prepare_calls;')
fixture = fixture.replace('#include "actual-functions.inc"', r'''
static int tcpm_prepare_sink_shutdown(struct tcpm_port *p, unsigned int timeout_ms,
 int (*reader)(void *,int *), void *context)
{
 assert(p==&core&&timeout_ms==2000&&!core_joined&&context==&tcpm);
 (void)reader;
 assert(port.irqs_started&&pd.irqs_started&&pd.supply_held);
 assert(!write_attempts&&!port_disabled&&!pd_disabled&&!unregisters);
 prepare_calls++;return prepare_error;
}
#include "actual-functions.inc"
''')
fixture = fixture.replace('core_joined=false; board_ok=pmic_ok=true;',
                          'core_joined=false; board_ok=pmic_ok=true;prepare_error=prepare_calls=0;')
tail = r'''
 setup(false);tcpm.samurai_contract_shutdown=true;
 assert(qcom_pmic_typec_samurai_sink(&tcpm));
 fw.power="dual";assert(!qcom_pmic_typec_samurai_sink(&tcpm));fw.power="sink";
 assert(!qcom_pmic_typec_stop_samurai_contract(&tcpm));assert_off();assert(prepare_calls==1);
 assert(!qcom_pmic_typec_stop_samurai_contract(&tcpm)&&prepare_calls==1);
 puts("PASS high-contract path prepares with IRQ/worker alive before join/MMIO close");
 const int errors[]={-EOPNOTSUPP,-ETIMEDOUT,-EIO,-EAGAIN};
 for(unsigned i=0;i<ARRAY_SIZE(errors);i++){
  setup(false);tcpm.samurai_contract_shutdown=true;prepare_error=errors[i];
  qcom_pmic_typec_shutdown(&d);
  assert(prepare_calls==1&&!unregisters&&!write_attempts&&!tcpm.samurai_joined);
  assert(port.irqs_started&&pd.irqs_started&&supply_count==1&&tcpm.tcpc.fwnode==&fw);
  qcom_pmic_typec_remove(&d);
  assert(prepare_calls==2&&unregisters==1&&tcpm.samurai_joined&&!tcpm.tcpm_port);
  assert(tcpm.samurai_stop_error==errors[i]&&!tcpm.samurai_pd_quiet);
  assert(!write_attempts&&put_count==1&&!tcpm.tcpc.fwnode);
  assert(!port.irqs_started&&!pd.irqs_started&&!pd.reset_work.active);
  assert(!port.cc_debounce_dwork.active&&!port.tcpm_port&&cc_post_joins==1);
  qcom_pmic_typec_remove(&d);assert(unregisters==1&&prepare_calls==2&&put_count==1);
 }
 puts("PASS failed preparation keeps shutdown alive; void remove joins without false5V close");
 setup(false);tcpm.samurai_contract_shutdown=true;fail_write=1;
 qcom_pmic_typec_shutdown(&d);
 assert(tcpm.samurai_joined&&tcpm.samurai_stop_error==-EIO&&!tcpm.tcpm_port);
 int attempts=write_attempts;qcom_pmic_typec_remove(&d);
 assert(unregisters==1&&prepare_calls==1&&put_count==1&&write_attempts==attempts);
 puts("PASS post-join close error and later remove never unregister NULL or double-join");
 return 0;
}'''
before, after = fixture.rsplit(' return 0;\n}', 1)
fixture = before + tail + after
out = HERE / "qcom-tests"
out.mkdir(exist_ok=True)
(out / "actual-types.inc").write_text(types)
(out / "actual-functions.inc").write_text(functions)
(out / "test.c").write_text(fixture)
cmd = ["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
       "-Wno-sign-compare", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g",
       "-I", str(out), str(out / "test.c"), "-o", str(out / "test")]
test_env = {**os.environ, "TMPDIR": str(HERE / "tmp")}
built = subprocess.run(cmd, capture_output=True, text=True, env=test_env)
(out / "compile.log").write_text(built.stdout + built.stderr)
assert built.returncode == 0, built.stderr
run = subprocess.run([str(out / "test")], capture_output=True, text=True, timeout=10, env=test_env)
result = dict(passed=run.returncode == 0, returncode=run.returncode, stderr=run.stderr,
              groups=run.stdout.splitlines(), functions=[n for _, names in selected for n in names],
              source_sha256={n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                             for n in ["qcom_pmic_typec.c", "qcom_pmic_typec_port.c", "qcom_pmic_typec_pdphy.c"]},
              functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),
              kernel_device_IRQ_work_TCPM_regmap_boundaries_modeled=True,
              physical_contract_and_ADC_proof_mocked=True, compiler_tmpdir=str(HERE / "tmp"),
              phone_accessed=False, installed=False)
(HERE / "test-qcom-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
raise SystemExit(run.returncode)
