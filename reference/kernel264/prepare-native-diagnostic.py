from pathlib import Path
R=Path(__file__).parent;s=(R/'native-stream-probe.c').read_text()
s=s.replace('unsigned frames,checked,changed,errors,pts_bad,busy_missing;', 'unsigned frames,checked,changed,errors,pts_bad,busy_missing,zero_pts;')
needle='''  d->last_pts=meta->pts;''';assert s.count(needle)==1
s=s.replace(needle,'''  d->last_pts=meta->pts;
  if(meta->pts<=0)d->zero_pts++;
  struct spa_meta_busy *busy=spa_buffer_find_meta_data(buf,SPA_META_Busy,sizeof(*busy));
  fprintf(stderr,"native-frame at=%.6f buffer=%p fd=%d pts=%"PRIi64" seq=%"PRIu64" busy=%u\\n",now(),(void*)b,(int)buf->datas[0].fd,meta->pts,meta->seq,busy?SPA_ATOMIC_LOAD(busy->count):0);''')
s=s.replace('if(digest(h->pixels,h->size)!=h->digest || !meta || meta->pts!=h->pts) d->changed++;','''if(digest(h->pixels,h->size)!=h->digest || !meta || meta->pts!=h->pts) {
  d->changed++;
  fprintf(stderr,"native-changed at=%.6f buffer=%p before-pts=%"PRIi64" after-pts=%"PRIi64"\\n",now(),(void*)h->buffer,h->pts,meta?meta->pts:INT64_MIN);
 }''')
s=s.replace('\\"metadata_busy_missing\\":%u,','\\"zero_header_pts\\":%u,\\"metadata_busy_missing\\":%u,')
s=s.replace('d.frames,d.checked,d.changed,d.busy_missing,','d.frames,d.checked,d.changed,d.zero_pts,d.busy_missing,')
s=s.replace('!d.busy_missing && d.last_pts','!d.busy_missing && !d.zero_pts && d.last_pts')
(R/'native-diagnostic-probe.c').write_text(s)
