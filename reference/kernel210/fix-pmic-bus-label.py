from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert hashlib.sha256(board.read_bytes()).hexdigest()=='b633ade429c4cf34726de6c3cf076507338bedbf856e183d54e5d04b0079ecf9'
text=board.read_text();fragment=(here/'front-camera.dtsi').read_text().replace('// SPDX-License-Identifier: BSD-3-Clause\n','',1)
old=fragment.replace('&i2c4 {','&i2c1 {',1);assert text.count(old)==1
board.write_text(text.replace(old,fragment))
report=json.loads((here/'camera-source-validation.json').read_text());report.update(board_after_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),pmic_source_label='i2c4',pmic_controller_path='/soc@0/geniqup@8c0000/i2c@890000',first_candidate_wrong_i2c_label_caught_by_path_assertion=True,first_candidate_not_deployed=True)
(here/'camera-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
