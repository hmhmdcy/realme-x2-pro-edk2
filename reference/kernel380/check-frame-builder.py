from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'frame-regression';work.mkdir(exist_ok=True)
boot=(P/'camss-icp-a5-boot.h.proposed').read_text();a=boot.index('struct camss_a5_nv12_layout {');b=boot.index('struct camss_a5_session {',a)
header=(HERE/'camss-icp-a5-ipe.h').read_text();header='\n'.join(line for line in header.splitlines() if not line.startswith('#include'))
body=(HERE/'camss-icp-a5-ipe.c').read_text();body='\n'.join(line for line in body.splitlines() if not line.startswith('#include'))
(work/'actual-header.h').write_text(boot[a:b]+header);(work/'actual-body.inc').write_text(body);(work/'probe.c').write_text((HERE/'frame-regression.c').read_text())
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
records=json.loads((P/'striping-cases-private.json').read_text());striping=json.loads((HERE/'striping-validation.json').read_text());rows=[]
for case,measure in zip(records,striping['tests']):
 args=[str(work/'probe'),str(measure['width']),str(measure['height']),str(measure['output_port']),str(measure['max_cores']),case['stripe'],str(measure['bl_capacity'])]
 q=subprocess.run([*args,'encode'],capture_output=True,timeout=10);assert not q.returncode,q.stderr.decode();assert len(q.stdout)==3816
 (P/(case['slug']+'-encoded-frame-private.bin')).write_bytes(q.stdout);rows.append(dict(case=case['slug'],encoded_bytes=3816,passed=True))
case=records[0];measure=striping['tests'][0];q=subprocess.run([str(work/'probe'),'640','480','8','1',case['stripe'],str(measure['bl_capacity']),'negative'],capture_output=True,timeout=10)
assert not q.returncode,q.stderr.decode();assert q.stdout==b'FRAME_INVALID_CASES 55\n';(work/'negative-private.log').write_bytes(q.stdout+q.stderr)
report=dict(stage=380,actual_production_builder_and_header_compiled=True,asan_ubsan=True,tests=rows,invalid_cases=55,
 rejects_all_pairwise_buffer_overlaps=True,checked_u64_range_and_plane_arithmetic=True,invalid_inputs_do_not_modify_destination=True,
 iq_and_command_content_and_actual_dma_mapping_not_validated_by_builder=True,frame_submission_implemented=False,hardware_execution=False,passed=True)
(HERE/'frame-builder-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
