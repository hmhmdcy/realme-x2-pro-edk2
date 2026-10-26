from pathlib import Path
import hashlib,json,os
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
private=Path('/mnt/e/edk2-samurai-out/kernel210');before=private/'source-before'
assert json.loads((here/'baseline-semantic-validation.json').read_text())['remaining_changed_properties']==[]
assert json.loads((here/'camera-resources-validation.json').read_text())['pmic_p_held_reset']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert sha(board)=='439db9439d065cc87f0d34ca35c02e6c8e25ed787957946ebc986096ef8fa9ff'
text=board.read_text();old='/* Internal CSID TPG; CCI and all external sensors remain disabled. */'
assert text.count(old)==1
text=text.replace(old,'/* Physical front sensor and internal CSID test-pattern support. */')
fragment=(here/'front-camera.dtsi').read_text()
text+='\n'+fragment.replace('// SPDX-License-Identifier: BSD-3-Clause\n','',1)
board.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='210 board DTS camera graph written; persistent config/module build next. No device install/reboot yet. Rear PMIC GPIO1 held at verified reset-low through gpio-hog; Q GPIO4 normal MFD ownership.',next='Compile candidate and typed-reference semantic diff, then enable VIDEO_IMX471 and build compatible modules. Preserve all unrelated custom modules.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
report=dict(stage=210,board_before_sha256='439db9439d065cc87f0d34ca35c02e6c8e25ed787957946ebc986096ef8fa9ff',board_after_sha256=sha(board),static_vio_reference=True,pm8150l_q_reset_pin=4,pm8150l_unused_rear_reset_pin=1,front_configuration_from_proven200=True,pldo_input_supplies_not_invented=True,product_installed=False)
(here/'camera-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
