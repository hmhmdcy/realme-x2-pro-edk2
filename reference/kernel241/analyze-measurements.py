from pathlib import Path
import json,struct
from measurement_decode import regression,summarize_measurements
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
reports={}
for kind in ['differential','ordered','afw','combined']:
    file=P/'evidence'/kind/'events-private.jsonl'
    if not file.exists():continue
    records=[json.loads(line) for line in file.read_text().splitlines()]
    report=summarize_measurements(records)
    protocol=next((row for row in records if row['kind']=='command' and row['message_id']==0x55),None)
    if protocol:
        report['protocol_query']={key:protocol[key] for key in ['matching_ack','ack_result','ack_error','indication_status']}
        fields={18:'supl_version_enum',19:'lpp_profile',25:'lppe_up',26:'lppe_cp'}
        values={}
        for tag,name in fields.items():
            raw=bytes.fromhex(protocol['ind_tlvs'].get(str(tag),''))
            assert not raw or len(raw)==4
            values[name]=struct.unpack('<I',raw)[0] if raw else None
        report['protocol_query']['values']=values
    reports[kind]=report
report=dict(stage=241,regression=regression(),reports=reports,identifiers_and_coordinates_not_exported=True)
(R/'measurement-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
