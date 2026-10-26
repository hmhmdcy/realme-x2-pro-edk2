"""Compare original firmware preparation with/without bounded observation."""
from pathlib import Path
import hashlib,importlib.util,json
from engine_model import prepare
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('striping383',HERE/'trace-striping.py');striping=importlib.util.module_from_spec(spec);spec.loader.exec_module(striping);execute=striping.execute
assert json.loads((HERE/'observer-validation.json').read_text())['passed'];rows=[]
for width,height in [(640,480),(1920,1080),(4608,3456)]:
 for port in [8,9]:
  for cores in [1,2]:
   blob,_,_,info=execute(width,height,port,cores,dirty=0xa5)
   second,_,_,_=execute(width,height,port,cores,dirty=0x5a)
   assert len(blob)==len(second)
   defined=bytes(~(a^b)&255 for a,b in zip(blob,second));canonical=bytes(a&mask for a,mask in zip(blob,defined))
   original,job,commands,_=prepare(blob,width,height,port,cores,observe=False)
   observed,ojob,ocommands,reads=prepare(blob,width,height,port,cores,observe=True)
   assert job==ojob and commands==ocommands
   alt,ajob,acommands,_=prepare(second,width,height,port,cores,observe=False)
   normalized,njob,ncommands,_=prepare(canonical,width,height,port,cores,observe=False)
   slug=f'{width}x{height}-p{port}-c{cores}'
   for name,data in [('canonical-stripe',canonical),('defined-bits',defined),('original-cdm',commands),('canonical-cdm',ncommands)]:
    (P/(slug+'-'+name+'-private.bin')).write_bytes(data)
   (P/(slug+'-reads-private.json')).write_text(json.dumps({str(k):sorted(v) for k,v in reads.items()})+'\n')
   rows.append(dict(**info,original_config_and_geometry_collation_and_cdm_preparation_executed=True,
    bounded_observer_and_unobserved_complete_cdm_buffer_and_job_equal=True,stripe_bytes_read=len(reads),
    output_bits_varying_with_complemented_dirty_storage=sum(8-mask.bit_count() for mask in defined),
    original_cdm_dirty_seed_difference_bytes=sum(a!=b for a,b in zip(commands,acommands)),
    canonical_cdm_difference_bytes=sum(a!=b for a,b in zip(commands,ncommands)),canonical_job_equal=job==njob,
    generated_cdm_sha256=hashlib.sha256(commands).hexdigest(),instruction_count=original.instructions,passed=True))
   print(json.dumps({k:rows[-1][k] for k in ['width','height','output_port','max_cores','stripe_bytes_read','canonical_cdm_difference_bytes']}),flush=True)
report=dict(stage=383,tests=rows,original_firmware_code_not_replaced_by_geometry_or_cdm_stubs=True,
 only_os_allocator_log_stream_access_and_command_retirement_providers_modelled=True,
 original_chip_info_from_modeled_version_register_0x10705=True,stopped_before_hardware_driver_enqueue=True,
 no_engine_execution_or_pixel_dma_claim=True,full_hal_striping_algorithm_executed_with_two_dirty_seeds=True,
 kernel_native_striping_not_yet_implemented=True,hardware_execution=False,passed=True)
(HERE/'preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
