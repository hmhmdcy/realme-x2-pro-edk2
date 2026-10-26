/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual V4L2 userspace exerciser: changing frames, mmap, exported DMABUF. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define BUFFERS 2
#define FRAMES 8

struct memory { void *address; unsigned length; int dma; };
struct frame { uint32_t input_crc, output_crc, y_different; uint64_t uv_error; };
struct stream {
	const char *node, *directory;
	unsigned id, width, height, stride, frames;
	int dmabuf, nv21, close_streaming;
	struct frame result[FRAMES];
	pthread_barrier_t *barrier;
};

static int call(int fd, unsigned long request, void *arg)
{
	int ret;
	do { ret = ioctl(fd, request, arg); } while (ret < 0 && errno == EINTR);
	if (ret < 0) {
		fprintf(stderr, "ioctl %lx failed errno=%d\n", request, errno);
		exit(2);
	}
	return ret;
}

static uint32_t crc32(const void *address, unsigned size)
{
	const unsigned char *p = address;
	uint32_t crc = 0;
	for (unsigned i = 0; i < size; i++) {
		crc ^= p[i];
		for (unsigned bit = 0; bit < 8; bit++)
			crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
	}
	return crc;
}

static unsigned char luma(unsigned id,unsigned sequence,unsigned x,unsigned y)
{
 (void)id;(void)sequence;unsigned row=y/80,col=x/80;
 return !row?16+32*col:row<4?128:row==4?64:192;
}
static unsigned char chroma(const struct stream *s,unsigned sequence,unsigned x,unsigned y)
{
 (void)sequence;unsigned row=(2*y)/80,col=x/80;unsigned u,v;
 if(!row){u=v=128;}else if(row<4){u=96+32*(col%3);v=96+32*(row-1);}else{u=64+48*(col%4);v=208-48*(col/2);}
 return ((x&1)^s->nv21)?v:u;
}

static void pattern(const struct stream *s, void *address, unsigned sequence)
{
	unsigned char *p = address;
	memset(p, 0x55, s->stride * s->height * 3 / 2);
	for (unsigned y = 0; y < s->height; y++)
		for (unsigned x = 0; x < s->width; x++)
			p[y * s->stride + x] = luma(s->id, sequence, x, y);
	p += s->stride * s->height;
	for (unsigned y = 0; y < s->height / 2; y++)
		for (unsigned x = 0; x < s->width; x++)
			p[y * s->stride + x] = chroma(s, sequence, x, y);
}

static struct v4l2_format format(int fd, const struct stream *s, unsigned extra)
{
	struct v4l2_format f = { .type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE };
	f.fmt.pix_mp.width = s->width;
	f.fmt.pix_mp.height = s->height + extra;
	f.fmt.pix_mp.pixelformat = s->nv21 ? V4L2_PIX_FMT_NV21 : V4L2_PIX_FMT_NV12;
	f.fmt.pix_mp.plane_fmt[0].bytesperline = s->stride;
	call(fd, VIDIOC_S_FMT, &f);
	assert(f.fmt.pix_mp.num_planes == 1 && f.fmt.pix_mp.width == s->width &&
	       f.fmt.pix_mp.height == s->height + extra &&
	       f.fmt.pix_mp.plane_fmt[0].bytesperline == s->stride);
	return f;
}

static void request(int fd, unsigned type, unsigned memory, unsigned count)
{
	struct v4l2_requestbuffers r = { .type = type, .memory = memory, .count = count };
	call(fd, VIDIOC_REQBUFS, &r);
	assert(r.count >= count);
}

static struct memory allocate(int fd, unsigned type, unsigned index, int export)
{
	struct v4l2_plane plane = {};
	struct v4l2_buffer b = { .type = type, .memory = V4L2_MEMORY_MMAP,
		.index = index, .length = 1, .m.planes = &plane };
	struct memory m = { .dma = -1 };
	call(fd, VIDIOC_QUERYBUF, &b);
	m.length = plane.length;
	m.address = mmap(NULL, m.length, PROT_READ | PROT_WRITE, MAP_SHARED,
			 fd, plane.m.mem_offset);
	assert(m.address != MAP_FAILED);
	if (export) {
		struct v4l2_exportbuffer e = { .type = type, .index = index,
			.flags = O_RDWR | O_CLOEXEC };
		call(fd, VIDIOC_EXPBUF, &e);
		m.dma = e.fd;
	}
	return m;
}

