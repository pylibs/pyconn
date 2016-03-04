import logging
import queue
import time
import unittest

from pyconn.manager import ConnectionManager
from pyconn.message import Message

class BasicTests(unittest.TestCase):
    def setUp(self):
        self.cm1 = ConnectionManager(name='remote', enable_listener=True)
        self.cm1.start()
        self.cm2 = ConnectionManager(name='local')
        self.cm2.start()

    def tearDown(self):
        self.cm1.stop()
        self.cm2.stop()

    def test_connect(self):
        conn = self.cm2.connect('localhost', 12222)
        self.assertNotEqual(conn, None)
        m = Message(target='remote', data='Hello world')
        self.cm2.send(m)
        rm = self.cm1.get_queue('main').get(timeout=10)
        self.assertEqual(rm.data, 'Hello world')
        self.assertEqual(rm._id, m._id)
        repmsg = rm.create_reply(data='Hello to you too!')
        self.cm1.send(repmsg)
        rm = self.cm2.get_queue('main').get(timeout=10)
        self.assertEqual(rm.data, 'Hello to you too!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(name)-24s %(threadName)-12s %(message)s')
    unittest.main()
