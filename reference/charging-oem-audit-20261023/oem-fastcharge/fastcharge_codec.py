"""Offline metadata/received-frame decoder. No bus, GPIO, reply or update API."""
from pathlib import Path
import argparse,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private') if sys.platform=='win32' else Path('/mnt/e/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private')
SYMBOL='Stm8s_fw_data_4400_svooc_5000MA'
HEADER='drivers/power/oppo/vooc_ic/oplus_vooc_fw.h'
VOOC='drivers/power/oppo/oplus_vooc.c'

def sha(data): return hashlib.sha256(data).hexdigest()
def cached(name): return PRIVATE/'oem'/name.replace('/','--')
def uncomment(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:''.join('\n' if x=='\n' else ' ' for x in m[0]),text,flags=re.S)
def array_bytes(body):
    tokens=uncomment(body).strip().split(',')
    if tokens[-1].strip()=='':tokens.pop()
    if not tokens or any(not re.fullmatch(r'\s*(?:0[xX][0-9a-fA-F]+|[0-9]+)\s*',x) for x in tokens):
        raise ValueError('array contains unsupported or missing numeric token')
    values=[int(x.strip(),16 if x.strip().lower().startswith('0x') else 10) for x in tokens]
    if any(x>255 for x in values):raise ValueError('non-byte array value')
    return bytes(values)

def firmware_branches(text):
    # Deliberately scoped to this exact symbol/guard, not a general C preprocessor.
    pattern=(r'#ifdef CONFIG_OPLUS_SM8150R_CHARGER\s*'
      r'(unsigned char '+SYMBOL+r'\[\]\s*=\s*\{(?P<yes>.*?)\};)\s*'
      r'#else\s*(unsigned char '+SYMBOL+r'\[\]\s*=\s*\{(?P<no>.*?)\};)\s*#endif')
    matches=list(re.finditer(pattern,text,re.S))
    if len(matches)!=1:raise ValueError('missing/ambiguous expected firmware guard')
    m=matches[0]
    return {value:dict(data=array_bytes(m[label]),line=text[:m.start(label)].count('\n')+1)
            for value,label in [(True,'yes'),(False,'no')]},m[0]

def inspect_stm8s(data,expected=None):
    if not isinstance(data,bytes) or len(data)<68 or len(data)>65536 or len(data)%34:
        raise ValueError('STM8S record length must be whole 34-byte records')
    addresses=[int.from_bytes(data[i:i+2],'little') for i in range(0,len(data),34)]
    if addresses[0]!=0x8800 or addresses[-1]!=0x9fe0:raise ValueError('unexpected image endpoints')
    if any(a<0x8800 or a>0x9fe0 or a%32 for a in addresses):raise ValueError('unaligned/out-of-range address')
    if any(b<=a for a,b in zip(addresses,addresses[1:])):raise ValueError('duplicate/backward address')
    if expected is not None and data!=expected:raise ValueError('does not match selected fixed OEM image')
    gaps=[dict(after=hex(a),before=hex(b),unrepresented_bytes=b-a-32)
          for a,b in zip(addresses,addresses[1:]) if b-a!=32]
    return dict(format='STM8S record stream: LE16 flash address then 32 data bytes',bytes=len(data),records=len(addresses),
       first_address=hex(addresses[0]),last_address=hex(addresses[-1]),gaps=gaps,
       firmware_version=data[-4],version_offset=len(data)-4,sha256=sha(data),
       tail32_hex=data[-32:].hex(),checksum='no checksum/authentication algorithm established by this parser',
       running_mcu_version_known=False)

def notification_constants(text):
    return {int(value,16):name.removeprefix('VOOC_NOTIFY_') for name,value in
       re.findall(r'^#define\s+(VOOC_NOTIFY_[A-Z_]+)\s+(0x[0-9a-fA-F]+)',text,re.M)}

def decode_frame(bits,context='normal',firmware_present=True):
    """Classify an already observed seven-bit value in OEM branch order.

    Context is explicit: this function does not fabricate a captured handshake,
    authorize charging, calculate replies or claim timing is a passive protocol.
    """
    if context not in ['normal','adapter_model','mcu_version','adapter_version']:
        raise ValueError('unknown receive context')
    if not isinstance(bits,str) or not re.fullmatch('[01]{7}',bits):raise ValueError('exactly seven binary bits required')
    data=int(bits,2)
    constants=notification_constants(cached(VOOC).read_text())
    if context=='normal' and not bits.startswith('101'):
        return dict(value=data,kind='invalid_prefix',context=context,accepted_framing=False)
    # These three branches precede the adapter-model payload branch.
    leading={0x52,0x54,0x5e}
    before_version={0x58,0x5a,0x53,0x59,0x5c,0x5d,0x56}
    if data in leading:
        kind='notification';name=constants[data]
    elif context=='adapter_model':
        return dict(value=data,kind='adapter_model',context=context,accepted_framing=True,
          reserved_error=data in [0x0f,0x1f,0x3f,0x7f],zero_maps_to='CHARGER_SUBTYPE_FASTCHG_VOOC' if data==0 else None)
    elif data in before_version:
        kind='notification';name=constants[data]
    elif context=='mcu_version' and firmware_present:
        return dict(value=data,kind='mcu_version',context=context,accepted_framing=True)
    elif context=='adapter_version':
        return dict(value=data,kind='adapter_version',context=context,accepted_framing=True)
    elif data==0x5b:
        kind='notification';name=constants[data]
    else:return dict(value=data,kind='unknown',context=context,accepted_framing=True,oem_data_error=True)
    return dict(value=data,kind=kind,name=name,context=context,accepted_framing=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    frame=sub.add_parser('frame');frame.add_argument('bits');frame.add_argument('--context',default='normal')
    fw=sub.add_parser('firmware');fw.add_argument('path',type=Path);fw.add_argument('--sm8150r',choices=['yes','no'],required=True)
    args=parser.parse_args()
    if args.command=='frame':result=decode_frame(args.bits,args.context)
    else:
        branches,_=firmware_branches(cached(HEADER).read_text())
        if not args.path.is_file() or args.path.stat().st_size>65536:raise ValueError('bounded regular firmware file required')
        result=inspect_stm8s(args.path.read_bytes(),branches[args.sm8150r=='yes']['data'])
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
