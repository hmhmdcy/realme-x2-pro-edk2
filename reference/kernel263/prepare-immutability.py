"""Preserve the old harness; add real shared-buffer content immutability checks."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).parent
native=(R.parent/'kernel262/native-pipewire-probe.py').read_text()
native=re.sub(r"which,kind='front','rgb';delay=int\(sys.argv\[1\]\);assert delay in \[[^\n]+\]", "which,kind='front','rgb';delay=int(sys.argv[1]);assert delay in [6000000,3000000,6000007]",native,count=1)
native=native.replace('k262','k263').replace('stage=262','stage=263')
(R/'native-probe.py').write_text(native)
probe=(R.parent/'kernel262/pipewire-probe.py').read_text().replace('k262','k263')
probe=probe.replace("source=devices[0].create_element('camera')", "source=devices[0].create_element('camera') if int(sys.argv[1])!=6000007 else Gst.ElementFactory.make('libcamerasrc')\nif int(sys.argv[1])==6000007:source.set_property('camera-name','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10')")
probe=probe.replace("shared_bufferpool=source.get_property('use-bufferpool')", "shared_bufferpool=source.get_property('use-bufferpool') if source.find_property('use-bufferpool') else None,source_factory=source.get_factory().get_name()")
probe=probe.replace('[1000000,3000000,3000001,4000000,6000000]','[1000000,3000000,3000001,4000000,6000000,6000007]')
probe=probe.replace('held=[]',"held=[]\ndata.update(held_checked=0,held_content_changed=0,held_bytes_sampled=65536)")
probe=probe.replace("held.append((time.monotonic(),buffer.copy()))", "held.append((time.monotonic(),buffer.copy(),hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()))")
probe=probe.replace("  while held and time.monotonic()-held[0][0]>.12:held.pop(0)","  while held and time.monotonic()-held[0][0]>.12:\n   timestamp,buffer,digest=held.pop(0)\n   data['held_checked']+=1\n   data['held_content_changed']+=hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()!=digest\n   del buffer")
compile(native,'native-probe.py','exec');compile(probe,'immutability-probe.py','exec')
(R/'immutability-probe.py').write_text(probe)
print(json.dumps(dict(stage=263,shared_probe=6000000,copy_control=3000000,sample_bytes=65536,native_sha256=hashlib.sha256(native.encode()).hexdigest())))
