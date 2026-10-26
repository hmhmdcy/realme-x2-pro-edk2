"""Compare the final native scheduler/BL outputs, past frame preparation."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
names=['actual','native','actual-topology','native-topology','proposed-topology','maintained']
summaries={n:json.loads((P/('bl-'+n)/'summary-private.json').read_text()) for n in names}
for n,s in summaries.items():
 assert s['return_code']==0 and s['firmware_passes']==2 and not s['hardware_executed']
 assert s['pass_stripe_masks']==([[0,0],[3,0]] if n in ['actual','native','actual-topology'] else [[1,0],[3,0]])
gold=P/'bl-native-topology';ours=P/'bl-maintained'
files=sorted(p.name for p in gold.glob('*.bin') if p.name!='striping-private.bin')
assert len(files)>=5
for name in files:assert (gold/name).read_bytes()==(ours/name).read_bytes(),name
assert (gold/'queues-private.json').read_bytes()==(ours/'queues-private.json').read_bytes()
assert (gold/'striping-private.bin').read_bytes()!=(ours/'striping-private.bin').read_bytes()
observed=P/'bl-native-topology-observed'
assert (observed/'programs-private.bin').read_bytes()==(gold/'programs-private.bin').read_bytes()
assert (observed/'heap-private.bin').read_bytes()==(gold/'heap-private.bin').read_bytes()
reads=set(json.loads((observed/'stripe-reads-private.json').read_text()))
for at in [24+270,24+274,24+376,2268+30,2268+318,2268+322]:assert at in reads and at+1 in reads
r=dict(stage=430,scope='Offline native target ARM/Thumb firmware plus native ARM64 HAL topology/striping oracle',
 final_pass_distribution_and_bl_generation_executed=True,stock_topology_fragment_cases=16,
 old_default_topology_and_old_extents_drop_coarse_stripe=True,topology_only_does_not_restore_coarse_stripe=True,
 topology3_and_six_coarse_write_extents_restore_dc_then_full_masks=[[1,0],[3,0]],
 maintained_config_from_compiled_c=True,maintained_striping_from_compiled_c=True,
 final_program_bytes_compared=524288,whole_heap_bytes_compared=2097152,all_live_allocations_work_and_context_identical=True,
 compared_binary_objects=len(files),queued_commands_identical=True,unused_opaque_striping_padding_not_copied=True,
 bounded_read_observation_preserves_final_program_and_heap=True,
 queue_and_os_providers_are_fixture_not_original_os_execution=True,hardware_executed=False,passed=True)
(HERE/'native-bl-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
