from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel382'
for name in ['boot-worker.py','launch-boot.py','poll-boot.py','preflight.py','snapshot-collector.py','firmware-context-validation.json','check-worker.py']:
 s=(OLD/name).read_text().replace('stage=382','stage=384').replace('k382-boot-','k384-boot-').replace('Prepared382','Prepared384')
 if name=='boot-worker.py':
  a=s.index(" for source,name in [('ipe-stripe.bin'");b=s.index(" save('load-core')",a);s=s[:a]+s[b:]
 if name=='launch-boot.py':
  a=" 'ipe-stripe.bin':P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin',\n";assert a in s;s=s.replace(a,'')
  a="['alignment-abi','bypass-iq','transfer','owner','dispatch','worker','intree-build']";assert a in s;s=s.replace(a,"['serializer','formats','transfer','worker','intree-build']")
 if name=='preflight.py':
  s=s.replace("camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()", "camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),\n battery={p.name:{n:(p/n).read_text().strip() for n in ['capacity','temp','status'] if (p/n).exists()} for p in Path('/sys/class/power_supply').iterdir() if (p/'type').read_text().strip()=='Battery'}")
 (HERE/name).write_text(s)
print('Prepared a unique synthetic transaction with no uploaded striping/IQ fixture.')
