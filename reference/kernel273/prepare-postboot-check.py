from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel270/check-postboot.py').read_text()
text=text.replace('stage=270','stage=273').replace("'v4l2_cci','s5k3m5']","'v4l2_cci','s5k3m5','s5kgw1']")
text=text.replace("('imx319 ','imx471 ','s5k3m5 ')","('imx319 ','imx471 ','s5k3m5 ','s5kgw1 ')")
text=text.replace("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')")
text=text.replace("['s5k3m5','failed to find sensor'","['s5kgw1','s5k3m5','gw1 identification','failed to find sensor'")
assert "'s5kgw1'" in text
p=R/'check-postboot.py';assert not p.exists();compile(text,p.name,'exec');p.write_text(text)
print('Four-sensor postboot inspection prepared')
