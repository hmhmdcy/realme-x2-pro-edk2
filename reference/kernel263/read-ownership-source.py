from pathlib import Path
r=Path('/home/cy122/x2pro-linux/libcamera214-root/work/pipewire262/pipewire-1.6.9')
for name,ranges in [('src/pipewire/impl-port.c',[(270,370)]),('spa/plugins/libcamera/libcamera-source.cpp',[(1020,1175),(1380,1470),(1980,2075)]),('src/pipewire/stream.c',[(1050,1190)])]:
 print(name)
 s=(r/name).read_text().splitlines()
 print('\n'.join(str(i+1)+':'+s[i] for a,b in ranges for i in range(a,min(b,len(s)))))
for name in ['src/gst/gstpipewirepool.c','src/gst/gstpipewiresrc.c']:
 s=(r/name).read_text().splitlines();print(name)
 for i,line in enumerate(s):
  if 'busy' in line.lower():print('\n'.join(str(j+1)+':'+s[j] for j in range(max(0,i-5),min(i+6,len(s)))))
