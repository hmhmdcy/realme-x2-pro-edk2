from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel124'
t=(r/'reference/kernel123/validate-camss-schema.py').read_text().replace('123','124')
t=t.replace("('enabled-missing-supplies',{'status':b'okay\\0'},False)","('enabled-missing-supply',{'status':b'okay\\0','vdda-phy-supply':None},False)")
t=t.replace("no_board_analog_supply_guess=True,enabled_missing_supplies_rejected=True,","native_single_phy_supply=True,enabled_missing_supply_rejected=True,")
t=t.replace("assert not strict_errors(raw)","assert not strict_errors(raw)\nassert len(cells('vdda-phy-supply'))==1\n")
t=t.replace("(ref/'camss-schema-validation.json').write_text", "(ref/'camss-schema-validation.json').write_text")
(ref/'validate-camss-schema.py').write_text(t)
wrapper=(r/'reference/kernel123/schema-wrapper.py').read_text().replace('123','124');(ref/'schema-wrapper.py').write_text(wrapper)
print('SCHEMA124_BASE_CHECK_PREPARED')
