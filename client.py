"""\
This module contains the client based connections.

Blocking Example Usage:

>>> # Create the object and connect to the server
>>> c = netlib.Connection("127.0.0.1", 6329)
>>> if failed(c.connect()):
>>>    print "Could not connect to the server"
>>>    sys.exit(1)
>>>
>>> if failed(c.login("username", "password")):
>>> 	print "Could not login"
>>> 	sys.exit(1)
>>>
>>> c.disconnect()
>>>

Non-Blocking Example Usage:

>>> # Create the object and connect to the server
>>> c = netlib.Connection("127.0.0.1", 6329, nb=1)
>>>
>>> c.connect()
>>> c.login("username", "password")
>>>
>>> # Wait for the connection to be complete
>>> if failed(c.wait()):
>>>    print "Could not connect to the server"
>>>    sys.exit(1)
>>>
>>> r = c.poll()
>>> while r == None:
>>> 	r = c.poll()
>>>
>>> 	# Do some other stuff!
>>> 	pass
>>>
>>> if failed(r):
>>> 	print "Could not login"
>>> 	sys.exit(1)
>>>
>>> # Disconnect and cleanup
>>> c.disconnect()
>>>
"""

# Python Imports
import encodings.idna
import socket
import types

# Local imports
import xstruct
import objects
constants = objects.constants

from version import version
from common import Connection, l

def failed(object):
	if type(object) == types.TupleType:
		return not object[0]
	else:
		if isinstance(object, objects.Fail):
			return True
	return False

sequence_max = 4294967296

class ClientConnection(Connection):
	"""\
	Class for a connection from the client side.
	"""

	def __init__(self, host=None, port=6923, nb=0, debug=0):
		Connection.__init__(self)

		self.buffers['undescribed'] = {}
		self.buffers['store'] = {}

		if host != None:
			self.setup(host, port, nb, debug)

		self.__desc = False

	def setup(self, host, port=6923, nb=0, debug=0, proxy=None):
		"""\
		*Internal*

		Sets up the socket for a connection.
		"""
		self.host = host
		self.proxy = None

		if host.startswith("http://") or host.startswith("https://"):

			import urllib
			opener = None

			# use enviroment varibles
			if proxy == None:
				opener = urllib.FancyURLopener()
			elif proxy == "":
				# Don't use any proxies
				opener = urllib.FancyURLopener({})
			else:
				if host.startswith("http://"):
					opener = urlib.FancyURLopener({'http': proxy})
				elif host.startswith("https://"):
					opener = urlib.FancyURLopener({'https': proxy})
				else:
					raise "URL Error..."
		
			import random, string
			url = "/"
			for i in range(0, 12):
				url += random.choice(string.letters+string.digits)
			
			o = opener.open(host + url, "")
			s = socket.fromfd(o.fileno(), socket.AF_INET, socket.SOCK_STREAM)

