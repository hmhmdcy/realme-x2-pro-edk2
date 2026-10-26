/* Lose one real frame completion while another configured context is queued. */
static unsigned read_parameter(const char *name)
{
 char path[256];snprintf(path,sizeof(path),"/sys/module/qcom_camss_icp_a5_core/parameters/%s",name);
 FILE *f=fopen(path,"r");unsigned value;assert(f && fscanf(f,"%u",&value)==1);fclose(f);return value;
}
static void arm_ack_loss(void)
{
 assert(read_parameter("test_drop_frame_ack")==0 && read_parameter("test_dropped_frame_acks")==0);
 int fd=open("/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack",O_WRONLY|O_CLOEXEC);assert(fd>=0 && write(fd,"1\n",2)==2);assert(!close(fd));
}
static unsigned verify_error_pixels(struct test_context *c,unsigned sequence)
{
 unsigned changed=0;unsigned char *data=c->out.address;
 for(unsigned y=0;y<c->s.height;y++)for(unsigned x=0;x<c->s.width;x++)changed+=data[y*c->s.stride+x]!=luma(c->s.id,sequence,x,y);
 return changed;
}
int main(int argc,char **argv)
{
 assert(argc==2);char before[2048],failed[2048],retry_blocked[2048],closed[2048],recovered[2048];snapshot(before,sizeof(before));
 struct test_context a=setup(argv[1],50),b=setup(argv[1],51);
 enqueue(&a);enqueue(&b);stream_on(&a);stream_on(&b);verify_sequence(&a,0);verify_sequence(&b,0);
 char warm[2048],warm_core[2048];snapshot(warm,sizeof(warm));assert(metric(warm,"completed")==metric(before,"completed")+2 && metric(warm,"starts")==metric(before,"starts")+1 && metric(warm,"stops")==metric(before,"stops"));
 FILE *core_file=fopen("/sys/bus/platform/devices/ac10000.icp/state","r");assert(core_file && fgets(warm_core,sizeof(warm_core),core_file));fclose(core_file);warm_core[strcspn(warm_core,"\n")]=0;
 assert(metric(warm_core,"session_creates")==2 && metric(warm_core,"session_destroys")==0 && metric(warm_core,"session_peak")==2);
 arm_ack_loss();struct timespec begin,end;assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
 enqueue_sequence(&a,1);enqueue_sequence(&b,1);
 expect_error(&a,capture_type);expect_error(&a,output_type);expect_error(&b,capture_type);expect_error(&b,output_type);
 assert(!clock_gettime(CLOCK_MONOTONIC,&end));double elapsed=end.tv_sec-begin.tv_sec+(end.tv_nsec-begin.tv_nsec)/1e9;
 snapshot(failed,sizeof(failed));assert(elapsed>=4.5 && elapsed<12.0);
 assert(metric(failed,"jobs")==metric(before,"jobs")+4 && metric(failed,"failed")==metric(before,"failed")+2 && metric(failed,"completed")==metric(before,"completed")+2);
 assert(strstr(failed,"\"fatal\":true") && strstr(failed,"\"running\":false") && strstr(failed,"\"pinned\":false"));
 assert(read_parameter("test_drop_frame_ack")==0 && read_parameter("test_dropped_frame_acks")==1);
 /* Read only after the error work finished and reset retired its imports.
  * The timed-out frame was processed; its successful ACK was withheld.
  * Its peer must never have touched the newly queued destination.
  */
 unsigned target_y_errors=verify_error_pixels(&a,1);assert(!target_y_errors);
 for(unsigned i=0;i<b.out.length;i++)assert(((unsigned char*)b.out.address)[i]==0xa7);
 struct test_context third=setup(argv[1],52);enqueue(&third);stream_on(&third);expect_error(&third,capture_type);expect_error(&third,output_type);
 stream_off(&third,0);close_context(&third);snapshot(retry_blocked,sizeof(retry_blocked));assert(strstr(retry_blocked,"\"fatal\":true") && metric(retry_blocked,"failed")==metric(before,"failed")+3);
 stream_off(&a,0);stream_off(&b,0);close_context(&b);close_context(&a);snapshot(closed,sizeof(closed));assert(strstr(closed,"\"fatal\":false") && !metric(closed,"users"));
 struct test_context healthy=setup(argv[1],53);enqueue(&healthy);stream_on(&healthy);verify_sequence(&healthy,0);stream_off(&healthy,0);close_context(&healthy);snapshot(recovered,sizeof(recovered));
 assert(metric(recovered,"jobs")==metric(before,"jobs")+6 && metric(recovered,"completed")==metric(before,"completed")+3 && metric(recovered,"failed")==metric(before,"failed")+3);
 assert(metric(recovered,"cancelled")==metric(before,"cancelled") && metric(recovered,"direct_completed")==metric(recovered,"completed"));
 printf("{\"case\":\"lost-valid-frame-ack\",\"elapsed_seconds\":%.6f,\"dropped_ack_count\":%u,\"two_configured_contexts\":true,\"timed_out_frame_y_verified_after_reset\":true,\"peer_destination_untouched\":true,\"new_context_blocked_until_old_consumers_closed\":true,\"normal_reopen_recovery_pixel_verified\":true,\"before\":%s,\"warm\":%s,\"warm_core\":%s,\"failed\":%s,\"retry_blocked\":%s,\"closed\":%s,\"recovered\":%s,\"passed\":true}\n",elapsed,read_parameter("test_dropped_frame_acks"),before,warm,warm_core,failed,retry_blocked,closed,recovered);fflush(stdout);
 return 0;
}
