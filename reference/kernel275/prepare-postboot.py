from pathlib import Path
R=Path(__file__).resolve().parent
for name in ['refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-postboot.py']:
 text=(R.parent/'kernel273'/name).read_text().replace('kernel273','kernel275').replace('k273','k275').replace('stage=273','stage=275').replace('k270-work','k273-work').replace('K273_','K275_')
 if name=='bootstrap-postboot.py':
  text=text.replace('packages-verified-state-private.json','packages-state-private.json')
  anchor="assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10/compatible').read_bytes()==b'samsung,s5kgw1\\0'"
  assert anchor in text;text=text.replace(anchor,anchor+"\nassert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4a000/i2c-bus@0/lens@72/compatible').read_bytes()==b'onnn,lc898219xi\\0'")
 if name=='check-postboot.py':
  anchor="'v4l2_cci','s5k3m5','s5kgw1']";assert anchor in text;text=text.replace(anchor,"'v4l2_cci','s5k3m5','s5kgw1','lc898219xi']")
  text=text.replace("['s5kgw1','s5k3m5'","['lc898219','s5kgw1','s5k3m5'")
 p=R/name;assert not p.exists()
 if name.endswith('.py'):compile(text,name,'exec')
 p.write_text(text)
print('Fresh USB discovery, boot identity adoption and nine-module inspection prepared')