static void queue(int fd, struct stream *s, unsigned type, unsigned index,
		  const struct memory *m, unsigned sequence)
{
	unsigned offset = s->dmabuf && type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE ? 16 : 0;
	struct v4l2_plane plane = { .length = m->length, .data_offset = offset };
	struct v4l2_buffer b = { .type = type, .index = index, .length = 1,
		.memory = s->dmabuf ? V4L2_MEMORY_DMABUF : V4L2_MEMORY_MMAP,
		.m.planes = &plane, .field = V4L2_FIELD_NONE };
	if (s->dmabuf)
		plane.m.fd = m->dma;
	if (type == V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE) {
		pattern(s, m->address + offset, sequence);
		s->result[sequence].input_crc = crc32(m->address + offset,
						      s->stride * s->height * 3 / 2);
		plane.bytesused = offset + s->stride * s->height * 3 / 2;
		b.timestamp.tv_sec = 1000 + s->id;
		b.timestamp.tv_usec = sequence * 1000;
	}
	call(fd, VIDIOC_QBUF, &b);
}

static struct v4l2_buffer dequeue(int fd, unsigned type, const struct stream *s,
				  struct v4l2_plane *plane)
{
	struct pollfd p = { .fd = fd, .events = POLLIN | POLLOUT };
	struct v4l2_buffer b = { .type = type, .length = 1,
		.memory = s->dmabuf ? V4L2_MEMORY_DMABUF : V4L2_MEMORY_MMAP,
		.m.planes = plane };
	int ret;
	struct timespec began, now;
	assert(!clock_gettime(CLOCK_MONOTONIC, &began));
	for (;;) {
		ret = ioctl(fd, VIDIOC_DQBUF, &b);
		if (!ret)
			break;
		if (errno == EINTR)
			continue;
		assert(errno == EAGAIN);
		assert(!clock_gettime(CLOCK_MONOTONIC, &now) && now.tv_sec - began.tv_sec < 15);
		do { ret = poll(&p, 1, 10000); } while (ret < 0 && errno == EINTR);
		assert(ret > 0);
	}
	assert(!(b.flags & V4L2_BUF_FLAG_ERROR));
	return b;
}

static void save(const struct stream *s, const void *address, unsigned bytes,
		  unsigned sequence, int failure)
{
	char path[512];
	if (failure)
		snprintf(path, sizeof(path), "%s/case-%u-failed-%u-private.nv12",
			 s->directory, s->id, sequence);
	else
		snprintf(path, sizeof(path), "%s/case-%u-last-private.nv12", s->directory, s->id);
	int fd = open(path, O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC, 0600);
	assert(fd >= 0);
	const unsigned char *p = address;
	while (bytes) {
		ssize_t n = write(fd, p, bytes);
		assert(n > 0);
		p += n;
		bytes -= n;
	}
	assert(!fsync(fd));
	close(fd);
}

