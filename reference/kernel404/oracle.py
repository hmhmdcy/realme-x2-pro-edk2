"""Reuse complete target HAL/FW with an explicit LTM-only wire fixture."""
from pathlib import Path
import importlib.util,inspect,struct
HERE=Path(__file__).resolve().parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module('routing396',HERE.parent/'kernel396/probe-routing.py');ltm=module('ltm403',HERE.parent/'kernel403/ltm-model.py');oracle=ltm.LTM();headers,offsets=oracle.headers(r.f.DATA+0x40000+2848)
scope=dict(r.__dict__)
text=inspect.getsource(r.striping).replace('def striping(width,height,port,cores,enabled):','def striping(width,height,port,cores,iq_blob,uv_swap=False,dirty=0xa5,layouts=None):')
text=text.replace("struct.pack_into('<III',config,off,20,width,height);","struct.pack_into('<III',config,off,20,width,height);struct.pack_into('<I',config,off+24,int(uv_swap));")
text=text.replace("struct.pack_into('<4I',config,off+52,width,height,width,height//2)","struct.pack_into('<4I',config,off+52,*(layouts[index!=0] if layouts else (width,height,width,height//2)))")
start=text.index(' for off in [52,68,244,260]:');end=text.index('u.mem_write(out,',start);text=text[:start]+' u.mem_write(iq,iq_blob);'+text[end:];text=text.replace('bytes([0xa5])*capacity','bytes([dirty])*capacity');exec(compile(text,'ltm-striping-original','exec'),scope);striping=scope['striping']
text=inspect.getsource(r.prepare).replace('def prepare(blob,width,height,port,cores,enabled,command):','def prepare(blob,width,height,port,cores,iq_blob,uv_swap=False,layouts=None):').replace('arrays=D+0x48000','arrays=iq+2592')
text=text.replace("struct.pack_into('<III',wire,off,20,width,height);","struct.pack_into('<III',wire,off,20,width,height);struct.pack_into('<I',wire,off+24,int(uv_swap));")
text=text.replace("struct.pack_into('<4I',wire,off+52,width,height,width,height//2)","struct.pack_into('<4I',wire,off+52,*(layouts[p!=0] if layouts else (width,height,width,height//2)))")
text=text.replace('0x20000000+width*height','0x20000000+(layouts[0][0]*layouts[0][1] if layouts else width*height)').replace('0x24000000+width*height','0x24000000+(layouts[1][0]*layouts[1][1] if layouts else width*height)')
start=text.index(' for off in [52,68,244,260]:');end=text.index(' m.payload=D+0x20000;',start);text=text[:start]+' m.u.mem_write(iq,iq_blob)\n'+text[end:]
text=text.replace('arrays+(32 if off==48 else 0)','arrays+(32 if off==44 else 64 if off==48 else 0)');exec(compile(text,'ltm-firmware-original','exec'),scope);prepare=scope['prepare']
def iq_blob(dc,ip,enabled=True):
 iq=bytearray(5584)
 for off in [52,68,244,260]:struct.pack_into('<I',iq,off,1)
 values=[int(enabled),1,1,1,0,19,38,7,0,0,1023,0,0,0,0,0,0,0,0,0,0,dc,ip];struct.pack_into('<23I',iq,2096,*values)
 struct.pack_into('<8I',iq,2624,0,1,r.f.DATA+0x40000+2672,155<<12,11 if enabled else 255,0,0,0);iq[2672:2828]=headers
 return bytes(iq)
