"""Keep individual EEPROM samples and provisional values outside the repository."""
from pathlib import Path
import hashlib,json,shlex,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
poll=json.loads((P/'calibration-hold-poll-private.json').read_text());summary=poll['summary']
assert summary['passed'] and summary['duplicate_reads_equal'] and not summary['power_owner_still_live']
samples=[]
for index,row in enumerate(summary['reads'],1):
 command=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k299-eeprom-r1/eeprom-read{index}-private.bin').read_bytes();assert len(b)==12287;sys.stdout.buffer.write(b)"
 q=host.ssh('python3 -c '+shlex.quote(command),timeout=15);assert len(q.stdout)==row['bytes'] and hashlib.sha256(q.stdout).hexdigest()==row['sha256']
 p=P/f'imx319-eeprom-read{index}-private.bin';assert not p.exists();p.write_bytes(q.stdout);samples.append(q.stdout)
assert samples[0]==samples[1]
# These two offsets are directly present at the start of the AF description.
# Full-layout and factory-checksum verification still precede any application.
macro,infinity=struct.unpack_from('<HH',samples[0],146)
candidate=dict(source='direct factory AF prefix offsets146/148, little-endian masks65535',macro=macro,infinity=infinity,
 within10bit_lens_code_range=macro<=1023 and infinity<=1023,factory_checksum_not_verified=True,not_applied=True)
(P/'imx319-af-candidate-private.json').write_text(json.dumps(candidate,indent=2)+'\n')
out=dict(stage=299,bytes_per_read=len(samples[0]),independent_full_reads=2,duplicate_reads_equal=True,host_transfer_hashes_verified=True,
 unit_data_and_hashes_kept_private=True,af_prefix_candidate_within10bit_range=candidate['within10bit_lens_code_range'],
 factory_checksum_and_full_layout_not_verified=True,no_values_applied=True,no_eeprom_data_writes=True)
(HERE/'eeprom-transfer-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
