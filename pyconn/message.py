import uuid


class Message(object):
    def __init__(self, **kwargs):
        self._id = uuid.uuid4()
        self.source = kwargs.pop('source', None)
        self.source_qname = kwargs.pop('source_qname', 'main')
        self.target = kwargs.pop('target', None)
        self.target_qname = kwargs.pop('target_qname', 'main')
        self.data = kwargs.pop('data', None)

    def create_reply(self, data):
        reply = Message(source=self.target, source_qname=self.target_qname,
            target=self.source, target_qname=self.source_qname, data=data)
        reply._orig_id = self._id
        return reply
