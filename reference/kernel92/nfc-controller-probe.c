/* Generic netlink only: GET_DEVICE, DEV_UP, GET_DEVICE, DEV_DOWN.
 * No firmware download, secure-element operations, polling, or tag exchange.
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <linux/nfc.h>
#include <netlink/netlink.h>
#include <netlink/genl/genl.h>
#include <netlink/genl/ctrl.h>
static struct nl_sock *sock;
static int family;
static int show(struct nl_msg *msg, void *arg)
{
    (void)arg;struct nlmsghdr *hdr=nlmsg_hdr(msg);
    struct genlmsghdr *gh=nlmsg_data(hdr);struct nlattr *a[NFC_ATTR_MAX+1]={0};
    if(nla_parse(a,NFC_ATTR_MAX,genlmsg_attrdata(gh,0),genlmsg_attrlen(gh,0),NULL))return NL_STOP;
    printf("device index=%u name=%s protocols=0x%x powered=%u\n",
        a[NFC_ATTR_DEVICE_INDEX]?nla_get_u32(a[NFC_ATTR_DEVICE_INDEX]):~0U,
        a[NFC_ATTR_DEVICE_NAME]?nla_get_string(a[NFC_ATTR_DEVICE_NAME]):"?",
        a[NFC_ATTR_PROTOCOLS]?nla_get_u32(a[NFC_ATTR_PROTOCOLS]):0,
        a[NFC_ATTR_DEVICE_POWERED]?nla_get_u8(a[NFC_ATTR_DEVICE_POWERED]):0);
    return NL_OK;
}
static int cmd(int op)
{
    struct nl_msg *m=nlmsg_alloc(); if(!m)exit(2);
    if(!genlmsg_put(m,NL_AUTO_PORT,NL_AUTO_SEQ,family,0,NLM_F_ACK,op,NFC_GENL_VERSION))exit(2);
    if(nla_put_u32(m,NFC_ATTR_DEVICE_INDEX,0))exit(2);
    int r=nl_send_auto(sock,m);nlmsg_free(m);
    if(r>=0)r=nl_recvmsgs_default(sock);
    printf("nfc command=%d result=%d %s\n",op,r,r<0?nl_geterror(r):"OK");fflush(stdout);return r;
}
int main(void)
{
    alarm(30);sock=nl_socket_alloc(); if(!sock)return 2;
    if(genl_connect(sock))return 2;family=genl_ctrl_resolve(sock,NFC_GENL_NAME);if(family<0)return 2;
    nl_socket_modify_cb(sock,NL_CB_VALID,NL_CB_CUSTOM,show,NULL);
    int r=cmd(NFC_CMD_GET_DEVICE);
    if(r>=0) {r=cmd(NFC_CMD_DEV_UP); if(r>=0){r=cmd(NFC_CMD_GET_DEVICE);int down=cmd(NFC_CMD_DEV_DOWN);if(down<0)r=down;}}
    nl_socket_free(sock);return r<0?1:0;
}
