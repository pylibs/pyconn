import logging
import queue
import select, socket
import threading, time
import uuid

from .wrapper import SocketWrapper

# constants
DEFAULT_BACKLOG = 5
DEFAULT_TIMEOUT = 0.5

DEFAULT_LISTEN_HOST = '127.0.0.1'
DEFAULT_LISTEN_PORT = 12222


# Connection manager takes care of all sockets, listeners and connections.
class ConnectionManager(object):
    def __init__(self, **kwargs):
        # properties
        self.name = kwargs.pop('name', str(uuid.uuid4()))
        self.listener_enabled = kwargs.pop('enable_listener', False)
        self.timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT)

        # List of accepted sockets
        self.remote_sockets = []
        self.remote_sockets_dict = {}
        self.remote_sockets_rdict = {}

        # List of locally created sockets
        self.local_sockets = []
        self.local_sockets_dict = {}
        self.local_sockets_rdict = {}

        self.sockets_dict = {}

        # Listener
        self.listen_socket = None
        if self.listener_enabled:
            self.listen_host = kwargs.pop('listen_host', DEFAULT_LISTEN_HOST)
            self.listen_port = kwargs.pop('listen_port', DEFAULT_LISTEN_PORT)
            self.listen_backlog = kwargs.pop('listen_backlog', DEFAULT_BACKLOG)

        self.queues = {}
        self.send_queue = queue.Queue()
        self.logger = logging.getLogger('ConnectionManager/' + self.name)

        self.accept_thread = None
        self.receive_thread = None
        self.send_thread = None

        self.active = False
        self.initialized = False

    def init(self):
        self.logger.info('Initializing connection manager.')
        if self.listener_enabled:
            try:
                self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listen_socket.bind((self.listen_host, self.listen_port))
                self.listen_socket.listen(self.listen_backlog)
                self.listen_socket.settimeout(self.timeout)
                self.logger.info('Created listener [%s] successfully.' % self.name)
            except Exception as e:
                self.logger.error('Could not create listener due to the exception [%s]' % str(e))
                self.initialized = False
                return
        self.initialized = True

    def deinit(self):
        self.logger.info('De-initializing connection manager.')

        if self.accept_thread is not None:
            self.accept_thread.join()
            self.accept_thread = None

        if self.listener_enabled:
            if self.listen_socket is not None:
                try:
                    self.listen_socket.shutdown(socket.SHUT_RD)
                except:
                    self.logger.warning('Shutdown on listener socket raised an exception.')
                self.listen_socket.close()

        if self.receive_thread is not None:
            self.receive_thread.join()

        if self.send_thread is not None:
            self.send_thread.join()

    def start(self):
        self.init()
        if not self.initialized:
            self.deinit()
            return

        self.active = True
        if self.listener_enabled:
            self.accept_thread = threading.Thread(target=self.accept_loop, name='AcceptLoop')
            self.accept_thread.start()

        self.receive_thread = threading.Thread(target=self.receive_loop, name='ReceiveLoop')
        self.receive_thread.start()

        self.send_thread = threading.Thread(target=self.send_loop, name='SendLoop')
        self.send_thread.start()

    def stop(self):
        self.active = False
        self.deinit()

    def connect(self, host=DEFAULT_LISTEN_HOST, port=DEFAULT_LISTEN_PORT):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock = SocketWrapper(self, sock, self.name)
            sock.init()
            self.sockets_dict[sock.target_name] = sock
            self.local_sockets.append(sock)
        except Exception as e:
            pass

        return sock

    def send(self, message):
        if message.source is None:
            message.source = self.name
        self.send_queue.put(message)

    def get_queue(self, qname):
        return self.queues.setdefault(qname, queue.Queue())

    # Threads
    def accept_loop(self):
        while self.active:
            try:
                sock, addr = self.listen_socket.accept()
                sock = SocketWrapper(self, sock, self.name)
                sock.init()
                self.remote_sockets.append(sock)
                self.sockets_dict[sock.target_name] = sock
            except socket.timeout:
                pass  # This is expected

    def send_loop(self):
        while self.active:
            try:
                message = self.send_queue.get(timeout=self.timeout)
                sock = self.sockets_dict.get(message.target, None)
                if sock is None:
                    self.logger.error('Could not find connected target [%s]' % message.target)
                else:
                    sock.send_obj(message)
            except queue.Empty:
                pass  # This is expected

    def receive_loop(self):
        while self.active:
            sockets = self.local_sockets + self.remote_sockets
            if len(sockets) == 0:
                time.sleep(self.timeout)
            else:
                try:
                    rlist, wlist, xlist = select.select(sockets, [], sockets, self.timeout)
                except Exception as e:
                    self.logger.warning(str(e))
                    continue
                if len(rlist) > 0 or len(xlist) > 0:
                    for sock in (rlist + xlist):
                        self.handle_receive(sock)

    def handle_receive(self, sock):
        try:
            message = sock.recv_obj()
        except OSError:
            message = None
        if message is None:
            if sock in self.remote_sockets:
                self.remote_sockets.remove(sock)
            elif sock in self.local_sockets:
                self.local_sockets.remove(sock)
                self.sockets_dict.pop(sock.name)
            sock.close()
            return

        self.get_queue(message.target_qname).put(message)
