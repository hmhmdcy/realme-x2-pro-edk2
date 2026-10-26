"""Bounded offline AArch64 configuration-library execution with explicit libc/C++ providers."""
from pathlib import Path
import ctypes
import hashlib
import json
import re
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/cy122/.local/lib/python3.14/site-packages')
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_INVALID
from unicorn.arm64_const import *

LIB_SHA = '9b317c9e3154929964aef1cca37b79fda00f7201c119d5f4cf9656f5c1917548'
CONFIG_SHA = '4d73f1ad3216bc9338e9113cd23d2b1ea68403cee3ab0b3c9fe718aa3f4e37f0'
STOP, STACK, TLS, DATA, HEAP = 0x4000000, 0x2000000, 0x3000000, 0x5000000, 0x6000000
P = Path('/mnt/e/edk2-samurai-out')


def sleb(raw, cursor):
    value, shift = 0, 0
    while True:
        byte = raw[cursor]; cursor += 1
        value |= (byte & 127) << shift; shift += 7
        if not byte & 128:
            return value - (1 << shift) if byte & 64 else value, cursor


class Machine:
    def __init__(self, file_available=True):
        raw = (P/'kernel453/af-config-source/libhwconfigurationutil-r6.so').read_bytes()
        self.config = (P/'kernel453/af-config-source/CameraHWConfiguration-r6.config').read_bytes()
        self.file_available = file_available
        assert hashlib.sha256(raw).hexdigest() == LIB_SHA and hashlib.sha256(self.config).hexdigest() == CONFIG_SHA
        self.raw = raw
        phoff, shoff = struct.unpack_from('<QQ', raw, 32)
        phsize, phnum, shsize, shnum, shstr = struct.unpack_from('<HHHHH', raw, 54)
        segments = [struct.unpack_from('<II6Q', raw, phoff+i*phsize) for i in range(phnum)]
        sections = [struct.unpack_from('<II4QII2Q', raw, shoff+i*shsize) for i in range(shnum)]
        names = raw[sections[shstr][4]:sections[shstr][4]+sections[shstr][5]]
        self.sections = {names[s[0]:].split(b'\0')[0].decode():s for s in sections}
        def payload(name):
            s = self.sections[name]; return raw[s[4]:s[4]+s[5]]
        strings = payload('.dynstr'); symbols = payload('.dynsym')
        self.symbols = [struct.unpack_from('<IBBHQQ', symbols, i) for i in range(0, len(symbols), 24)]
        self.symbol_names = [strings[s[0]:].split(b'\0')[0].decode() for s in self.symbols]
        self.addresses = {name:s[4] for name,s in zip(self.symbol_names,self.symbols) if s[3]}
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        maximum = (max(s[3]+s[6] for s in segments if s[0] == 1)+4095)&~4095
        self.u.mem_map(0, maximum)
        for kind, flags, offset, va, pa, size, memsize, align in segments:
            if kind == 1:
                self.u.mem_write(va, raw[offset:offset+size])
        for address,size in [(STACK,0x100000),(TLS,4096),(STOP,4096),(DATA,0x100000),(HEAP,0x1000000)]:
            self.u.mem_map(address,size)
        self.u.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)
        self.u.reg_write(UC_ARM64_REG_TPIDR_EL0, TLS)
        self.cursor = HEAP
        self.providers, self.trace, self.loads, self.streams = {}, [], [], {}
        self.file_streams = set()
        self.last_assigned = b''
        self.external = {}
        for i,name in enumerate(name for name,s in zip(self.symbol_names,self.symbols) if not s[3] and name):
            self.external[name] = DATA+0x80000+i*16
        def relocate(offset, info, addend):
            index, kind = info >> 32, info & 0xffffffff
            assert kind in (257,1025,1026,1027), (hex(offset),kind)
            name = self.symbol_names[index]
            value = addend if kind == 1027 else (self.symbols[index][4] if self.symbols[index][3] else self.external[name])+addend
            self.put64(offset,value)
        data = payload('.rela.dyn'); assert data[:4] == b'APS2'
        cursor=4; count,cursor=sleb(data,cursor); offset,cursor=sleb(data,cursor); addend=0; done=0
        while done < count:
            group,cursor=sleb(data,cursor); flags,cursor=sleb(data,cursor)
            if flags & 2: delta,cursor=sleb(data,cursor)
            if flags & 1: info,cursor=sleb(data,cursor)
            if flags & 8 and flags & 4: adelta,cursor=sleb(data,cursor)
            for unused in range(group):
                if not flags & 2: delta,cursor=sleb(data,cursor)
                offset += delta
                if not flags & 1: info,cursor=sleb(data,cursor)
                if flags & 8:
                    if not flags & 4: adelta,cursor=sleb(data,cursor)
                    addend += adelta
                else: addend=0
                relocate(offset,info,addend);done+=1
        assert done == count and cursor == len(data)
        # Base zero leaves RELR values unchanged; still validate every encoded slot.
        at = 0
        for value, in struct.iter_unpack('<Q',payload('.relr.dyn')):
            if not value & 1:
                at=value;self.read64(at);at+=8
            else:
                for bit in range(63):
                    if value & (2 << bit): self.read64(at+bit*8)
                at+=63*8
        for offset,info,addend in struct.iter_unpack('<QQq',payload('.rela.plt')):
            relocate(offset,info,addend)
        self.reverse_external = {value:name for name,value in self.external.items()}
        self.char_facet = self.alloc(128); table=self.alloc(128)
        self.put64(self.char_facet,table);self.put64(table+56,DATA+0x7f000)
        self.u.hook_add(UC_HOOK_CODE,self.step)
        self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)

    def invalid(self,u,access,address,size,value,unused):
        raise RuntimeError(f'invalid {address:x} pc={u.reg_read(UC_ARM64_REG_PC):x}')

    def read32(self,p): return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def read64(self,p): return struct.unpack('<Q',self.u.mem_read(p,8))[0]
    def put64(self,p,v): self.u.mem_write(p,struct.pack('<Q',v & ((1<<64)-1)))
    def alloc(self,n):
        assert 0 < n < 0x100000
        p=self.cursor;self.cursor+=(n+31)&~31;assert self.cursor < HEAP+0x1000000
        self.u.mem_write(p,bytes(n));return p
    def string(self,p):
        assert p
        value=bytes(self.u.mem_read(p,8192));assert b'\0' in value
        return value.split(b'\0')[0]
    def cstring(self,value):
        p=self.alloc(len(value)+1);self.u.mem_write(p,value+b'\0');return p
    def cpp(self,p):
        head=self.u.mem_read(p,1)[0]
        return bytes(self.u.mem_read(self.read64(p+16),self.read64(p+8))) if head & 1 else bytes(self.u.mem_read(p+1,head>>1))
    def set_cpp(self,p,value):
        if len(value) <= 22:
            self.u.mem_write(p,bytes([len(value)*2])+value+b'\0'+bytes(22-len(value)))
        else:
            data=self.cstring(value);self.u.mem_write(p,struct.pack('<QQQ',(len(value)+16)|1,len(value),data))
    def ret(self,value=0):
        self.u.reg_write(UC_ARM64_REG_X0,value & ((1<<64)-1))
        self.u.reg_write(UC_ARM64_REG_PC,self.u.reg_read(UC_ARM64_REG_LR))
    def ios(self,stream):
        delta=self.read64(self.read64(stream)-24)
        return (stream+delta)&((1<<64)-1)
    def getline(self,stream,out,delimiter):
        if stream not in self.streams:
            self.streams[stream]=[self.last_assigned,0]
        raw,pos=self.streams[stream]
        end=raw.find(bytes([delimiter & 255]),pos)
        if end < 0: end=len(raw)
        self.set_cpp(out,raw[pos:end]);self.streams[stream][1]=end+1
        if pos >= len(raw): self.u.mem_write(self.ios(stream)+32,struct.pack('<I',6))
        self.ret(stream)
    def step(self,u,pc,size,unused):
        self.trace.append(pc)
        a,b,c,d,e=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(5)]
        if pc == 0xd828:
            self.providers['C++ getline byte-stream provider']=self.providers.get('C++ getline byte-stream provider',0)+1
            self.getline(a,b,c);return
        if pc == 0xcd70:
            self.providers['C++ filebuf::close provider']=self.providers.get('C++ filebuf::close provider',0)+1
            self.ret(a);return
        if pc == DATA+0x7f000: self.ret(b);return
        if pc not in self.reverse_external:
            return
        name=self.reverse_external[pc];self.providers[name]=self.providers.get(name,0)+1;result=0
        if name in ('malloc','_Znwm','_Znam'): result=self.alloc(a)
        elif name in ('free','_ZdlPv','_ZdaPv','__cxa_finalize','__cxa_atexit','__cxa_guard_release'): pass
        elif name == '__cxa_guard_acquire': result=1;self.u.mem_write(a,b'\1')
        elif name in ('strlen','__strlen_chk'): result=len(self.string(a))
        elif name in ('memcpy','memmove'): self.u.mem_write(a,bytes(self.u.mem_read(b,c)));result=a
        elif name in ('strcmp','strncmp'):
            left,right=self.string(a),self.string(b)
            if name == 'strncmp': left,right=left[:c],right[:c]
            result=(left>right)-(left<right)
        elif name == '__strrchr_chk':
            at=self.string(a).rfind(bytes([b&255]));result=a+at if at>=0 else 0
        elif name == 'strndup': result=self.cstring(self.string(a)[:b])
        elif name == 'strtol':
            raw=self.string(a); libc=ctypes.CDLL(None);libc.strtol.restype=ctypes.c_long
            libc.strtol.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_int]
            buffer=ctypes.create_string_buffer(raw);end=ctypes.c_void_p()
            result=libc.strtol(ctypes.addressof(buffer),ctypes.byref(end),c)
            if b: self.put64(b,a+end.value-ctypes.addressof(buffer))
        elif name == '__dynamic_cast':
            result=a if a and self.read64(self.read64(a)-8)==c else 0
        elif name == 'fopen':
            path,mode=self.string(a),self.string(b);self.loads.append(dict(path=path.decode(),mode=mode.decode()))
            assert path==b'/odm/etc/camera/CameraHWConfiguration.config' and mode in (b'r',b'rb'), (path,mode)
            if self.file_available:
                stream=u.reg_read(UC_ARM64_REG_SP)+0x50;self.streams[stream]=[self.config,0];self.file_streams.add(stream);result=DATA+0x60000
        elif name == 'fclose': pass
        elif name == '_ZNSt3__18ios_base4initEPv': self.u.mem_write(a+32,bytes(4))
        elif name == '_ZNSt3__18ios_base5clearEj': self.u.mem_write(a+32,struct.pack('<I',b))
        elif name == '_ZNKSt3__18ios_base6getlocEv': self.put64(u.reg_read(UC_ARM64_REG_X8),0)
        elif 'use_facet' in name: result=self.char_facet
        elif 'has_facet' in name: result=0
        elif 'locale' in name or 'basic_streambuf' in name or 'basic_istream' in name or 'basic_ios' in name: pass
        elif 'basic_string' in name:
            if '4findEcm' in name or '5rfindEcm' in name:
                raw=self.cpp(a);char=bytes([b&255]);index=raw.rfind(char,0,min(c+1,len(raw))) if 'rfind' in name else raw.find(char,c)
                result=index if index>=0 else (1<<64)-1
            elif 'C1ERKS5_mmRKS4_' in name or 'C2ERKS5_mmRKS4_' in name:
                self.set_cpp(a,self.cpp(b)[c:c+d]);result=a
            elif 'aSERKS5_' in name:
                value=self.cpp(b);self.set_cpp(a,value);self.last_assigned=value
                self.streams={key:item for key,item in self.streams.items() if key in self.file_streams}
                result=a
            elif '6resizeEmc' in name:
                value=self.cpp(a);self.set_cpp(a,value[:b]+bytes([c&255])*max(0,b-len(value)));result=a
            elif '6appendEPKcm' in name: self.set_cpp(a,self.cpp(a)+bytes(self.u.mem_read(b,c)));result=a
            elif '9push_backEc' in name: self.set_cpp(a,self.cpp(a)+bytes([b&255]));result=a
            else: raise RuntimeError('unimplemented C++ string provider '+name)
        elif name == '__vsprintf_chk':
            fmt=self.string(d);assert fmt==b'%s[%s]',fmt
            stack,grtop,vrtop,groff,vroff=struct.unpack('<QQQii',u.mem_read(e,32));values=[]
            for unused in range(2):
                if groff<0: pointer=self.read64(grtop+groff);groff+=8
                else: pointer=self.read64(stack);stack+=8
                values.append(self.string(pointer))
            value=values[0]+b'['+values[1]+b']';assert len(value)<c
            u.mem_write(a,value+b'\0');result=len(value)
        elif name in ('__android_log_write','vsnprintf'): pass
        else: raise RuntimeError('unexpected provider '+name+' lr='+hex(u.reg_read(UC_ARM64_REG_LR)))
        self.ret(result)

    def call(self,entry,*arguments,end=STOP):
        for i,value in enumerate(arguments): self.u.reg_write(UC_ARM64_REG_X0+i,value)
        self.u.reg_write(UC_ARM64_REG_LR,STOP);self.u.reg_write(UC_ARM64_REG_SP,STACK+0xf0000)
        self.u.emu_start(entry,end,timeout=15000000,count=3000000)
        assert self.u.reg_read(UC_ARM64_REG_PC)==end,hex(self.u.reg_read(UC_ARM64_REG_PC))
        return self.u.reg_read(UC_ARM64_REG_X0)

    def load(self):
        obj=self.alloc(16)
        if self.file_available:
            self.call(0x15e68,obj,end=0x15eb0)
        else:
            self.call(0x15e68,obj)
        self.u.mem_write(0x1ab90,b'\1');self.put64(0x1ab98,self.read64(obj))
        return self.read64(obj)

    def get_keys(self, group):
        return self.call(0x184b8,self.cstring(group))

    def get_count(self, group, key):
        return self.call(0x18570,self.cstring(group),self.cstring(key))

    def get_list(self, group, key, locale, count):
        assert 0 < count <= 64
        out=self.alloc((count+2)*4);self.u.mem_write(out,b'\xcc'*((count+2)*4))
        status=self.call(0x16d50,self.cstring(group),self.cstring(key),self.cstring(locale),out,count)
        assert bytes(self.u.mem_read(out+count*4,8)) == b'\xcc'*8
        return status,list(struct.unpack('<'+'i'*count,self.u.mem_read(out,count*4)))


