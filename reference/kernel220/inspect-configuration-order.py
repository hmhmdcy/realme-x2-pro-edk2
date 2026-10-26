from pathlib import Path
root=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera218')
for name,regions in {'src/libcamera/pipeline/simple/simple.cpp':[(490,640),(1560,1610)],'src/ipa/simple/soft_simple.cpp':[(95,112),(196,219)],'src/libcamera/software_isp/software_isp.cpp':[(140,205)]}.items():
 lines=(root/name).read_text().splitlines();print('\nFILE',name)
 for begin,end in regions:
  for i in range(begin-1,end):print(f'{i+1}: {lines[i]}')
