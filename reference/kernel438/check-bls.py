from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
data=json.loads((P/'ife-bls-candidates-private.json').read_text());rows=[]
for variant,stage,file in [('sunny_imx319',299,'factory-bls-export-validation.json'),('qtech_s5k3m5sx',306,'tele-bls-export-validation.json'),('sunny_imx471',438,'front-factory-bls-export-validation.json')]:
 row=next(r for r in data if r['variant']==variant);proof=json.loads((HERE.parent/('kernel'+str(stage))/file).read_text())
 assert row['source_sha256']==proof['source_sha256'] and row['ife_regions']==proof['ife_regions']
 assert proof['independent_reader_and_direct_decoder_agree'] and row['all_ife_regions_same'] and row['root_enable_values']==[1]
 rows.append(dict(variant=variant,ife_roots=row['ife_roots'],ife_regions=row['ife_regions'],original_reader_and_direct_decoder_agree=True,xml_evidence='../kernel'+str(stage)+'/'+file,ife_values_not_taken_from_bps=True,profile_restored=variant!='sunny_imx471'))
r=dict(stage=438,rows=rows,front_bls_recovered_but_full_front_profile_not_applied=True,individual_dark_calibration_claimed=False,passed=True)
(HERE/'bls-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
