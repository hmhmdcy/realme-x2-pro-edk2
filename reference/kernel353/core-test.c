/* SPDX-License-Identifier: GPL-2.0-only */
#include "core-test-shim.h"
#include "actual-header-private.h"
#include "actual-hfi-private.c"
#include "actual-fw-private.c"
#include "original-reference-private.c"

static struct camss_a5_ring concurrent_ring;
static struct camss_a5_qhdr concurrent_header;
static u32 concurrent_data[1024];
static void *producer(void *arg)
{
	u32 tid=(uintptr_t)arg;
	for(u32 i=0;i<1000;i++){
		u32 packet[]={12,tid,i};int ret;
		while((ret=camss_a5_ring_write(&concurrent_ring,packet,sizeof(packet)))==-ENOSPC)sched_yield();
		assert(!ret);
	}
	return NULL;
}
static void concurrency(void)
{
	struct camss_a5_qtable table;u64 addresses[]={0x7401000,0x7402000,0x7500000};u32 lengths[]={4096,4096,102400};
	assert(!camss_a5_qtable_init(&table,addresses,lengths));concurrent_header=table.queues[0];
	assert(!camss_a5_ring_init(&concurrent_ring,&concurrent_header,concurrent_data,sizeof(concurrent_data)));
	pthread_t threads[2];assert(!pthread_create(&threads[0],NULL,producer,(void*)1));assert(!pthread_create(&threads[1],NULL,producer,(void*)2));
	u32 next[]={0,0};
	for(unsigned int n=0;n<2000;){
		u32 packet[3];size_t bytes;int ret=camss_a5_ring_read(&concurrent_ring,packet,sizeof(packet),&bytes);
		if(ret==-EAGAIN){sched_yield();continue;}
		assert(!ret&&bytes==12&&packet[1]>=1&&packet[1]<=2&&packet[2]==next[packet[1]-1]++);n++;
	}
	assert(!pthread_join(threads[0],NULL)&&!pthread_join(threads[1],NULL));assert(next[0]==1000&&next[1]==1000);
}
static void transport(void)
{
	struct camss_a5_qtable table;u64 addresses[]={0x7401000,0x7402000,0x7500000};u32 lengths[]={4096,4096,102400};
	struct hfi_qtbl original;memset(&original,0,sizeof(original));reference_init(&original,addresses);
	assert(!camss_a5_qtable_init(&table,addresses,lengths));assert(sizeof(original)==sizeof(table));assert(!memcmp(&table,&original,sizeof(table)));
	struct camss_a5_qtable untouched;memset(&untouched,0xa5,sizeof(untouched));struct camss_a5_qtable before=untouched;
	u64 bad_addresses[]={0x100000000ULL,0x7402000,0x7500000};assert(camss_a5_qtable_init(&untouched,bad_addresses,lengths)==-EINVAL);assert(!memcmp(&before,&untouched,sizeof(before)));
	u64 end_addresses[]={0xfffffffcULL,0x7402000,0x7500000};assert(camss_a5_qtable_init(&untouched,end_addresses,lengths)==-EINVAL);assert(!memcmp(&before,&untouched,sizeof(before)));
	struct camss_a5_ring ring;u32 data[12],reference_data[12],packet[11];
	table.queues[0].words=12;assert(!camss_a5_ring_init(&ring,&table.queues[0],data,sizeof(data)));
	unsigned int cases=0;
	for(u32 r=0;r<12;r++)for(u32 w=0;w<12;w++)for(u32 count=1;count<12;count++){
		for(u32 j=0;j<12;j++)data[j]=reference_data[j]=0xabc00000+j;
		for(u32 j=0;j<count;j++){packet[j]=0xcba00000+j;}
		packet[0]=count*4;
		table.queues[0].read=r;table.queues[0].write=w;memcpy(&original.q_hdr[0],&table.queues[0],956);
		reference_setup(&original,reference_data,NULL,NULL);int expected=hfi_write_cmd(packet);
		int result=camss_a5_ring_write(&ring,packet,count*4);assert((result==0)==(expected==0));
		assert(!memcmp(data,reference_data,sizeof(data)));assert(!memcmp(&original.q_hdr[0],&table.queues[0],956));cases++;
	}
	assert(cases==1584);
	/* Compare single-message wrap cases against the original bulk reader;
	 * multi-packet preservation below intentionally has a different API. */
	u32 messages[1024],reference_messages[1024],out[1024],old_out[1024];struct camss_a5_ring msg;
	assert(!camss_a5_ring_init(&msg,&table.queues[1],messages,sizeof(messages)));
	unsigned int rpos[]={0,1,500,1023},counts[]={1,2,255,256};unsigned int reads=0;
	for(unsigned int a=0;a<4;a++)for(unsigned int b=0;b<4;b++){
		u32 r=rpos[a],count=counts[b];memset(messages,0,sizeof(messages));
		for(u32 j=0;j<count;j++)messages[(r+j)%1024]=j?0x11220000+j:count*4;
		memcpy(reference_messages,messages,sizeof(messages));table.queues[1].read=r;table.queues[1].write=(r+count)%1024;
		memcpy(&original.q_hdr[1],&table.queues[1],956);reference_setup(&original,NULL,reference_messages,NULL);
		u32 old_words=0;assert(!hfi_read_message(old_out,1,&old_words));size_t bytes=0;assert(!camss_a5_ring_read(&msg,out,sizeof(out),&bytes));
		assert(bytes==count*4&&old_words==count&&!memcmp(out,old_out,bytes));assert(!memcmp(&original.q_hdr[1],&table.queues[1],956));reads++;
	}
	/* Multiple packets, including a wrapped header/payload boundary. */
	table.queues[1].read=1023;table.queues[1].write=4;messages[1023]=8;messages[0]=0x20001;messages[1]=12;messages[2]=0x20006;messages[3]=99;
	size_t bytes=777;memset(out,0xa5,sizeof(out));assert(camss_a5_ring_read(&msg,out,4,&bytes)==-ENOSPC&&bytes==777&&table.queues[1].read==1023&&out[0]==0xa5a5a5a5);
	assert(!camss_a5_ring_read(&msg,out,sizeof(out),&bytes)&&bytes==8&&out[1]==0x20001&&table.queues[1].read==1);
	assert(!camss_a5_ring_read(&msg,out,sizeof(out),&bytes)&&bytes==12&&out[2]==99&&table.queues[1].read==4);
	assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EAGAIN);
	/* Invalid packets and queue metadata leave caller output and indices. */
	for(u32 invalid=0;invalid<3;invalid++){
		table.queues[1].read=0;table.queues[1].write=1;messages[0]=(u32[]){0,5,4096}[invalid];bytes=777;out[0]=0xa5a5a5a5;
		assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EBADMSG&&bytes==777&&out[0]==0xa5a5a5a5&&table.queues[1].read==0);
	}
	table.queues[1].read=0;table.queues[1].write=1;messages[0]=12;assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EAGAIN&&table.queues[1].read==0);
	table.queues[1].read=1024;assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EPROTO);
	table.queues[1].read=0;table.queues[1].status=0;assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-ENODEV);
	table.queues[1].status=1;table.queues[1].words=1023;assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EPROTO);
	table.queues[1].words=1024;table.queues[1].packet_size=4;assert(camss_a5_ring_read(&msg,out,sizeof(out),&bytes)==-EPROTO);
	packet[0]=8;u32 previous=table.queues[0].write;assert(camss_a5_ring_write(&ring,packet,4)==-EINVAL&&table.queues[0].write==previous);
	printf("TRANSPORT_PASS writes=%u reference_reads=%u\n",cases,reads);
}