static void *run_stream(void *argument)
{
	struct stream *s = argument;
	int fd = open(s->node, O_RDWR | O_NONBLOCK | O_CLOEXEC), exporter = -1;
	assert(fd >= 0 && s->frames <= FRAMES && s->frames >= BUFFERS);
	struct v4l2_capability cap;
	call(fd, VIDIOC_QUERYCAP, &cap);
	assert(!strcmp((char *)cap.driver, "qcom-ipe-a5") &&
	       (cap.device_caps & V4L2_CAP_VIDEO_M2M_MPLANE));
	struct v4l2_format f = format(fd, s, 0);
	unsigned bytes = f.fmt.pix_mp.plane_fmt[0].sizeimage;
	struct memory input[BUFFERS], output[BUFFERS];
	unsigned src = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
	unsigned dst = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
	if (s->dmabuf) {
		exporter = open(s->node, O_RDWR | O_NONBLOCK | O_CLOEXEC);
		assert(exporter >= 0);
		format(exporter, s, 2);
		request(exporter, src, V4L2_MEMORY_MMAP, 2 * BUFFERS);
		for (unsigned i = 0; i < BUFFERS; i++) {
			input[i] = allocate(exporter, src, i, 1);
			output[i] = allocate(exporter, src, BUFFERS + i, 1);
		}
		request(fd, src, V4L2_MEMORY_DMABUF, BUFFERS);
		request(fd, dst, V4L2_MEMORY_DMABUF, BUFFERS);
	} else {
		request(fd, src, V4L2_MEMORY_MMAP, BUFFERS);
		request(fd, dst, V4L2_MEMORY_MMAP, BUFFERS);
		for (unsigned i = 0; i < BUFFERS; i++) {
			input[i] = allocate(fd, src, i, 0);
			output[i] = allocate(fd, dst, i, 0);
		}
	}
	errno = 0;
	assert(ioctl(fd, VIDIOC_S_FMT, &f) == -1 && errno == EBUSY);
	for (unsigned i = 0; i < BUFFERS; i++) {
		memset(output[i].address, 0xa7, output[i].length);
		queue(fd, s, src, i, &input[i], i);
		queue(fd, s, dst, i, &output[i], i);
	}
	call(fd, VIDIOC_STREAMON, &src);
	call(fd, VIDIOC_STREAMON, &dst);
	if (s->barrier)
		pthread_barrier_wait(s->barrier);
	for (unsigned sequence = 0; sequence < s->frames; sequence++) {
		struct v4l2_plane plane = {};
		struct v4l2_buffer b = dequeue(fd, dst, s, &plane);
		assert(b.index < BUFFERS && b.sequence == sequence &&
		       b.timestamp.tv_sec == 1000 + s->id &&
		       b.timestamp.tv_usec == sequence * 1000 &&
		       plane.data_offset == 0 && plane.bytesused == bytes);
		unsigned char *p = output[b.index].address;
		struct frame *r = &s->result[sequence];
		r->output_crc = crc32(p, bytes);
		for (unsigned y = 0; y < s->height; y++)
			for (unsigned x = 0; x < s->width; x++)
				r->y_different += p[y * s->stride + x] != luma(s->id, sequence, x, y);
		for (unsigned y = 0; y < s->height / 2; y++)
			for (unsigned x = 0; x < s->width; x++)
				r->uv_error += abs((int)p[s->stride * s->height + y * s->stride + x] -
						  (int)chroma(s, sequence, x, y));
		fprintf(stderr, "frame case=%u sequence=%u input_crc=%u output_crc=%u Ydiff=%u UVerror=%llu\n",
			s->id, sequence, r->input_crc, r->output_crc, r->y_different,
			(unsigned long long)r->uv_error);
		if (r->y_different || r->uv_error >= (uint64_t)s->width * s->height / 2) {
			save(s, p, bytes, sequence, 1);
			exit(3);
		}
		for (unsigned i = bytes; i < output[b.index].length; i++)
			assert(p[i] == 0xa7);
		if (sequence + 1 == s->frames)
			save(s, p, bytes, sequence, 0);
		struct v4l2_plane in_plane = {};
		struct v4l2_buffer in = dequeue(fd, src, s, &in_plane);
		assert(in.index < BUFFERS && in.sequence == sequence);
		assert(r->input_crc == crc32(input[in.index].address + (s->dmabuf ? 16 : 0), bytes));
		if (sequence + BUFFERS < s->frames) {
			memset(output[b.index].address, 0xa7, output[b.index].length);
			queue(fd, s, dst, b.index, &output[b.index], sequence + BUFFERS);
			queue(fd, s, src, in.index, &input[in.index], sequence + BUFFERS);
		}
	}
	if (!s->close_streaming) {
		call(fd, VIDIOC_STREAMOFF, &src);
		call(fd, VIDIOC_STREAMOFF, &dst);
	}
	close(fd); /* also test close without explicit STREAMOFF */
	for (unsigned i = 0; i < BUFFERS; i++) {
		munmap(input[i].address, input[i].length);
		munmap(output[i].address, output[i].length);
		if (input[i].dma >= 0) close(input[i].dma);
		if (output[i].dma >= 0) close(output[i].dma);
	}
	if (exporter >= 0) close(exporter);
	return NULL;
}