##			# Read in the headers
##			buffer = ""
##			while not buffer.endswith("\r\n\r\n"):
##				print "buffer:", repr(buffer)
##				try:
##					buffer += s.recv(1)
##				except socket.error, e:
##					pass
##			print "Finished the http headers..."

		else:
			if host.startswith("tp://") or host.startswith("tps://"):
				if host.count(":") > 1:
					# FIXME: Need to extract the port
					pass
				else:
					if host.startswith("tp://"):
						self.port = 6923
					elif host.startswith("tps://"):
						self.port = 6924
			else:
				self.port = port

			s = None
			for af, socktype, proto, cannoname, sa in \
					socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):

				try:
					s = socket.socket(af, socktype, proto)
					if debug:
						print "Trying to connect to connect: (%s, %s)" % (host, self.port)

					s.connect(sa)
					break
				except socket.error, msg:
					if debug:
						print "Connect fail: (%s, %s)" % (host, self.port)
					if s:
						s.close()
						
					s = None
					continue
			
			if not s:
				raise socket.error, msg

		Connection.setup(self, s, nb=nb, debug=debug)
		self.no = 1

	def _description_error(self, p):
		# Need to figure out how to do non-blocking properly...
		# Send a request for the description
		if not self.__desc:
			q = objects.OrderDesc_Get(p.sequence-1, [p.type])
			self._send(q)

			self.__desc = True
		
		q = self._recv(p.sequence-1)

		if q != None and isinstance(q, objects.Sequence):
			q = self._recv(p.sequence-1)

		if q != None and isinstance(q, objects.Description):
			self.__desc = False

			# Register the desciption
			q.register()
	
	def _common(self):
		"""\
		*Internal*

		Does all the common goodness.
		"""
		# Increase the no number
		self.no += 1

	def _okfail(self, no):
		"""\
		*Internal*

		Completes the an ok or fail function.
		"""
		p = self._recv(no)
		if not p:
			return None

		# Check it's the reply we are after
		if isinstance(p, objects.OK):
			return True, p.s
		elif isinstance(p, objects.Fail):
			return False, p.s
		else:
			# We got a bad packet
			raise IOError("Bad Packet was received")

	def _get_header(self, type, no):
		"""\
		*Internal*

		Completes the get_* function.
		"""
		p = self._recv(no)
		if not p:
			return None

		if isinstance(p, objects.Fail):
			# The whole command failed :(
			return [(False, p.s)]
		elif isinstance(p, type):
			# Must only be one, so return
			return [p]
		elif not isinstance(p, objects.Sequence):
			# We got a bad packet
			raise IOError("Bad Packet was received %s" % p)

		# We have to wait on multiple packets
		self.buffers['store'][no] = []
	
		if self._noblock():
			# Do the commands in non-blocking mode
			self._next(self._get_finish, no)
			for i in range(0, p.number):
				self._next(self._get_data, (type, no))

			# Keep the polling going
			return _continue

		else:
			# Do the commands in blocking mode
			for i in range(0, p.number):
				self._get_data(type, no)
			
			return self._get_finish(no)

	def _get_data(self, type, no):
		"""\
		*Internal*

		Completes the get_* function.
		"""
		p = self._recv(no)

		if p != None:
			if isinstance(p, objects.Fail):
				p = (False, p.s)
			elif not isinstance(p, type):
				raise IOError("Bad Packet was received %s" % p)

			self.buffers['store'][no].append(p)

			if self._noblock():
				return _continue

	def _get_finish(self, no):
		"""\
		*Internal*

		Completes the get_* functions.
		"""
		store = self.buffers['store'][no]
		del self.buffers['store'][no]

		return l(store)

	def _get_ids(self, type, key, position, amount=-1, raw=False):
		"""\
		*Internal*

		Send a GetID packet and setup for a IDSequence result.
		"""
		self._common()

		p = object.mapping[type](self.no, key, position, amount)
		self._send(p)

		if self._noblock():
			self._append(self._get_idsequence, (self.no, False, raw))
			return None
		else:
			return self._get_idsequence(self.no, False, raw)
	
	def _get_idsequence(self, no, iter=False, raw=False):
		"""\
		*Internal*

		Finishes any function which gets an IDSequence.
		"""
		p = self._recv(no)
		if not p:
			return None

		# Check it's the reply we are after
		if isinstance(p, objects.Fail):
			return False, p.s
		elif isinstance(p, objects.IDSequence):
			if iter:
				return p.iter()
			elif raw:
				return p
			else:
				return p.ids
		else:
			# We got a bad packet
			raise IOError("Bad Packet was received")

	class IDIter(object):
		"""\
		*Internal*

		Class used to iterate over an ID list. It will get more IDs as needed.
		
		On a non-blocking connection the IDIter will return (None, None) while
		no data is ready. This makes it good to use in an event loop.

		On a blocking connection the IDIter will wait till the information is
		ready.
		"""	
		def __init__(self, connection, type, amount=10):
			"""\
			IDIter(connection, type, amount=10)

			connection
				Is a ClientConnection
			type
				Is the ID of the GetID packet to send
			amount
				Is the amount of IDs to get at one time
			"""
			self.connection = connection
			self.type = type
			self.amount = amount

			self.ids = None
			self.remaining = None
			self.key = None

			# Send out a packet if we are non-blocking
			if self.connection._noblock():
				self.next()

		def next(self):
			"""\
			Get the next (ids, modified time) pair.
			"""
			# Get the first bit of information
			if self.key is None and self.remaining is None:
				if self.ids is None:
					self.ids = []
					p = self.connection._get_ids(self.type, -1, 0, 0, raw=true)
				else:
					p = self.connect.poll()
				
				# Check for Non-blocking mode
				if p is None:
					return (None, None)
				# Check for an error
				elif failed(p):
					raise IOError("Failed to get remaining IDs")

				self.remaining = p.left
				self.key = p.key
			
			# Get more IDs
			if len(self.ids) <= 0:
				no = self.remaining
				if no <= 0:
					raise StopIteration()
				elif no > self.amount:
					no = self.amount
				
				p = self.connection._get_ids(self.type, self.key, self.position, no, raw=true)
				# Check for Non-blocking mode
				if p is None:
					return (None, None)
				# Check for an error
				elif failed(p):
					raise IOError("Failed to get remaining IDs")
				
				self.ids = p.ids
				self.remaining = p.left
			
			self.position += 1	
			return self.ids.pop()

	def connect(self, str=""):
		"""\
		Connects to a Thousand Parsec Server.
		"""
		self._common()
		
		# Send a connect packet
		from version import version
		p = objects.Connect(self.no, ("libtpproto-py/%i.%i.%i " % version) + str)
		self._send(p)
		
		if self._noblock():
			self._append(self._connect, self.no)
			return None
		
		# and wait for a response
		return self._connect(self.no)

	def _connect(self, no):
		"""\
		*Internal*

		Completes the connect function, which will automatically change
		to an older version if server only supports it.
		"""
		p = self._recv([0, no])
		if not p:
			return None

		# Check it's the reply we are after
		if isinstance(p, objects.OK):
			return True, p.s
		elif isinstance(p, objects.Fail):
			if p.protocol != objects.GetVersion():
				print "Changing version."
				if objects.SetVersion(p.protocol):
					return self.connect()
			return False, p.s
		elif isinstance(p, objects.Redirect):
			self.setup(p.s, nb=self._noblock(), debug=self.debug, proxy=self.proxy)
			return self.connect()
		else:
			# We got a bad packet
			raise IOError("Bad Packet was received")

	def ping(self):
		"""\
		Pings the Thousand Parsec Server.
		"""
		self._common()
		
		# Send a connect packet
		p = objects.Ping(self.no)
		self._send(p)
		
		if self._noblock():
			self._append(self._okfail, self.no)
			return None
		
		# and wait for a response
		return self._okfail(self.no)
	
	def login(self, username, password):
		"""\
		Login to the server using this username/password.
		"""
		self._common()

		self.username = username

		p = objects.Login(self.no, username, password)
		self._send(p)
		
		if self._noblock():
			self._append(self._okfail, self.no)
			return None
		
		# and wait for a response
		return self._okfail(self.no)
	
	def get_object_ids(self, a=None, y=None, z=None, r=None, x=None, id=None, iter=False):
		"""\
		Get objects ids from the server,
		
		# Get all object ids (plus modification times)
		[(25, 10029436), ...] = get_object_ids()

		# Get all object ids (plus modification times) via an Iterator
		<Iter> = get_object_ids(iter=True)

		# Get all object ids (plus modification times) at a location
		[(25, 10029436), ..] = get_objects_ids(x, y, z, radius)
		[(25, 10029436), ..] = get_objects_ids(x=x, y=y, z=z, r=radius)

		# Get all object ids (plus modification times) at a location via an Iterator
		<Iter> = get_objects_ids(x, y, z, radius, iter=True)
		<Iter> = get_objects_ids(x=x, y=y, z=z, r=radius, iter=True)

		# Get all object ids (plus modification times) contain by an object
		[(25, 10029436), ..] = get_objects_ids(id)
		[(25, 10029436), ..] = get_objects_ids(id=id)

		# Get all object ids (plus modification times) contain by an object via an Iterator
		<Iter> = get_object_ids(id, iter=true)
		<Iter> = get_object_ids(id=id, iter=true)
		"""
		self._common()

		if a != None and y != None and z != None and r != None:
			x = a
		elif a != None:
			id = a	
	
		p = None

		if x != None:
			p = objects.Object_GetID_ByPos(self.no, x, y, z, r)
		elif id != None:
			p = objects.Object_GetID_ByContainer(self.no, id)
		else:
			if iter:
				return self.IDIter(self, objects.Object_GetID)
			
			p = objects.Object_GetID(self.no, -1, 0, -1)
		
		self._send(p)
		if self._noblock():
			self._append(self._get_idsequence, (self.no, iter))
			return None
		else:
			return self._get_idsequence(self.no, iter)

	def get_objects(self, a=None, id=None, ids=None):
		"""\
		Get objects from the server,

		# Get the object with id=25
		[<obj id=25>] = get_objects(25)
		[<obj id=25>] = get_objects(id=25)
		[<obj id=25>] = get_objects(ids=[25])
		[<obj id=25>] = get_objects([id])
		
		# Get the objects with ids=25, 36
		[<obj id=25>, <obj id=36>] = get_objects([25, 36])
		[<obj id=25>, <obj id=36>] = get_objects(ids=[25, 36])
		"""
		self._common()

		if a != None:
			if hasattr(a, '__getitem__'):
				ids = a
			else:
				id = a
		
		if id != None:
			ids = [id]
	
		p = objects.Object_GetById(self.no, ids)
		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Object, self.no))
			return None
		else:
			return self._get_header(objects.Object, self.no)

	def get_orders(self, oid, *args, **kw):
		"""\
		Get orders from an object,

		# Get the order in slot 5 from object 2
		[<ord id=2 slot=5>] = get_orders(2, 5)
		[<ord id=2 slot=5>] = get_orders(2, slot=5)
		[<ord id=2 slot=5>] = get_orders(2, slots=[5])
		[<ord id=2 slot=5>] = get_orders(2, [5])
		
		# Get the orders in slots 5 and 10 from object 2
		[<ord id=2 slot=5>, <ord id=2 slot=10>] = get_orders(2, [5, 10])
		[<ord id=2 slot=5>, <ord id=2 slot=10>] = get_orders(2, slots=[5, 10])

		# Get all the orders from object 2
		[<ord id=2 slot=5>, ...] = get_orders(2)
		"""
		self._common()

		if kw.has_key('slots'):
			slots = kw['slots']
		elif kw.has_key('slot'):
			slots = [kw['slot']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			slots = args[0]
		else:
			slots = args

		p = objects.Order_Get(self.no, oid, slots)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Order, self.no))
			return None
		else:
			return self._get_header(objects.Order, self.no)

	def insert_order(self, oid, slot, type, *args, **kw):
		"""\
		Add a new order to an object.

		Forms are
		insert_order(oid, slot, type, [arguments for order])
		insert_order(oid, slot, [Order Object])
		"""
		self._common()
		
		o = None
		if isinstance(type, objects.Order) or isinstance(type, objects.Order_Insert):
			o = type
			o._type = objects.Order_Insert.no

			o.id = oid
			o.slot = slot
			
			o.sequence = self.no
		else:	
			o = apply(objects.Order_Insert, (self.no, oid, slot, type,)+args, kw)
			
		self._send(o)

		if self._noblock():
			self._append(self._okfail, self.no)
			return None
		
		# and wait for a response
		return self._okfail(self.no)
		
	def remove_orders(self, oid, *args, **kw):
		"""\
		Removes orders from an object,

		# Remove the order in slot 5 from object 2
		[<Ok>] = remove_orders(2, 5)
		[<Ok>] = remove_objects(2, slot=5)
		[<Ok>] = remove_objects(2, slots=[5])
		[(False, "No order 5")] = remove_objects(2, [5])
		
		# Remove the orders in slots 5 and 10 from object 2
		[<Ok>, (False, "No order 10")] = remove_objects(2, [5, 10])
		[<Ok>, (False, "No order 10")] = remove_objects(2, slots=[5, 10])
		"""
		self._common()

		if kw.has_key('slots'):
			slots = kw['slots']
		elif kw.has_key('slot'):
			slots = [kw['slot']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			slots = args[0]
		else:
			slots = args

		p = objects.Order_Remove(self.no, oid, slots)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.OK, self.no))
			return None
		else:
			return self._get_header(objects.OK, self.no)

	def get_orderdescs(self, *args, **kw):
		"""\
		Get order descriptions from the server. 
		
		Note: When the connection gets an order which hasn't yet been
		described it will automatically get an order description for that
		order, you don't need to do this manually.

		# Get the order description for type 5
		[<orddesc id=5>] = get_orderdescs(5)
		[<orddesc id=5>] = get_orderdescs(type=5)
		[<orddesc id=5>] = get_orderdescs(types=[5])
		[(False, "No desc 5")] = get_orderdescs([5])
		
		# Get the order description for type 5 and 10
		[<orddesc id=5>, (False, "No desc 10")] = get_orderdescs([5, 10])
		[<orddesc id=5>, (False, "No desc 10")] = get_orderdescs(types=[5, 10])
		"""
		self._common()

		if kw.has_key('types'):
			types = kw['types']
		elif kw.has_key('type'):
			types = [kw['type']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			types = args[0]
		else:
			types = args

		p = objects.OrderDesc_Get(self.no, types)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.OrderDesc, self.no))
			return None
		else:
			return self._get_header(objects.OrderDesc, self.no)

	def time(self):
		"""\
		Gets the time till end of turn from a Thousand Parsec Server.
		"""
		self._common()
		
		# Send a connect packet
		p = objects.TimeRemaining_Get(self.no)
		self._send(p)
		
		if self._noblock():
			self._append(self._time, self.no)
			return None
		
		# and wait for a response
		return self._time(self.no)
	
	def _time(self, no):
		"""\
		*Internal*

		Completes the time function.
		"""
		p = self._recv(no)
		if not p:
			return None

		# Check it's the reply we are after
		if isinstance(p, objects.TimeRemaining):
			return True, p.time
		elif isinstance(p, objects.Fail):
			return False, p.s
		else:
			# We got a bad packet
			raise IOError("Bad Packet was received")

	def get_boards(self, x=None, id=None, ids=None):
		"""\
		Get boards from the server,

		# Get the board with id=25
		[<board id=25>] = get_boards(25)
		[<board id=25>] = get_boards(id=25)
		[<board id=25>] = get_boards(ids=[25])
		[(False, "No such board")] = get_boards([id])
		
		# Get the boards with ids=25, 36
		[<board id=25>, (False, "No board")] = get_boards([25, 36])
		[<board id=25>, (False, "No board")] = get_boards(ids=[25, 36])
		"""
		self._common()

		# Setup arguments
		if id != None:
			ids = [id]
		if hasattr(x, '__getitem__'):
			ids = x
		elif x != None:
			ids = [x]
	
		p = objects.Board_Get(self.no, ids)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Board, self.no))
			return None
		else:
			return self._get_header(objects.Board, self.no)

	def get_messages(self, bid, *args, **kw):
		"""\
		Get messages from an board,

		# Get the message in slot 5 from board 2
		[<msg id=2 slot=5>] = get_messages(2, 5)
		[<msg id=2 slot=5>] = get_messages(2, slot=5)
		[<msg id=2 slot=5>] = get_messages(2, slots=[5])
		[(False, "No such 5")] = get_messages(2, [5])
		
		# Get the messages in slots 5 and 10 from board 2
		[<msg id=2 slot=5>, (False, "No such 10")] = get_messages(2, [5, 10])
		[<msg id=2 slot=5>, (False, "No such 10")] = get_messages(2, slots=[5, 10])
		"""
		self._common()

		if kw.has_key('slots'):
			slots = kw['slots']
		elif kw.has_key('slot'):
			slots = [kw['slot']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			slots = args[0]
		else:
			slots = args

		p = objects.Message_Get(self.no, bid, slots)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Message, self.no))
			return None
		else:
			return self._get_header(objects.Message, self.no)

	def insert_message(self, bid, slot, message, *args, **kw):
		"""\
		Add a new message to an board.

		Forms are
		[<Ok>] = insert_message(bid, slot, [arguments for message])
		[(False, "Insert failed")] = insert_message(bid, slot, [Message Object])
		"""
		self._common()
		
		o = None
		if isinstance(message, objects.Message) or isinstance(message, objects.Message_Insert):
			o = message
			o._type = objects.Message_Insert.no
			o.sequence = self.no
		else:	
			o = apply(objects.Message_Insert, (self.no, bid, slot, message,)+args, kw)
			
		self._send(o)

		if self._noblock():
			self._append(self._okfail, self.no)
			return None
		
		# and wait for a response
		return self._okfail(self.no)
		
	def remove_messages(self, oid, *args, **kw):
		"""\
		Removes messages from an board,

		# Remove the message in slot 5 from board 2
		[<Ok>] = remove_messages(2, 5)
		[<Ok>] = remove_messages(2, slot=5)
		[<Ok>] = remove_messages(2, slots=[5])
		[(False, "Insert failed")] = remove_messages(2, [5])
		
		# Remove the messages in slots 5 and 10 from board 2
		[<Ok>, (False, "No such 10")] = remove_messages(2, [10, 5])
		[<Ok>, (False, "No such 10")] = remove_messages(2, slots=[10, 5])
		"""
		self._common()

		if kw.has_key('slots'):
			slots = kw['slots']
		elif kw.has_key('slot'):
			slots = [kw['slot']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			slots = args[0]
		else:
			slots = args

		p = objects.Message_Remove(self.no, oid, slots)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.OK, self.no))
			return None
		else:
			return self._get_header(objects.OK, self.no)

	def get_categories(self, *args, **kw):
		"""\
		Get category descriptions,

		# Get the description for category 5
		[<cat id=5>] = get_categories(5)
		[<cat id=5>] = get_categories(id=5)
		[<cat id=5>] = get_categories(ids=[5])
		[(False, "No such 5")] = get_categories([5])
		
		# Get the descriptions for category 5 and 10
		[<msg id=5>, (False, "No such 10")] = get_categories([5, 10])
		[<msg id=5>, (False, "No such 10")] = get_categories(ids=[5, 10])
		"""
		self._common()

		if kw.has_key('ids'):
			ids = kw['ids']
		elif kw.has_key('id'):
			ids = [kw['id']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			ids = args[0]
		else:
			ids = args

		p = objects.Category_Get(self.no, ids)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Category, self.no))
			return None
		else:
			return self._get_header(objects.Category, self.no)

	def get_components(self, *args, **kw):
		"""\
		Get components descriptions,

		# Get the description for components 5
		[<cat id=5>] = get_components(5)
		[<cat id=5>] = get_components(id=5)
		[<cat id=5>] = get_components(ids=[5])
		[(False, "No such 5")] = get_components([5])
		
		# Get the descriptions for components 5 and 10
		[<msg id=5>, (False, "No such 10")] = get_components([5, 10])
		[<msg id=5>, (False, "No such 10")] = get_components(ids=[5, 10])
		"""
		self._common()

		if kw.has_key('ids'):
			ids = kw['ids']
		elif kw.has_key('id'):
			ids = [kw['id']]
		elif len(args) == 1 and hasattr(args[0], '__getitem__'):
			ids = args[0]
		else:
			ids = args

		p = objects.Component_Get(self.no, ids)

		self._send(p)

		if self._noblock():
			self._append(self._get_header, (objects.Component, self.no))
			return None
		else:
			return self._get_header(objects.Component, self.no)

	def disconnect(self):
		"""\
		Disconnect from a server.
		"""
		if self._noblock() and len(self.nb) > 0:
			raise IOError("Still waiting on non-blocking commands!")

		self.s.close()
		del self
