"""Reproduce the observed cleanup abort through original OEM entry/destroy code."""
from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
target=json.loads((P/'pre-reset-decoded-private.json').read_text());assert target['complete'] and target['exception_type']==3
s=(HERE.parent/'kernel363/check-firmware-init.py').read_text()
a=s.index("cases=[");b=s.index('\nrecords=[]',a);s=s[:a]+"cases=['no-shared-pointer','no-shared-size']"+s[b:]
anchor="        if 0x24746<=pc<0x24c58:return"
replacement="""        if pc==0x540:
            from unicorn.arm_const import UC_ARM_REG_R4
            state['observed_fault']=dict(pc=pc,far=uc.reg_read(UC_ARM_REG_R4),lr=uc.reg_read(UC_ARM_REG_LR));uc.emu_stop();return
        if 0x24746<=pc<0x24c58 or 0x1bf7e<=pc<0x1c012 or 0x6a80<=pc<0x6aa0 or 0x532<=pc<0x620:return"""
assert s.count(anchor)==1;s=s.replace(anchor,replacement)
s=s.replace('0x7e1c,0x8316,0x1bf7e,0x6998,0x25b3e','0x7e1c,0x8316,0x6b4a,0x6998,0x25b3e')
a=s.index('    assert u.reg_read(UC_ARM_REG_PC)==STOP');b=s.index('report=dict(stage=363',a)
s=s[:a]+'''    assert u.reg_read(UC_ARM_REG_PC)==0x540 and state['observed_fault']['far']==TARGET['far'] and state['observed_fault']['pc']==TARGET['fault_pc']
    assert state['responses']==[] and struct.unpack('<I',u.mem_read(REG+0x44,4))[0]==0x01000100
    records.append(dict(case=case,actual_entry_destroy_and_mutex_destroy_instructions_executed=True,
        masked_object_pointer_and_fault_pc_match_real_snapshot=True,failure_occurs_before_response_two=True,passed=True))
report=dict(stage=372,tests=records,original_firmware_functions=['fwEntryFunction','ICPHostInterface_destroy','vSYS_DestroyMutex','DALSYS_DestroyObject'],
    os_alloc_threads_signal_destruction_logging_and_mmu_providers_mocked=True,
    shared_pointer_or_size_absence_reproduces_target_cleanup_load_fault=True,
    not_proof_that_target_csr_was_zero_or_hardware_reset_clears_csr=True,phone_operations=False,passed=True)
(HERE/'shared-failure-validation.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report,indent=2))
'''
s=s.replace('import host','import host\nTARGET='+repr({k:target[k] for k in ['far','fault_pc']}),1)
(P/'shared-failure-private.py').write_text(s)
exec(compile(s,str(HERE/'check-shared-failure.py'),'exec'),dict(__file__=str(HERE/'check-shared-failure.py')))
