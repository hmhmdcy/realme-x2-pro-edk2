"""Compare independent packed C and type-table-driven Python outputs privately."""
from pathlib import Path
import hashlib,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'eeprom-layout-validation.json').read_text())['lsc_samples_decoded']==4420
binary=P/'decode-lsc-private'
q=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'decode-lsc.c'),'-o',str(binary)],capture_output=True)
(P/'lsc-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary),'--self-test'],capture_output=True);assert q.returncode==0
(P/'lsc-self-test-private.log').write_bytes(q.stdout+q.stderr)
decoded=json.loads((P/'unit-wb-lsc-private.json').read_text())
records=[]
for index in [1,2]:
    q=subprocess.run([str(binary),str(P.parent/f'kernel299/imx319-eeprom-read{index}-private.bin')],capture_output=True)
    assert q.returncode==0 and len(q.stdout)==4*221*2
    result=list(struct.unpack('<884H',q.stdout))
    for row in decoded['lsc']:
        assert result==[v for channel in row['channels'] for v in channel]
    (P/f'lsc-independent-read{index}-private.bin').write_bytes(q.stdout)
    records.append(dict(read=index,all5_lights_match=True,points_per_channel=221,channels=4))
report=dict(stage=304,strict_c_compile=True,independent_packed40_vectors_pass=True,
            private_sample_comparisons=records,passed=True,individual_values_not_published=True,
            no_calibration_applied=True,factory_checksum_verified=False,
            c_source_sha256=hashlib.sha256((HERE/'decode-lsc.c').read_bytes()).hexdigest())
(HERE/'lsc-crosscheck-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
