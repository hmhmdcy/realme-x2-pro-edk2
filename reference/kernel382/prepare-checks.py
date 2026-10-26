from pathlib import Path
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel381';P=host.PRIVATE
(P/'camss-icp-a5-boot.h.proposed').write_bytes((P.parent/'kernel381/camss-icp-a5-boot.h.proposed').read_bytes())
(HERE/'session-regression.c').write_bytes((OLD/'session-regression.c').read_bytes())
s=(OLD/'check-transfer.py').read_text().replace('stage=381','stage=382')
s=s.replace("(HERE.parent/'kernel380/camss-icp-a5-ipe.c')", "(P/'camss-icp-a5-ipe.c.proposed')")
s=s.replace(',iq[2584]={0}','').replace('.iq=iq,','').replace('.iq_bytes=sizeof(iq),','')
s=s.replace('if(scenario==68)iq[0]=1','if(scenario==68)job.input=NULL').replace('scenario==68?-EOPNOTSUPP:','scenario==68?-EINVAL:')
s=s.replace('nonzero_unvalidated_iq_rejected=True','external_iq_input_removed_and_kernel_defaults_checked=True')
anchor='   memset(active->image_output.cpu,0x7c,640*480*3/2);';assert s.count(anchor)==1
s=s.replace(anchor,'''   u32 iq_iova=get_unaligned_le32(active->request.cpu+4);assert(iq_iova>=REQUEST_IOVA && iq_iova+2584<=REQUEST_IOVA+active->request.bytes);
   u8 *iq=active->request.cpu+iq_iova-REQUEST_IOVA;for(unsigned i=0;i<2584;i++)assert(iq[i]==(i==52||i==68||i==244||i==260));
'''+anchor)
(HERE/'check-transfer.py').write_text(s)
# Owner protocol is unchanged; test_frame itself is checked by the kernel build.
for name in ['check-owner.py','owner-regression.c','check-dispatch.py','check-worker.py']:
 s=(OLD/name).read_text().replace('stage=381','stage=382');(HERE/name).write_text(s)
print('Prepared actual transfer function regression with byte-exact generated IQ assertions.')
