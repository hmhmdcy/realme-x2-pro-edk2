"""Build the recovered generic manager without changing its selection code."""
from pathlib import Path
import json,shutil,subprocess
import host

HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'manager-build';work.mkdir(exist_ok=True)
mapping={'TYPES':'parametertypes.h','UTILS':'parameterutils.h','MODULE':'parametermodule.h','MANAGER':'parametersetmanager.h',
 'ENTRY':'parameterfilesymboltableentry.h','TABLE':'parameterfilesymboltable.h','TTYPES':'parametertuningtypes.h'}
for row in json.loads((P/'manager-template-private.json').read_text())['templates']:
 if row['file'].endswith('.partial'):continue
 text=(P/'sources'/row['file']).read_text()
 for key,value in mapping.items():text=text.replace('$'+key+'$',value)
 (work/row['file']).write_text(text)
(work/'Windows.h').write_text('''#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <strings.h>
#include <cstddef>
using UINT8=uint8_t;using UINT16=uint16_t;using UINT32=uint32_t;using UINT64=uint64_t;
using INT8=int8_t;using INT16=int16_t;using INT32=int32_t;using INT64=int64_t;
using BYTE=uint8_t;using CHAR=char;using VOID=void;using BOOL=bool;using SIZE_T=size_t;
constexpr BOOL TRUE=true,FALSE=false;
#define sprintf_s snprintf
#define _strnicmp strncasecmp
inline int strcpy_s(char *d,size_t n,const char*s){if(strlen(s)>=n)return 1;strcpy(d,s);return 0;}
inline int strcat_s(char *d,size_t n,const char*s){if(strlen(d)+strlen(s)>=n)return 1;strcat(d,s);return 0;}
inline int memcpy_s(void*d,size_t n,const void*s,size_t count){if(count>n)return 1;memcpy(d,s,count);return 0;}
''')
(work/'parametertuningtypes.h').write_text('''#pragma once
#include "parametertypes.h"
#include "parametermodule.h"
enum class ModeType:UINT32 {Default=0,Sensor,Usecase,Feature1,Feature2,Scene,Effect};
struct TuningMode {ModeType mode;union {UINT16 value;UINT32 storage;} subMode;};
''')
shutil.copyfile(HERE/'selection-runner.cpp',work/'selection-runner.cpp')
sources=sorted(work.glob('*.cpp'))
q=subprocess.run(['g++','-std=c++17','-O2','-fno-strict-aliasing','-I'+str(work),*[str(f) for f in sources],'-o',str(P/'stock-selection-manager')],capture_output=True)
(P/'selector-build.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
print('Built original mode-tree reader and GetModule with generic name/UID payload stubs.')
