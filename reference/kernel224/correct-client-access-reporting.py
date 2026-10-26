"""Correct ambiguous client reporting without repeating successful native tests."""
from pathlib import Path
import hashlib,json
import host

here=Path(__file__).resolve().parent
items=[]
for name in ['standard-cam-validation.json','standard-gstreamer-validation.json']:
 p=here/name;original=p.read_bytes();r=json.loads(original)
 assert r['program_exit']==0 and r['frame_count']==6 and r.pop('no_cpu_pixel_buffer_access')
 backup=host.PRIVATE/(name+'.before-client-field-correction-private.json')
 assert not backup.exists();backup.write_bytes(original)
 r.update(no_client_pixel_buffer_access=True,software_isp_cpu_statistics_reads_raw=True,
          reporting_field_corrected_from='no_cpu_pixel_buffer_access',
          correction_does_not_change_native_test_outcome=True)
 p.write_text(json.dumps(r,indent=2)+'\n')
 items.append(dict(file=name,original_report_preserved_privately=True,
                   original_public_report_sha256=hashlib.sha256(original).hexdigest()))
report=dict(stage=224,corrected_reports=items,
            correction='The applications did not inspect scene pixels. CPU software ISP inside the pipeline did read RAW buffers.',
            original_native_outputs_retained_privately=True,native_captures_not_repeated=True)
(here/'client-reporting-correction-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
