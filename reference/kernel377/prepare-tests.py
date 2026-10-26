from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel376'
s=(OLD/'session-regression.c').read_text().replace('unsigned bytes,mapped;','unsigned bytes,mapped,iova;')
s=s.replace('#define U64_MAX UINT64_MAX','#define U64_MAX UINT64_MAX\n#define U32_MAX UINT32_MAX')
s=s.replace('static u32 get_unaligned_le32', 'static void dma_wmb(void){}\nstatic u32 get_unaligned_le32')
s=s.replace('if(mode==4)return -ENOSPC;', 'if(mode==4 || (mode==31 && get_unaligned_le32((u8 *)p+8)==IPE_MEM_MAP))return -ENOSPC;')
# Ring fixture is declared before production constants; use the literal wire
# opcode only in that provider, not in the production methods.
s=s.replace('==IPE_MEM_MAP))return -ENOSPC;','==14))return -ENOSPC;')
anchor=' if(command==IPE_CREATE){';assert s.count(anchor)==1
block=''' if(command==IPE_ASYNC_DIRECT && get_unaligned_le32(last_packet+8)!=IPE_DESTROY){
  u32 opcode=get_unaligned_le32(last_packet+8);assert(last_bytes==56 && (opcode==IPE_MEM_MAP || opcode==IPE_MEM_UNMAP));
  assert(get_unaligned_le32(last_packet+44)==1 && get_unaligned_le32(last_packet+48)==CONFIG_IOVA && get_unaligned_le32(last_packet+52)==4096);
  if(mode==41 && opcode==IPE_MEM_UNMAP)return 0;
  bytes=44;put_unaligned_le32(IPE_ASYNC_DIRECT_ACK,reply+4);put_unaligned_le32(opcode,reply+8);memcpy(reply+12,last_packet+12,16);
  if((mode==32 && opcode==IPE_MEM_MAP)||(mode==36 && opcode==IPE_MEM_UNMAP))put_unaligned_le32(7,reply+28);
 }else if(command==IPE_ASYNC_INDIRECT){
  assert(last_bytes==40 && get_unaligned_le32(last_packet+8)==IPE_CONFIG_IO && get_unaligned_le32(last_packet+36)==CONFIG_IOVA);
  assert(active->config_fw_mapped && active->config_owner && get_unaligned_le32(active->config.cpu)==20 && get_unaligned_le32(active->config.cpu+8*84)==20);
  if(mode==35)return 0;
  bytes=mode==40?48:56;put_unaligned_le32(IPE_ASYNC_INDIRECT_ACK,reply+4);put_unaligned_le32(IPE_CONFIG_IO,reply+8);memcpy(reply+12,last_packet+12,16);
  put_unaligned_le32(mode==33?7:0,reply+28);put_unaligned_le32(mode==34?0xa0001:0,reply+32);put_unaligned_le32(65536,reply+36);
 }else'''
