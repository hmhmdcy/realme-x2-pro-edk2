"""Rejoin only observed SAMPLE splits around complete libcamera logger lines."""
import re
def join_split_sample_record(text):
 logger=re.compile(r'\[\d+:\d+:\d+\.\d+\] \[\d+\] +(INFO|DEBUG|WARN|ERROR) \w+ \S+:\d+ ')
 out=[];pending=None;splits=0
 for line in text.splitlines():
  match=logger.search(line)
  if pending is None:
   if line.startswith('SAMPLE sequence=') and match:
    pending=line[:match.start()];out.append(line[match.start():]);splits+=1
   else:out.append(line)
  elif match:
   pending+=line[:match.start()];out.append(line[match.start():])
  else:
   pending+=line
   assert re.fullmatch(r'SAMPLE sequence=\d+ width=\d+ height=\d+ stride=\d+ bytes=\d+',pending)
   out.append(pending);pending=None
 assert pending is None
 joined='\n'.join(out)+'\n'
 for marker in ['SAMPLE sequence=','ADAPT_FRAME ','IPE_OBSERVE ','IPE_TONE_QUEUE ','IPE_RECEIPT ']:assert joined.count(marker)==text.count(marker)
 return joined,splits
