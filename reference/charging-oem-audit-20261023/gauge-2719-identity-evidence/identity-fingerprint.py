"""Saved FirmwareVersion evidence only; no I2C, transport or policy interface.

The historical 11-byte payload can be fingerprinted without claiming its
FirmwareVersion field byte order or mapping 0x2719 to a catalog part.
"""
from pathlib import Path
import argparse,hashlib,json,re
KNOWN_PAYLOAD=bytes.fromhex('2719000400060003850200')
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def require(condition,message):
    if not condition:raise ValueError(message)


def decode_saved(text):
    require(isinstance(text,bytes) and 0<len(text)<=65536,'bounded saved text required')
    text=text.decode('ascii')
    lines=[line for line in text.splitlines() if line.startswith('FirmwareVersion')]
    require(len(lines)==1,'exactly one complete FirmwareVersion record required')
    tokens=lines[0].split(' ');require(tokens[0]=='FirmwareVersion','record prefix')
    fields={}
    for token in tokens[1:]:
        require(re.fullmatch('[a-z_]+=[0-9a-fx]+',token),'record token')
        key,value=token.split('=');require(key not in fields,'duplicate record field');fields[key]=value
    require({'command','request','response','validation'}<=fields.keys()
        and fields.keys()<={'command','request','response','validation','payload','length','checksum'},'record fields')
    require(fields['command']=='0x0002' and fields['request']=='000200' and fields['validation']=='0','fixed historical command/route/return')
    require(re.fullmatch('[0-9a-f]{72}',fields['response']),'complete 36-byte frame required')
    packet=bytes.fromhex(fields['response'])
    require(packet[:2]==b'\x02\x00' and packet[35]==15,'firmware echo/payload11/length15')
    require((sum(packet[:13])+packet[34])&255==255,'firmware checksum')
    for name,expected in [('payload','11'),('length','15'),('checksum',f'{packet[34]:02x}')]:
        if name in fields:require(fields[name]==expected,'printed field contradicts actual frame: '+name)
    payload=packet[2:13]
    # SLUUA65E 12.2.2 supplies this field order. Its ttTT prose disagrees
    # with the one-byte TT layout token. Report slices only; do not turn a
    # near-family layout or an apparent byte order into exact-chip semantics.
    return dict(schema='samurai-saved-gauge-firmware-fingerprint-v1',command=2,
        complete_frame_valid=True,frame_sha256=sha(packet),payload_sha256=sha(payload),payload_hex=payload.hex(),
        payload_bytes=len(payload),length_byte=packet[35],historical_payload_match=payload==KNOWN_PAYLOAD,
        standard_layout_raw_slices_unconfirmed=dict(device_number=payload[:2].hex(),version=payload[2:4].hex(),build_number=payload[4:6].hex(),
            firmware_type=payload[6:7].hex(),impedance_track_version=payload[7:9].hex(),reserved_rr=payload[9:10].hex(),reserved_ee=payload[10:11].hex()),
        exact_model=None,firmware_fields_semantically_verified=False,new_mac_compatibility_verified=False,
        tca_mapping_verified=False,new_mac_query_authorized=False,device_accessed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--saved');a=p.parse_args()
    value=decode_saved(Path(a.saved).read_bytes()) if a.saved else dict(source_only=True,device_accessed=False,new_mac_query_authorized=False)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
