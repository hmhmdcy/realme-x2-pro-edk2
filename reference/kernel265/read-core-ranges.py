from pathlib import Path
K=Path('/home/cy122/x2pro-linux/libcamera214-root/work/pipewire263-broadcast/pipewire-1.6.9')
for name,ranges in {'src/pipewire/impl-port.c':[(215,300),(320,400),(470,568)],'src/pipewire/stream.c':[(840,900),(1080,1165),(2538,2648)],'src/gst/gstpipewiresrc.c':[(680,785)]}.items():
 lines=(K/name).read_text().splitlines();print('\nFILE '+name)
 for start,end in ranges:
  for i in range(start-1,min(len(lines),end)):print(str(i+1)+': '+lines[i])