int inherited386_main(int argc, char **argv)
{
	assert(argc == 3);
	pthread_barrier_t barrier;
	assert(!pthread_barrier_init(&barrier, NULL, 2));
	struct stream streams[] = {
		{ .id = 0, .width = 640, .height = 480, .stride = 640, .frames = 6 },
		{ .id = 1, .width = 640, .height = 480, .stride = 672, .frames = 4,
		  .nv21 = 1, .dmabuf = 1, .close_streaming = 1 },
		{ .id = 2, .width = 640, .height = 480, .stride = 640, .frames = 4,
		  .barrier = &barrier },
		{ .id = 3, .width = 640, .height = 480, .stride = 640, .frames = 4,
		  .nv21 = 1, .barrier = &barrier },
	};
	for (unsigned i = 0; i < 4; i++) {
		streams[i].node = argv[1];
		streams[i].directory = argv[2];
	}
	run_stream(&streams[0]);
	run_stream(&streams[1]);
	pthread_t threads[2];
	assert(!pthread_create(&threads[0], NULL, run_stream, &streams[2]));
	assert(!pthread_create(&threads[1], NULL, run_stream, &streams[3]));
	assert(!pthread_join(threads[0], NULL) && !pthread_join(threads[1], NULL));
	puts("{\"passed\":true,\"cases\":[");
	for (unsigned i = 0; i < 4; i++) {
		struct stream *s = &streams[i];
		printf("%s{\"id\":%u,\"width\":%u,\"height\":%u,\"stride\":%u,"
		       "\"nv21\":%s,\"dmabuf\":%s,\"close_streaming\":%s,\"frames\":[",
		       i ? "," : "", s->id, s->width, s->height, s->stride,
		       s->nv21 ? "true" : "false", s->dmabuf ? "true" : "false",
		       s->close_streaming ? "true" : "false");
		for (unsigned j = 0; j < s->frames; j++) {
			struct frame *r = &s->result[j];
			printf("%s{\"sequence\":%u,\"input_crc\":%u,\"output_crc\":%u,"
			       "\"y_different\":%u,\"uv_abs_error\":%llu}",
			       j ? "," : "", j, r->input_crc, r->output_crc, r->y_different,
			       (unsigned long long)r->uv_error);
		}
		printf("]}");
	}
	puts("]}");
	return 0;
}

