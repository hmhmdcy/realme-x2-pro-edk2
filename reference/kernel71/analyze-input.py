from pathlib import Path
import collections, hashlib, json, struct
r=Path(__file__).resolve().parent
data=(r/'input-events.bin').read_bytes()
meta=(r/'touch-eventmeta.validated.txt').read_text()
digest=hashlib.sha256(data).hexdigest()
assert digest in meta
assert f'{len(data)} /tmp/K71T/events' in meta
assert not any('timeout 120 cat /dev/input/event2' in line for line in meta.splitlines()),'Capture is still running'
assert len(data)%24==0 and data
events=list(struct.iter_unpack('<qqHHi',data))
counts=collections.Counter((typ,code) for sec,usec,typ,code,value in events)
slot=0;slots={};contacts={};closed=[];frames=0;max_active=0;timestamps=[]
positions=[];double_frames=0;btn_down=btn_up=0
for sec,usec,typ,code,value in events:
 assert 0<=usec<1000000
 timestamps.append(sec+usec/1000000)
 if typ==3:
  if code==47: slot=value
  elif code==57:
   if value==-1:
    if slot in slots: closed.append(slots.pop(slot))
   else:
    assert slot not in slots,('New tracking ID before release',slot,value)
    key=(slot,value);slots[slot]=key;contacts[key]=dict(start=sec+usec/1000000,positions=[])
  elif code in (53,54):
   if slot in slots:
    contact=contacts[slots[slot]]
    contact['x' if code==53 else 'y']=value
 elif typ==1 and code==330:
  if value: btn_down+=1
  else: btn_up+=1
 elif typ==0 and code==0:
  frames+=1;max_active=max(max_active,len(slots))
  if len(slots)>=2: double_frames+=1
  for key in slots.values():
   contact=contacts[key]
   if 'x' in contact and 'y' in contact:
    point=(contact['x'],contact['y']);contact['positions'].append(point);positions.append(point)
assert timestamps==sorted(timestamps)
moving=sum(len(set(c['positions']))>1 for c in contacts.values())
report=dict(input_event_bytes=len(data),record_size=24,event_records=len(events),
 plain_sha256=digest,device_plain_sha256_matches=True,device_length_matches=True,
 capture_process_ended=True,syn_report_frames=frames,contacts_started=len(contacts),
 contacts_released=len(closed),active_contacts_at_end=len(slots),moving_contacts=moving,
 max_simultaneous_contacts=max_active,two_or_more_contact_frames=double_frames,
 btn_touch_down=btn_down,btn_touch_up=btn_up,event_seconds_span=timestamps[-1]-timestamps[0],
 x_range=[min(p[0] for p in positions),max(p[0] for p in positions)] if positions else None,
 y_range=[min(p[1] for p in positions),max(p[1] for p in positions)] if positions else None,
 event_types_codes={f'{typ}:{code}':count for (typ,code),count in sorted(counts.items())},
 user_confirmed_taps_swipes_two_fingers=True,
 limitation='Basic recorded input test only; no suspend/resume, orientation/edge calibration or long-run acceptance.')
report['coordinates_inside_configured_panel']=bool(positions) and all(0<=x<1080 and 0<=y<2400 for x,y in positions)
report['basic_touch_pass']=len(contacts)>0 and len(closed)==len(contacts) and not slots and moving>0 and max_active>=2 and report['coordinates_inside_configured_panel'] and btn_down>0 and btn_up>0
(r/'input-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(r/'input-events.bin').write_bytes(data)
print(json.dumps(report,indent=2))
