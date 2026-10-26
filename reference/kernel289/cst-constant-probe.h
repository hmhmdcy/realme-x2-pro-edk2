/* SPDX-License-Identifier: GPL-2.0-only */
static uint32_t cst_saved[12];static bool cst_saved_valid;
static void cst_probe_set(bool high)
{
 if(!cst_saved_valid){for(unsigned i=0;i<12;i++)cst_saved[i]=mmio_read(gamma_base,0xf30+i*4);cst_saved_valid=true;}
 for(unsigned row=0;row<3;row++){
  mmio_write(gamma_base,0xf30+16*row,0);mmio_write(gamma_base,0xf34+16*row,0);
  mmio_write(gamma_base,0xf38+16*row,high?512u<<16:512u);mmio_write(gamma_base,0xf3c+16*row,1023u<<16);
 }
 mmio_write(gamma_base,0x4ac,1);printf("CST_CONSTANT offset_field=%s value=512 coefficients=zero\n",high?"high":"low");fflush(stdout);
}
static void cst_probe_restore(void)
{
 if(!cst_saved_valid||!gamma_base)return;
 for(unsigned i=0;i<12;i++)mmio_write(gamma_base,0xf30+i*4,cst_saved[i]);mmio_write(gamma_base,0x4ac,1);
 bool equal=true;for(unsigned i=0;i<12;i++)equal&=mmio_read(gamma_base,0xf30+i*4)==cst_saved[i];
 printf("CST_RESTORE registers=%d\n",equal);cst_saved_valid=false;
}
