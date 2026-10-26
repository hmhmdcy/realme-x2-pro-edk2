"""Extract published patch messages; keep provenance for each input."""
from pathlib import Path
import email,email.policy,mailbox,json,re
import host
HERE=Path(__file__).resolve().parent
out=HERE/'upstream';out.mkdir(exist_ok=True)
manifest=[]
for message in mailbox.mbox(host.PRIVATE/'upstream-streams-thread.mbox',factory=lambda f:email.message_from_binary_file(f,policy=email.policy.default)):
 subject=str(message['Subject'])
 if subject.startswith('Re:'):continue
 body=message.get_body(preferencelist=('plain',))
 text=body.get_content() if body else message.get_payload(decode=True).decode(errors='replace')
 if 'diff --git' not in text:continue
 m=re.search(r'\[PATCH (\d)/8\]',subject)
 if not m:continue
 name=m[1]+'-streams.patch'
 (out/name).write_text('From: '+str(message['From'])+'\nSubject: '+subject+'\n\n'+text)
 manifest.append({'file':name,'subject':subject,'message_id':str(message['Message-ID']),'url':'https://lore.kernel.org/all/'+str(message['Message-ID']).strip('<>')+'/'})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
