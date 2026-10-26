"""A temporary loopback-only CONNECT relay for verified APK repositories."""
import http.server,select,socket
allowed={'mirror.postmarketos.org','dl-cdn.alpinelinux.org','mirror.nura.eco'}
class Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_CONNECT(self):
        host,sep,port=self.path.rpartition(':')
        if not sep or host not in allowed or port!='443':
            self.send_error(403);return
        try:upstream=socket.create_connection((host,443),timeout=15)
        except OSError:self.send_error(502);return
        self.send_response(200);self.end_headers()
        peers=[self.connection,upstream]
        try:
            while True:
                ready,_,_=select.select(peers,[],[],60)
                if not ready:return
                for source in ready:
                    data=source.recv(65536)
                    if not data:return
                    peers[source is self.connection].sendall(data)
        except (OSError,TimeoutError):pass
        finally:upstream.close()
server=http.server.ThreadingHTTPServer(('127.0.0.1',18081),Proxy)
print('APK_ALLOWLIST_PROXY_READY_ON_LOOPBACK',flush=True)
server.serve_forever()
