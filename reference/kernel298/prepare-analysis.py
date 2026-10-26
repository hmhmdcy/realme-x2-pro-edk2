"""Prepare independent RDI-pattern comparisons, retaining #297 evidence separately."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel297/analyze-stats-color.py').read_text().replace('297','298').replace('stats-r2','blc')
s=s.replace("names=['initial_unity_snapshot'", "names=['initial_unity_snapshot'")
a=s.index('names=[');b=s.index('matrix=',a)
s=s[:a]+'''names=['black_zero','black_4096','black_8192','black_16384','disable_black','disabled_black_update','reenable_black_with_wb','params_stopped_state_retained','image_reopen_black_zero','black_16384_stats_stopped','black_16384_stats_restarted']
gains=np.ones((11,3));gains[6:8,0]=2;gains[6:8,2]=1.5
levels=[0,4096,8192,16384,0,0,8192,8192,0,16384,16384]
offsets=[(v*16383+32767)//65535 for v in levels]
'''+s[b:]
s=s.replace('linear=np.clip(rgb*gains[phase],0,1);','linear=np.clip(np.maximum(rgb-offsets[phase]/16368,0)*gains[phase],0,1);')
s=s.replace('frame=n,gains_rgb=', 'frame=n,black_level_u16=levels[phase],hardware_offset_u14=offsets[phase],gains_rgb=')
s=s.replace('black_level_statistics_ipa_and_full_iq_incomplete=True,','sensor_dark_calibration_pending=True,ipa_and_full_iq_incomplete=True,bls_hardware_contract_only=True,')
s=s.replace('stats-pixel-validation.json','blc-pixel-validation.json')
(HERE/'analyze-blc-color.py').write_text(s)
s=(HERE.parent/'kernel297/analyze-frame-association.py').read_text().replace('297','298').replace('stats-r2-capture','blc-capture').replace('stats-pixel','blc-pixel').replace('frame-association-validation','blc-frame-association-validation')
(HERE/'analyze-blc-frame-association.py').write_text(s)
print('Prepared BLS subtract-before-gain model from independent RDI RAW reference.')