static void firmware(const char *path,const char *expected_path)
{
	FILE *file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));long len=ftell(file);rewind(file);assert(len>0);
	u8 *raw=malloc(len),*copy=malloc(len),*dest=malloc(CAMSS_A5_FW_WINDOW+32),*expected=malloc(CAMSS_A5_FW_WINDOW);assert(raw&&copy&&dest&&expected);
	assert(fread(raw,1,len,file)==(size_t)len);fclose(file);file=fopen(expected_path,"rb");assert(file&&fread(expected,1,CAMSS_A5_FW_WINDOW,file)==CAMSS_A5_FW_WINDOW);fclose(file);
	struct firmware fw={(size_t)len,raw};struct camss_a5_fw_layout layout;
	memset(dest,0xa5,CAMSS_A5_FW_WINDOW+32);assert(!camss_a5_fw_load(&fw,dest+16,CAMSS_A5_FW_WINDOW,&layout));
	assert(layout.span==3686400&&layout.segments==3&&layout.entry==0);assert(!memcmp(dest+16,expected,CAMSS_A5_FW_WINDOW));
	for(unsigned int i=0;i<16;i++)assert(dest[i]==0xa5&&dest[CAMSS_A5_FW_WINDOW+16+i]==0xa5);
	for(unsigned int kind=0;kind<17;kind++){
		memcpy(copy,raw,len);fw.data=copy;fw.size=len;u32 ph=get_unaligned_le32(copy+28);u32 window=CAMSS_A5_FW_WINDOW;
		switch(kind){
		case 0:fw.size=51;break;case 1:copy[0]=0;break;case 2:copy[EI_CLASS]=2;break;case 3:copy[EI_DATA]=2;break;
		case 4:put16(copy+18,183);break;case 5:put32(copy+24,4);break;case 6:put16(copy+42,31);break;
		case 7:put32(copy+28,UINT32_MAX);break;case 8:put16(copy+44,0);break;
		case 9:put32(copy+ph+16,UINT32_MAX);break;case 10:put32(copy+ph+4,UINT32_MAX);break;
		case 11:put32(copy+ph+8,UINT32_MAX-1);break;case 12:window=1024;break;
		case 13:put32(copy+ph+28,3);break;case 14:put32(copy+ph+4,get_unaligned_le32(copy+ph+4)+1);break;
		case 15:put32(copy+ph+24,PF_R|PF_W);break;case 16:put32(copy+ph,PT_NOTE);break;
		}
		memset(dest,0xa5,CAMSS_A5_FW_WINDOW+32);layout=(struct camss_a5_fw_layout){123,456,789};
		assert(camss_a5_fw_load(&fw,dest+16,window,&layout)==-ENOEXEC&&layout.entry==123&&layout.span==456&&layout.segments==789);
		for(unsigned int i=0;i<CAMSS_A5_FW_WINDOW+32;i++)assert(dest[i]==0xa5);
	}
	free(raw);free(copy);free(dest);free(expected);puts("FIRMWARE_PASS original_plus_17_rejections BSS_and_gaps_zeroed guards_intact");
}
int main(int argc,char **argv)
{
	assert(argc==3);transport();concurrency();firmware(argv[1],argv[2]);
	printf("CORE_PASS concurrent_packets=2000 dma_read=%u dma_write=%u dma_full=%u\n",dma_reads,dma_writes,dma_full);return 0;
}
