"""Publish own adapter/client and sanitized evidence in the existing scope."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
for p in [HERE/'handoff.md',HERE.parents[1]/'NEXT-SESSION.md']:
 p.write_text(p.read_text().replace('（完整正确哈希以既有lock/384归档为准）',''))
s=(HERE.parent/'kernel384/finish-public.py').read_text()
s=s.replace('kernel384','kernel386').replace('through383-2026-10-20','through385-2026-10-21').replace('stage=384','stage=386')
s=s.replace('camera: generate native bypass striping and verify real IPE pixel output','camera: expose native IPE through V4L2 mem2mem and verify real queue lifecycle')
s=s.replace('last_hardware_experiment_stage=384','last_hardware_experiment_stage=386')
s=s.replace('all_synthetic_output_bytes_match_stage382_original_striping=True','mmap_dmabuf_and_two_m2m_contexts_eighteen_frames_hardware_verified=True')
exec(compile(s,str(HERE/'finish-public-generated.py'),'exec'),globals())
