# PyConn

PyConn is a TCP connection manager, which provides an easy interface to manage listeners and connected sockets, and also a message based communication framework.

### Installation
From the repository:

    pip install git+https://github.com/pylibs/pyconn.git

or, from the code:

    python setup.py install


### Usage
Use the connection manager.

    from pyconn.manager import ConnectionManager
    cm = ConnectionManager(name=<appname>, enable_listener=<True or False>, listen_host=<host>, listen_port=<port>)
    cm.start()
    # ...
    cm.stop()

Connect to targets.

    cm.connect(<host>, <port>)

Once connection has been made, communication can be done using the target app name.

    from pyconn.message import Message
    msg = Message(source_qname=<origin queue name>,
                  target=<target app name>,
                  target_qname=<queue name in the target>,
                  data=<data to be sent>)
    cm.send(msg)

Note: The data must be serializable using pickle.

Data on the other end can be received using the queue from connection manager.

    queue = cm.get_queue('<queue name>')
    queue.get()

### Questions?
Mail me at sattvik@gmail.com
