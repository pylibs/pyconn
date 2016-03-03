import pickle


class SocketWrapper(object):
    def __init__(self, manager, sock, name):
        self.manager = manager
        self.sock = sock
        self.name = name
        self.target_name = None

    def init(self):
        self.send_str(self.name)
        self.target_name = self.recv_str()

    def fileno(self):
        return self.sock.fileno()

    def _read(self, length):
        read_length = 0
        result = b''
        while read_length < length:
            data = self.sock.recv(length-read_length)
            if len(data) == 0:
                return None
            read_length += len(data)
            result += data
        return result

    def _write(self, data):
        while len(data) > 0:
            sent_length = self.sock.send(data)
            data = data[sent_length:]

    def send_int(self, val):
        data = val.to_bytes(8, 'little')
        self._write(data)

    def recv_int(self):
        data = self._read(8)
        if data is None:
            return None
        if len(data) == 0:
            return None
        return int.from_bytes(data, 'little')

    def send_str(self, string):
        string = bytes(string, 'utf8')
        self.send_int(len(string))
        self._write(string)

    def recv_str(self):
        l = self.recv_int()
        if l is None:
            return None
        string = self._read(l)
        return string.decode('utf8')

    def send_obj(self, val):
        val = pickle.dumps(val)
        self.send_int(len(val))
        self._write(val)

    def recv_obj(self):
        l = self.recv_int()
        if l is None:
            return None
        val = self._read(l)
        return pickle.loads(val)

    def close(self):
        self.sock.close()
        self.sock = None
