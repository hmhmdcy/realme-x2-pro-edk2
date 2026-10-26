from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel270/probe-telephoto.py').read_text()
changes=[('k270-telephoto-capture-r1','k273-main-capture-r1'),('k270-work','k273-work'),('stage=270','stage=273'),
 ("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010']"),
 ("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')"),
 ('/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10'),
 ("camera='S5K3M5 telephoto'","camera='S5KGW1 main'"),('telephoto-capture-response','main-capture-response'),
 ('telephoto-capture-validation','main-capture-validation')]
for a,b in changes:assert a in text,a;text=text.replace(a,b)
p=R/'probe-main.py';assert not p.exists();compile(text,p.name,'exec');p.write_text(text)
print('Bounded physical main-camera RAW/RGB test prepared')
