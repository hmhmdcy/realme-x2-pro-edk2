from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');base=k/'drivers/media/platform/qcom/camss'
for name,markers in [('camss-csid-gen2.c',['static int csid_reset','static irqreturn_t csid_isr']),('camss-csid.c',['static int csid_set_power','static int csid_set_clock_rates']),('camss.c',['static int camss_cpas_init','static int camss_runtime_resume','static int camss_runtime_suspend'])]:
 s=(base/name).read_text();print(name)
 for marker in markers:
  start=s.find(marker);print(s[start:start+6500] if start>=0 else marker+' NOT FOUND')
