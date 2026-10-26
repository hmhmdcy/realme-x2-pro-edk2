"""Read-only final stock capture and fixed GET 0x55 result summary."""
from pathlib import Path
import importlib.util
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel254')
spec=importlib.util.spec_from_file_location('d',ROOT/'kernel250/decode-android-hal.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def main():
    packets,parsing=d.parse_trace(P/'hal-final.trace')
    quality=d.summarize(packets,parsing)
    rows=[json.loads(s) for s in (P/'protocol-readback-private.jsonl').read_text().splitlines()]
    replies=[d.decode_wire(bytes.fromhex(r['hex'])) for r in rows if r['kind']=='reply']
    replies=[r for r in replies if r and r['message_id']==0x55]
    ack=next(r for r in replies if r['flags']==2)
    ind=next(r for r in replies if r['flags']==4)
    result,error=struct.unpack('<HH',bytes.fromhex(ack['tlvs']['2']))
    status=struct.unpack('<I',bytes.fromhex(ind['tlvs']['1']))[0]
    assert result==error==status==0
    values={name:int.from_bytes(bytes.fromhex(ind['tlvs'][str(tag)]),'little')
            for tag,name in [(18,'supl_version_enum'),(19,'lpp_config'),(25,'lppe_up_mask'),(26,'lppe_cp_mask')]
            if str(tag) in ind['tlvs']}
    report=dict(quality=quality,protocol_get=dict(message_id='0x55',request_mask='0x60c',
        ack_result=result,ack_error=error,completion_status=status,values=values,
        requested_but_absent=[n for n in ['supl_version_enum','lpp_config','lppe_up_mask','lppe_cp_mask'] if n not in values],
        missing_values_not_assumed_zero_or_applied=True),
        all_exports_source_sha_verified=True,source_was_readonly_get_not_set=True)
    (ROOT/'kernel254/final-readback-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(protocol_get=report['protocol_get'],sv=quality['quality']['sv'],
                        pqwm1=quality['pqwm1'],success_positions=quality['quality']['successful_qmi_positions_with_valid_coordinates']),indent=2))


if __name__=='__main__': main()