s=s.replace(anchor,block+' '+anchor[1:])
anchor=' mode=scenario;\n';assert s.count(anchor)==1
s=s.replace(anchor,''' if(scenario==43){
  u32 f[11];u8 out[1216];while(fread(f,sizeof(u32),11,stdin)==11){
   struct camss_a5_ipe_io io={.input={f[0],f[1],f[2],f[3],f[4]},.output={f[5],f[6],f[7],f[8],f[9]},.output_port=f[10]};
   assert(!encode_ipe_io(out,sizeof(out),&io));assert(fwrite(out,1,sizeof(out),stdout)==sizeof(out));
  }return 0;
 }
 if(scenario==44){
  for(unsigned bad=0;bad<13;bad++){
   u8 out[1216],saved[1216];memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
   struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
   if(bad==3)io.input.width=639;if(bad==4)io.output.height=479;if(bad==5)io.input.stride=638;
   if(bad==6)io.output.slice_height=478;if(bad==7)io.input.stride=641;if(bad==8)io.input.slice_height=481;
   if(bad==9){io.input.stride=U32_MAX-1;io.input.slice_height=U32_MAX-1;}
   if(bad==10)io.output_port=0;if(bad==11)io.input.width=0;if(bad==12)io.output.height=0;
   assert(encode_ipe_io(bad==0?NULL:out,bad==1?1215:1216,bad==2?NULL:&io)==-EINVAL && !memcmp(out,saved,sizeof(out)));
  }return 0;
 }
 if(scenario>=30){
  u8 config[4096];a.config.cpu=config;a.config.bytes=a.config.mapped=4096;a.config.iova=CONFIG_IOVA;
  struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
  assert(!camss_a5_ipe_create(&a,&one,2));mode=scenario;
  if(scenario==37)io.input.width=639;
  if(scenario==38)a.config.mapped=0;
  ret=camss_a5_ipe_configure_nv12(&a,scenario==39?&foreign:&one,&io);
  if(scenario==30){assert(!ret && a.io_configs==1 && a.config_maps==1 && a.config_unmaps==1 && !a.config_fw_mapped && !a.config_owner && one.configured && one.scratch_bytes==65536);}
  else if(scenario==31 || scenario==37 || scenario==38 || scenario==39){assert(ret==(scenario==31?-ENOSPC:scenario==39?-ENODEV:-EINVAL) && !a.config_fw_mapped && !a.session_uncertain && !a.io_configs);}
  else if(scenario==33 || scenario==34){assert(ret==-EREMOTEIO && !a.config_fw_mapped && !a.session_uncertain && !one.configured && a.config_maps==1 && a.config_unmaps==1);}
  else if(scenario==36){assert(ret==-EREMOTEIO && a.config_fw_mapped && a.config_owner==&one && !a.session_uncertain && !one.configured && a.io_configs==1);}
  else if(scenario==32 || scenario==35 || scenario==40 || scenario==41){
   assert(ret==(scenario==32?-EREMOTEIO:scenario==40?-EPROTO:-ETIMEDOUT) && a.session_uncertain && a.config_fw_mapped && a.config_owner==&one);
   mode=0;reset_error=1;assert(model_stop(&a)==-EBUSY && a.config_fw_mapped && a.config_owner==&one && a.cpu_enabled && a.power_held && backing && one.a5==&a);
   reset_error=0;assert(!model_stop(&a) && !a.config_fw_mapped && !a.config_owner && !one.a5 && !a.cpu_enabled && !a.power_held);return 0;
  }else assert(0);
  mode=0;assert(!camss_a5_ipe_destroy(&a,&one) && !a.config_fw_mapped && !a.config_owner);
  assert(!model_stop(&a) && !resets && !a.cpu_enabled && !a.power_held && !a.session_count);return 0;
 }
'''+anchor)
(HERE/'session-regression.c').write_text(s)
s=(OLD/'check-session.py').read_text().replace('stage=376','stage=377').replace('range(27)','list(range(27))+list(range(30,42))')
s=s.replace('list(range(30,42)):', 'list(range(30,42))+[44]:')
s=s.replace('two_simultaneous_independent_sessions=True,','two_simultaneous_independent_sessions=True,io_map_config_unmap_and_error_ownership_checked=True,')
(HERE/'check-session.py').write_text(s)
s=(OLD/'owner-regression.c').read_text().replace('static unsigned creates,destroys;','static unsigned creates,destroys;\nstruct camss_a5_ipe_io {int unused;};static const struct camss_a5_ipe_io test_io={0};static unsigned scratch_observed[2];')
s=s.replace('struct camss_a5_session {struct camss_a5 *a5;unsigned type;};','struct camss_a5_session {struct camss_a5 *a5;unsigned type,scratch_bytes;};')
anchor='static void *devm_kzalloc(';idx=s.index(anchor)
s=s[:idx]+'''static int camss_a5_ipe_configure_nv12(struct camss_a5 *a,struct camss_a5_session *session,const struct camss_a5_ipe_io *io){
 assert(session->a5==a && io==&test_io && test_lock);session->scratch_bytes=65536;
 return ((scenario==34 && session->type==2)||(scenario==35 && session->type==3))?-EREMOTEIO:0;
}
'''+s[idx:]
(HERE/'owner-regression.c').write_text(s)
s=(OLD/'check-owner.py').read_text().replace('stage=376','stage=377').replace('30,31,32,33]','30,31,32,33,34,35]');(HERE/'check-owner.py').write_text(s)
print('Prepared actual IO/session/cleanup and owner models, including forced-reset retention on ambiguous mapping.')
