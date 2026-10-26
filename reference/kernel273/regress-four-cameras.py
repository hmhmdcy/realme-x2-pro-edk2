"""Alternate all four physical sensors after r21 deployment and desktop restore."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'main-capture-validation.json').read_text())['all_passed']
assert json.loads((R/'desktop-restore-validation.json').read_text())['desktop_started']
text=(R.parent/'kernel270/regress-three-cameras.py').read_text()
changes=[('k270-three-camera-regression-r1','k273-four-camera-regression-r1'),('k270-work','k273-work'),('stage=270','stage=273'),
 ("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010']"),
 ("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')"),
 ("['cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']","['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']"),
 ("ids=dict(front=","ids=dict(main='/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10',front="),
 ("pattern=['front','wide','tele','front','tele','wide']*2+['tele','tele']","pattern=['front','main','wide','tele','main','front','tele','wide']*2+['main','main']"),
 ('interrupted=index==12','interrupted=index==16'),('timeout=2 if interrupted','timeout=3 if interrupted'),
 ("len(state['runs'])==14","len(state['runs'])==18"),('front_and_two_rear_cameras=True','front_and_three_rear_cameras=True'),
 ('three-camera-regression-response','four-camera-regression-response'),('three-camera-regression-validation','four-camera-regression-validation')]
for a,b in changes:assert a in text,a;text=text.replace(a,b)
exec(compile(text,'four-camera-regression273-generated.py','exec'),dict(__file__=str(R/'four-camera-regression-generated.py')))
