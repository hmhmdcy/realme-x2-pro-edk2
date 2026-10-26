int main(void)
{
 struct iommu_domain domain={true},other={true};struct device dev={&domain};
 struct page pages[6]={{0x100000},{0x500000},{0x200000},{0x700000},{0x300000},{0x900000}};
 struct scatterlist sg[3]={{&pages[0],4096,0,0x30000000,4096},{&pages[1],8192,0,0x30001000,8192},{&pages[2],4096,0,0x30003000,4096}};
 struct sg_table table={sg,3,3};struct dma_buf b;init_buffer(&b,&table,16384);
 unsigned cases=0;
 for(u32 offset=0;offset<=16384;offset+=4){
  for(unsigned size=0;size<5;++size){
   const u32 sizes[]={0,4,4096,8192,16384};u32 value=0xdeadbeef;
   int ret=image_iova(&table,offset,sizes[size],&value);
   bool valid=sizes[size] && offset<=16384-sizes[size];
   assert((ret==0)==valid);
   assert(value==(valid?0x30000000+offset:0xdeadbeef));++cases;
  }
 }
 struct camss_a5_dma_image image={0};assert(!camss_a5_dma_image_map(&dev,&image,&b,16,12288,DMA_TO_DEVICE));
 assert(image.iova==0x30000010 && b.refs==2 && last_usage==DMA_RESV_USAGE_WRITE);
 assert(camss_a5_dma_image_map(&dev,&image,&b,0,4,DMA_TO_DEVICE)==-EBUSY);
 assert(!camss_a5_dma_image_release(&image) && b.refs==1);clean_provider();++cases;
 for(unsigned fault=0;fault<7;++fault){
  u64 saved=sg[1].address;b.resv->waited=fault==0?0:fault==1?-EINTR:1;
  fail_attach=fault==2;fail_map=fault==3;if(fault==4)sg[1].address+=4;
  u32 offset=fault==5?3:fault==6?16380:16;
  int ret=camss_a5_dma_image_map(&dev,&image,&b,offset,12288,DMA_FROM_DEVICE);assert(ret<0);
  assert(!image.buffer && !image.sgt && b.refs==1);sg[1].address=saved;b.resv->waited=1;clean_provider();++cases;
 }
 assert(!camss_a5_dma_image_map(&dev,&image,&b,0,4096,DMA_FROM_DEVICE));assert(last_usage==DMA_RESV_USAGE_READ);
 dev.domain=&other;assert(camss_a5_dma_image_release(&image)==-EXDEV && refs==1 && mappings==1 && attachments==1);
 dev.domain=&domain;assert(!camss_a5_dma_image_release(&image));clean_provider();++cases;
 struct scatterlist edge={&pages[0],4096,0,0xfffffffcULL,4};struct sg_table et={&edge,1,1};u32 value=0;
 assert(!image_iova(&et,0,4,&value) && value==0xfffffffc);edge.dma_length=8;assert(image_iova(&et,0,8,&value)==-ERANGE);
 edge.address=0;assert(image_iova(&et,0,4,&value)==-ERANGE);++cases;
 struct scatterlist os[3]={{&pages[3],4096,0,0x40000000,4096},{&pages[4],8192,0,0x40001000,8192},{&pages[5],4096,0,0x40003000,4096}};
 struct sg_table ot={os,3,3};struct dma_buf out;init_buffer(&out,&ot,16384);
 struct camss_a5_dma_image output={0};
 assert(!camss_a5_dma_image_map(&dev,&image,&b,16,12288,DMA_TO_DEVICE));
 assert(!camss_a5_dma_image_map(&dev,&output,&out,0,12288,DMA_FROM_DEVICE));
 assert(!camss_a5_dma_images_disjoint(&image,&output));
 assert(!camss_a5_dma_image_release(&output));os[2].page=&pages[1];
 assert(!camss_a5_dma_image_map(&dev,&output,&out,0,16384,DMA_FROM_DEVICE));assert(camss_a5_dma_images_disjoint(&image,&output)==-EINVAL);
 assert(!camss_a5_dma_image_release(&output));os[2].page=&pages[5];
 assert(!camss_a5_dma_image_map(&dev,&output,&out,0,12288,DMA_FROM_DEVICE));
 fail_alloc=true;assert(camss_a5_dma_images_disjoint(&image,&output)==-ENOMEM);fail_alloc=false;
 assert(camss_a5_dma_images_disjoint(&image,&image)==-EINVAL);
 assert(!camss_a5_dma_image_release(&output) && !camss_a5_dma_image_release(&image));clean_provider();cases+=4;
 /* Two different exports of one backing range must not pass by IOVA alone. */
 os[0].page=sg[0].page;assert(!camss_a5_dma_image_map(&dev,&image,&b,16,16,DMA_TO_DEVICE));
 assert(!camss_a5_dma_image_map(&dev,&output,&out,16,16,DMA_FROM_DEVICE));
 assert(camss_a5_dma_images_disjoint(&image,&output)==-EINVAL);
 assert(!camss_a5_dma_image_release(&output));assert(!camss_a5_dma_image_map(&dev,&output,&out,32,16,DMA_FROM_DEVICE));
 assert(!camss_a5_dma_images_disjoint(&image,&output));
 assert(!camss_a5_dma_image_release(&output) && !camss_a5_dma_image_release(&image));cases+=2;
 /* Merged DMA entries still retain the original physical SG list. */
 sg[0].dma_length=12288;sg[1].address=0x30003000;sg[1].dma_length=4096;table.nents=2;
 assert(!image_iova(&table,0,16384,&value) && value==0x30000000);++cases;
 os[0].page=&pages[3];
 assert(!camss_a5_dma_image_map(&dev,&image,&b,0,16384,DMA_TO_DEVICE));
 assert(!camss_a5_dma_image_map(&dev,&output,&out,0,16384,DMA_FROM_DEVICE));
 assert(!camss_a5_dma_images_disjoint(&image,&output));
 assert(!camss_a5_dma_image_release(&output) && !camss_a5_dma_image_release(&image));++cases;
 clean_provider();printf("DMA_MODEL cases=%u passed=1\n",cases);return 0;
}