def main():
    out=P/'kernel460';out.mkdir(mode=0o700,exist_ok=True)
    m=Machine();keyfile=m.load();assert keyfile
    group=b'OemCamActuatorSettingMap';base=b'Mode'
    keys=m.get_keys(group);count=m.get_count(group,b'Mode[0]')
    assert keys==4 and count==4,(keys,count)
    rows=[]
    for index in range(4):
        result,values=m.get_list(group,base,str(index).encode(),4)
        assert result==0,result
        rows.append(dict(locale=str(index),values=values,result=result))
    text=m.config.decode();expected={}
    for line in text.splitlines():
        if line.strip().startswith('Mode['):
            key,value=line.split('=',1)
            expected[key.strip()]=[int(token) for token in re.split(r'[;\s]+',value.split('#')[0].strip()) if token]
    assert all(row['values']==expected['Mode['+row['locale']+']'] for row in rows)
    assert m.get_list(group,base,b'4',4)[0] != 0
    assert m.get_count(group,b'absent') == 0
    truncated,short=m.get_list(group,base,b'1',2)
    assert truncated == 0 and short == expected['Mode[1]'][:2]
    failed=Machine(file_available=False);assert failed.load()==0
    assert len(failed.loads)==1 and failed.get_keys(group)==0
    proof=dict(library_sha256=LIB_SHA,configuration_sha256=CONFIG_SHA,
               keyfile=keyfile,loads=m.loads,instructions=len(m.trace),providers=m.providers,
               key_count=keys,values_count=count,rows=rows,
               independent_text_crosscheck_equal=True,
               failed_file_load=dict(open_attempts=failed.loads,key_count=0,no_fallback=True,providers=failed.providers),
               missing_locale_failed=True,missing_key_count_zero=True,truncated_output_native_min_count=True)
    (out/'native-config-trial-private.json').write_text(json.dumps(proof,indent=2)+'\n')
    (out/'native-library-trace-private.json').write_text(json.dumps(dict(pcs=m.trace,failed_load_pcs=failed.trace,
        providers=m.providers,failed_providers=failed.providers))+'\n')
    print(json.dumps(dict(parsed=True,instructions=len(m.trace),keys=keys,values_per_row=count,locale_getters_success=4)))


if __name__ == '__main__': main()