static int test_nv21;
struct test_context {
 int fd;
 struct stream s;
 struct memory in, out;
};
static const unsigned output_type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
static const unsigned capture_type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
static const char *status_path="/sys/bus/platform/devices/ac10000.icp/m2m_status";
static void snapshot(char *text, size_t bytes)
{
 FILE *f=fopen(status_path,"r");assert(f && fgets(text,bytes,f));fclose(f);
 text[strcspn(text,"\n")]=0;
}
static uint64_t metric(const char *text,const char *key)
{
 char pattern[80];snprintf(pattern,sizeof(pattern),"\"%s\":",key);
 const char *p=strstr(text,pattern);assert(p);return strtoull(p+strlen(pattern),NULL,10);
}
static struct test_context setup(const char *node,unsigned id)
{
 struct test_context c={.fd=open(node,O_RDWR|O_NONBLOCK|O_CLOEXEC),
  .s={.id=id,.width=640,.height=480,.stride=640,.frames=2,.nv21=test_nv21}};
 assert(c.fd>=0);format(c.fd,&c.s,0);
 request(c.fd,output_type,V4L2_MEMORY_MMAP,2);
 request(c.fd,capture_type,V4L2_MEMORY_MMAP,2);
 c.in=allocate(c.fd,output_type,0,0);c.out=allocate(c.fd,capture_type,0,0);
 return c;
}
static void enqueue(struct test_context *c)
{
 memset(c->out.address,0xa7,c->out.length);
 queue(c->fd,&c->s,output_type,0,&c->in,0);
 queue(c->fd,&c->s,capture_type,0,&c->out,0);
}
static void stream_on(struct test_context *c)
{
 unsigned a=output_type,b=capture_type;
 call(c->fd,VIDIOC_STREAMON,&a);call(c->fd,VIDIOC_STREAMON,&b);
}
static void stream_off(struct test_context *c,int capture_first)
{
 unsigned a=capture_first?capture_type:output_type;
 unsigned b=capture_first?output_type:capture_type;
 call(c->fd,VIDIOC_STREAMOFF,&a);call(c->fd,VIDIOC_STREAMOFF,&b);
}
static void unmap_context(struct test_context *c)
{
 assert(!munmap(c->in.address,c->in.length));assert(!munmap(c->out.address,c->out.length));
 c->in.address=c->out.address=MAP_FAILED;
}
static void close_context(struct test_context *c)
{
 if(c->in.address!=MAP_FAILED)unmap_context(c);
 assert(!close(c->fd));c->fd=-1;
}
static void verify_frame(struct test_context *c)
{
 struct v4l2_plane p={};struct v4l2_buffer b=dequeue(c->fd,capture_type,&c->s,&p);
 assert(b.index==0 && b.sequence==0 && b.timestamp.tv_sec==1000+c->s.id);
 unsigned bad=0;unsigned char *data=c->out.address;
 for(unsigned y=0;y<c->s.height;y++)for(unsigned x=0;x<c->s.width;x++)
  bad+=data[y*c->s.stride+x]!=luma(c->s.id,0,x,y);
 assert(!bad);struct v4l2_plane in={};dequeue(c->fd,output_type,&c->s,&in);
}
static int log_tail(void)
{
 int fd=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_CLOEXEC);assert(fd>=0);
 assert(lseek(fd,0,SEEK_END)>=0);return fd;
}
static void wait_configured(int fd)
{
 struct timespec begin,now;assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
 char line[8192];
 for(;;){
  ssize_t n=read(fd,line,sizeof(line)-1);
  if(n>0){line[n]=0;if(strstr(line,"ac10000.icp: A5 IPE CONFIG_IO acknowledged"))return;continue;}
  if(n<0 && errno==EINTR)continue;
  assert(n<0 && errno==EAGAIN);struct pollfd p={.fd=fd,.events=POLLIN};
  int ret=poll(&p,1,100);assert(ret>=0);
  assert(!clock_gettime(CLOCK_MONOTONIC,&now) && now.tv_sec-begin.tv_sec<8);
 }
}
static void cancel_case(const char *node,unsigned id,int close_active,int peer)
{
 char before[2048],after[2048];snapshot(before,sizeof(before));
 struct test_context c=setup(node,id),other={.fd=-1};
 if(peer){other=setup(node,20+id);enqueue(&other);}
 enqueue(&c);int log=log_tail();stream_on(&c);wait_configured(log);assert(!close(log));
 if(peer)stream_on(&other);
 if(close_active)close_context(&c);else stream_off(&c,id==1);
 if(peer){verify_frame(&other);stream_off(&other,0);close_context(&other);}
 if(!close_active){enqueue(&c);stream_on(&c);verify_frame(&c);stream_off(&c,0);close_context(&c);}
 snapshot(after,sizeof(after));
 assert(metric(after,"cancelled")>metric(before,"cancelled"));
 assert(metric(after,"failed")==metric(before,"failed"));
 assert(!metric(after,"users") && !metric(after,"orphans"));
 printf("{\"case\":%u,\"close_active\":%s,\"peer\":%s,\"configured_marker_observed_before_abort\":true,\"before\":%s,\"after\":%s,\"passed\":true}\n",id,close_active?"true":"false",peer?"true":"false",before,after);fflush(stdout);
}
static void expect_error(struct test_context *c,unsigned type)
{
 struct timespec begin,now;assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
 for(;;){
  struct v4l2_plane p={};struct v4l2_buffer b={.type=type,.memory=c->s.dmabuf?V4L2_MEMORY_DMABUF:V4L2_MEMORY_MMAP,.length=1,.m.planes=&p};
  int ret=ioctl(c->fd,VIDIOC_DQBUF,&b);
  if(!ret){assert(b.flags&V4L2_BUF_FLAG_ERROR);return;}
  if(errno==EIO)return;
  assert(errno==EAGAIN || errno==EINTR);
  assert(!clock_gettime(CLOCK_MONOTONIC,&now) && now.tv_sec-begin.tv_sec<8);
  struct pollfd f={.fd=c->fd,.events=POLLIN|POLLOUT};assert(poll(&f,1,100)>=0);
 }
}
static void rejected_alias(const char *node)
{
 char before[2048],after[2048];snapshot(before,sizeof(before));
 struct test_context exporter=setup(node,30),peer=setup(node,31);
 struct test_context bad={.fd=open(node,O_RDWR|O_NONBLOCK|O_CLOEXEC),.s={.id=32,.width=640,.height=480,.stride=640,.dmabuf=1}};
 assert(bad.fd>=0);format(bad.fd,&bad.s,0);
 struct v4l2_exportbuffer e={.type=output_type,.index=0,.flags=O_RDWR|O_CLOEXEC};call(exporter.fd,VIDIOC_EXPBUF,&e);
 request(bad.fd,output_type,V4L2_MEMORY_DMABUF,2);request(bad.fd,capture_type,V4L2_MEMORY_DMABUF,2);
 unsigned bytes=640*480*3/2;
 struct v4l2_plane p={.length=exporter.in.length,.bytesused=bytes,.m.fd=e.fd};
 struct v4l2_buffer b={.type=output_type,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p};
 pattern(&exporter.s,exporter.in.address,0);call(bad.fd,VIDIOC_QBUF,&b);
 b.type=capture_type;p.bytesused=0;call(bad.fd,VIDIOC_QBUF,&b);
 enqueue(&peer);int log=log_tail();stream_on(&bad);wait_configured(log);assert(!close(log));
 stream_on(&peer);
 expect_error(&bad,capture_type);expect_error(&bad,output_type);
 expect_error(&peer,capture_type);expect_error(&peer,output_type);
 stream_off(&bad,0);stream_off(&peer,0);
 assert(!close(bad.fd));assert(!close(e.fd));close_context(&exporter);close_context(&peer);
 snapshot(after,sizeof(after));
 assert(metric(after,"failed")==metric(before,"failed")+2);
 assert(metric(after,"completed")==metric(before,"completed"));
 assert(strstr(after,"\"fatal\":false") && !metric(after,"users"));
 struct test_context recovered=setup(node,33);enqueue(&recovered);stream_on(&recovered);verify_frame(&recovered);stream_off(&recovered,0);close_context(&recovered);
 char recovery[2048];snapshot(recovery,sizeof(recovery));
 assert(metric(recovery,"completed")==metric(after,"completed")+1);
 printf("{\"case\":4,\"same_dmabuf_alias_rejected\":true,\"peer_queue_error_verified\":true,\"reopen_recovery_pixel_verified\":true,\"hardware_fault_injection\":false,\"before\":%s,\"after\":%s,\"recovery\":%s,\"passed\":true}\n",before,after,recovery);fflush(stdout);
}
int inherited392_main(int argc,char **argv)
{
 assert(argc==2 || (argc==3 && !strcmp(argv[2],"--remaining")));
 if(argc==2){
  cancel_case(argv[1],0,0,0);
  cancel_case(argv[1],1,0,0);
  cancel_case(argv[1],2,1,0);
 }
 cancel_case(argv[1],3,0,1);
 rejected_alias(argv[1]);
 return 0;
}

