"""Read only the candidate sources after the shared storage guard."""
import storage

storage.mount.mounted_build()
root=storage.candidate()/'src/libcamera-v0.7.2'
for name,terms in {
 'src/ipa/camss-vfe/camss.cpp':['IPE_RECEIPT','completeIpe','observeIpe','pending','discard'],
 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp':['resolveIpe','completeIpe','discardIpe','pendingIpe','drop','FRAME_IPA_PREPARE'],
}.items():
 lines=(root/name).read_text().splitlines();indices=set()
 for i,line in enumerate(lines):
  if any(term in line for term in terms):indices.update(range(max(0,i-5),min(len(lines),i+10)))
 print(name)
 print('\n'.join(str(i+1)+':'+lines[i] for i in sorted(indices)))
