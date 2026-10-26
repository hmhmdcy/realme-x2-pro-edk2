"""Correct /lib vs /usr/lib alias comparison after the first preflight failed before mutation."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
old=json.loads((host.PRIVATE/'stage-failure-inspection-private.json').read_text());assert old['state']['terminal'] and old['state']['exit_code']==1 and not old['backup_created']
source=(R/'stage-cci.py').read_text()
source=source.replace('k276-cci-transaction','k276-cci-transaction-r2').replace('k276-cci-candidate.ko','k276-cci-candidate-r2.ko').replace('stage-response-private.log','stage-r2-response-private.log')
a="dest=Path(subprocess.check_output(['modinfo','-n','i2c_qcom_cci'],text=True).strip());assert dest==tree/'kernel/drivers/i2c/busses/i2c-qcom-cci.ko'"
b="observed=Path(subprocess.check_output(['modinfo','-n','i2c_qcom_cci'],text=True).strip());dest=tree/'kernel/drivers/i2c/busses/i2c-qcom-cci.ko';assert observed.resolve()==dest.resolve()"
assert source.count(a)==1;source=source.replace(a,b)
exec(compile(source,'cci-stage-r2-derived.py','exec'),dict(__file__=str(R/'stage-cci.py')))
