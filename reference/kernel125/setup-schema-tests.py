from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel125'
t=(r/'reference/kernel124/validate-camss-schema.py').read_text().replace('124','125')
t=t.replace('assert len(reg)==32','assert len(reg)==40').replace('0xacaf000,0xacb6000] and sizes==[4096]*6+[16384]*2','0xacaf000,0xacb6000,0xac40000,0xac42000] and sizes==[4096]*6+[16384]*2+[4096,20480]')
t=t.replace("len(strings('clock-names'))==31", "len(strings('clock-names'))==33").replace('clocks=31','clocks=33')
t=t.replace("('missing-icc',{'interconnects':None},False)","('missing-icc',{'interconnects':None},False),('missing-iova',{'memory-region':None},False)")
(ref/'validate-camss-schema.py').write_text(t)
(ref/'schema-wrapper.py').write_text((r/'reference/kernel124/schema-wrapper.py').read_text().replace('124','125'))
(ref/'test-endpoint-schema.py').write_text((r/'reference/kernel124/test-endpoint-schema.py').read_text().replace('124','125'))
(ref/'endpoint-schema-wrapper.py').write_text((r/'reference/kernel124/endpoint-schema-wrapper.py').read_text().replace('124','125'))
print('CPAS125_CAMSS_SCHEMA_10_MMIO_33_CLOCKS_AND_MANDATORY_IOVA_TESTS_READY')