static void set_chain_mode(unsigned mode)
{
 const char *path="/sys/module/camss_icp_a5_m2m/parameters/test_chain_mode";
 int fd=open(path,O_WRONLY|O_CLOEXEC);assert(fd>=0);char text[32];int n=snprintf(text,sizeof(text),"%u\n",mode);assert(write(fd,text,n)==n);assert(!close(fd));
 FILE *f=fopen(path,"r");unsigned actual;assert(f && fscanf(f,"%u",&actual)==1 && actual==mode);fclose(f);
}
static void dump_chain_file(const char *root,unsigned format,unsigned mode,const char *kind,const void *data,unsigned bytes)
{
 char path[512];snprintf(path,sizeof(path),"%s/format-%u-mode-%u-%s-private.nv12",root,format,mode,kind);
 int fd=open(path,O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);assert(fd>=0);const unsigned char *p=data;
 while(bytes){ssize_t n=write(fd,p,bytes);assert(n>0);p+=n;bytes-=n;}assert(!fsync(fd) && !close(fd));
 int directory=open(root,O_RDONLY|O_DIRECTORY|O_CLOEXEC);assert(directory>=0 && !fsync(directory) && !close(directory));
}
int main(int argc,char **argv)
{
 assert(argc==3);char before[2048],after[2048];snapshot(before,sizeof(before));unsigned bytes=640*480*3/2;
 unsigned char *pair=malloc(bytes);assert(pair);
 for(unsigned format=0;format<2;format++)for(unsigned mode=0;mode<8;mode++){
  test_nv21=format;set_chain_mode(mode);struct test_context c=setup(argv[1],60);enqueue(&c);stream_on(&c);
  struct v4l2_plane p={};struct v4l2_buffer b=dequeue(c.fd,capture_type,&c.s,&p);
  assert(b.index==0 && b.sequence==0 && b.timestamp.tv_sec==1060);
  struct v4l2_plane ip={};dequeue(c.fd,output_type,&c.s,&ip);
  assert(crc32(c.in.address,bytes)==c.s.result[0].input_crc);
  unsigned ydiff=0;unsigned char *out=c.out.address;uint64_t ysum=0;
  for(unsigned y=0;y<480;y++)for(unsigned x=0;x<640;x++){unsigned v=out[y*640+x];ydiff+=v!=luma(60,0,x,y);ysum+=v;}
  for(unsigned i=bytes;i<c.out.length;i++)assert(out[i]==0xa7);
  uint32_t output_crc=crc32(out,bytes);dump_chain_file(argv[2],format,mode,"output",out,bytes);
  if(!mode)dump_chain_file(argv[2],format,mode,"input",c.in.address,bytes);
  unsigned pairdiff=0;if(mode==1)memcpy(pair,out,bytes);if(mode==2)for(unsigned i=0;i<bytes;i++)pairdiff+=pair[i]!=out[i];
  stream_off(&c,0);close_context(&c);snapshot(after,sizeof(after));
  printf("{\"format\":%u,\"mode\":%u,\"y_different\":%u,\"y_sum\":%llu,\"pair_identity_different\":%u,\"output_crc\":%u,\"after\":%s,\"completed\":true}\n",format,mode,ydiff,(unsigned long long)ysum,pairdiff,output_crc,after);fflush(stdout);
  if(!mode)assert(!ydiff);
  if(mode==2)assert(!pairdiff);
  assert(!metric(after,"failed") && !metric(after,"cancelled") && !metric(after,"first_error"));
 }
 free(pair);set_chain_mode(0);snapshot(after,sizeof(after));assert(metric(after,"completed")==metric(before,"completed")+16 && metric(after,"direct_completed")==metric(after,"completed") && !metric(after,"users"));
 printf("{\"case\":\"fixed-conversion-chain\",\"frames\":16,\"before\":%s,\"after\":%s,\"passed\":true}\n",before,after);fflush(stdout);return 0;
}
