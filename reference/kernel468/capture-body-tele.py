"""Reuse the tested tele consumer, requiring the new sensor format readback."""
from pathlib import Path
import hashlib
source_path=Path(__file__).resolve().parent/'capture-body-base.py'
raw=source_path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c990fb7715375f8c088608317a82ae6b4550cb300e1505800d4e499f8054bc08'
source=raw.decode()
for old,new in [("sensor[0][:2]==('2104','1560')","sensor[0][:2]==('4208','2368')"),
                ('actual_sensor=[2104,1560]','actual_sensor=[4208,2368]')]:
    assert source.count(old)==1;source=source.replace(old,new)
exec(compile(source,'retained467-consumer-with-mode2-readback','exec'))
