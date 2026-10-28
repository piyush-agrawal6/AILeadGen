"""Public-network-only proxy for Chromium subresources, including CONNECT tunnels."""
import select
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from app.utils.urls import is_safe_ip


def public_socket(host, port):
    if port not in (80,443):
        raise ValueError("Non-web port blocked")
    addresses = socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    if not addresses or any(not is_safe_ip(item[4][0]) for item in addresses):
        raise ValueError("Non-public browser destination blocked")
    sock = socket.socket(addresses[0][0],socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect(addresses[0][4])
        return sock
    except Exception:
        sock.close()
        raise


class _Proxy(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8
    slots = threading.BoundedSemaphore(12)


class _Handler(BaseHTTPRequestHandler):
    timeout = 10
    protocol_version = "HTTP/1.1"

    def log_message(self,*args):
        pass

    def _tunnel(self, remote):
        transferred=0
        while transferred < 20_000_000:
            ready,_,_=select.select([self.connection,remote],[],[],10)
            if not ready: break
            for current in ready:
                data=current.recv(65536)
                if not data: return
                transferred+=len(data)
                (remote if current is self.connection else self.connection).sendall(data)

    def do_CONNECT(self):
        if not self.server.slots.acquire(blocking=False):
            self.send_error(429);return
        try:
            parsed=urlsplit("https://"+self.path)
            if parsed.port != 443 or parsed.username or parsed.password:
                raise ValueError("Invalid tunnel")
            with public_socket(parsed.hostname,443) as remote:
                self.send_response(200);self.end_headers()
                self._tunnel(remote)
        except Exception:
            self.close_connection=True
        finally:
            self.server.slots.release()

    def do_GET(self):
        if not self.server.slots.acquire(blocking=False):
            self.send_error(429);return
        try:
            parsed=urlsplit(self.path)
            if parsed.scheme != "http" or parsed.username or parsed.password or parsed.port not in (None,80):
                raise ValueError("Invalid proxy request")
            with public_socket(parsed.hostname,80) as remote:
                target=parsed.path or "/"
                if parsed.query: target+="?"+parsed.query
                headers="".join(f"{key}: {value}\r\n" for key,value in self.headers.items() if key.lower() not in ["proxy-authorization","proxy-connection","connection"])
                remote.sendall(f"GET {target} HTTP/1.1\r\n{headers}Connection: close\r\n\r\n".encode("latin1"))
                self._tunnel(remote)
        except Exception:
            self.close_connection=True
        finally:
            self.server.slots.release()


@contextmanager
def public_browser_proxy():
    server=_Proxy(("127.0.0.1",0),_Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown();server.server_close()
