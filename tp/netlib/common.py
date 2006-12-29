
# Python imports
import socket
import select
import time

# Local imports
import xstruct
import objects

from support.output import *

_continue = []

try:
	set()
except NameError:
	from sets import Set as set

class l(list):
	def __str__(self):
		return "[%s]" % ", ".join([str(i) for i in self])

class NotImplimented(Exception):
	pass

class SSLWrapper:
	def __init__(self, s):
		self.s = socket.ssl(s)

	def send(self, data):
		no = 0
		while no != len(data):
			no += self.s.write(data)

	def recv(self, amount):
		return self.s.read(amount)

from StringIO import StringIO
class StringQueue(StringIO):
	def __init__(self, *args, **kw):
		StringIO.__init__(self, *args, **kw)
		self._read_pos  = 0
		self._write_pos = 0

	def left(self):
		return self._write_pos - self._read_pos

	def read(self, *args, **kw):
		self.seek(self._read_pos)
		try:
			return StringIO.read(self, *args, **kw)
		finally:
			self._read_pos = self.tell()
			if self._read_pos > 1024*8:
				self.trim()

	def truncate(self, size=None):
		if size is None:
			size = self._read_pos

		StringIO.truncate(self, size)

		self._read_pos = 0
		self._write_pos = 0

	def trim(self):
		# Read the remaining stuff
		self.seek(self._read_pos)
		waiting = StringIO.read(self)
		self.truncate(0)
		self.write(waiting)

	def write(self, *args, **kw):
		self.seek(self._write_pos)
		try:
			return StringIO.write(self, *args, **kw)
		finally:
			self._write_pos = self.tell()

	def peek(self, amount=None):
		self.seek(self._read_pos)
		if amount is None:
			return StringIO.read(self)
		else:
			return StringIO.read(self, amount)

	def seekto(self, s):
		"""\
		Seek forward until an a string is found. 
		Return None if not found.
		"""
		pass

	def __str__(self):
		return "<StringQueue left(%i)>" % self.left()
	__repr__ = __str__

BUFFER_SIZE = 4096

class Connection:
	"""\
	Base class for Thousand Parsec protocol connections.
	Methods common to both server and client connections
	go here.
	"""
	def __init__(self):
		self.buffered = {}
		self.buffered['bytes-received'] = StringQueue()
		self.buffered['bytes-tosend']   = StringQueue()
		self.buffered['frames-received'] = {}

	def setup(self, s, nb=False, debug=False):
		"""\
		*Internal*

		Sets up the socket for a connection.
		"""
		self.s = s
		self.s.setblocking(False)

		self.setblocking(nb)
		self.debug = debug

	def fileno(self):
		"""\
		Returns the file descriptor number.
		"""
		# This is cached so our fileno doesn't go away when the socket dies..
		if not hasattr(self, "_fileno"):
			self._fileno = self.s.fileno()
		return self._fileno

	def setblocking(self, nb):
		"""\
		Sets the connection to either blocking or non-blocking.
		"""
		if not nb and self._noblock():
			# Check we arn't waiting on anything
			if len(self.nb) > 0:
				raise IOError("Still waiting on non-blocking commands!")

			del self.nb
		elif nb and not self._noblock():
			self.nb = []

	def pump(self):
		"""\
		Causes the connection to read and process stuff from the
		buffer. This will allow you to read out of band messages.

		Calling oob will also cause the connection to be pumped.
		"""
		noblock = self._noblock()
		if not noblock:
			self.setblocking(1)

		self._send()
		self._recv()

		if not noblock:
			self.setblocking(0)

	def _noblock(self):
		"""\
		*Internal*

		Returns if the connection is blocking.
		"""
		return hasattr(self, 'nb')

	def _send(self, p=None):
		"""\
		*Internal*

		Sends a single TP packet to the socket.
		"""
		buffer = self.buffered['bytes-tosend']

		if not p is None:
			if self.debug:
				green("Sending: %r\n" % p)

			buffer.write(str(p))

		try:
			sent = self.s.send(buffer.peek(BUFFER_SIZE))
		except socket.error, e:
			print "Send Socket Error", e
			sent = 0

		if self.debug and sent > 0:
			green("Sending: %s \n" % xstruct.hexbyte(buffer.peek(sent)))

		buffer.read(sent)

	def _recv(self, sequence=-1):
		"""\
		*Internal*

		Reads a single TP packet with correct sequence number from the socket.
		"""
		if not hasattr(sequence, '__getitem__'):
			sequences = set([sequence])
		else:
			sequences = set(sequence)

		buffer = self.buffered['bytes-received']
		frames = self.buffered['frames-received']
		size = objects.Header.size

		while True:
			# Pump the outgoing queue to
			self._send()

			# Return any frames we have received
			for ready in sequences.intersection(frames.keys()):
				# Cleanup any empty buffers
				if len(frames[ready]) == 0:
					del frames[ready]
					continue

				# Return the first frame
				p = frames[ready][0]
				try:
					p.process(p._data)
					del frames[ready][0]
					if self.debug:
						red("Receiving: %r\n" % p)
					return p
				except objects.DescriptionError:
					self._description_error(p)
				except Exception, e:
					self._error(p)
					del frames[ready][0]

			# Recieve any data from the wire
			try:
				data = self.s.recv(BUFFER_SIZE)
				if data == '':
					raise IOError("Socket.recv returned no data, connection must have been closed...")

				buffer.write(data)
			except socket.error, e:
				#print "Read Socket Error", e
				if not self._noblock():
					time.sleep(0.1)

			# Parse any frames we have received
			while buffer.left() >= size:
				q = objects.Header(buffer.peek(size))

				fsize = size+q.length
				if buffer.left() < fsize:
					break

				d = buffer.peek(fsize)
				red("Receiving: %s \n" % xstruct.hexbyte(d))
				q._data = d[size:]

				buffer.read(fsize)

				if not frames.has_key(q.sequence):
					frames[q.sequence] = []
				frames[q.sequence].append(q)

			if self._noblock():
				return None

	def _description_error(self, packet):
		"""\
		Called when we get a packet which hasn't be described.

		The packet will be of type Header ready to be morphed by calling
		process as follows,

		p.process(p._data)
		"""
		raise objects.DescriptionError("Can not deal with an undescribed packet.")

	def _version_error(self, h):
		"""\
		Called when a packet of the wrong version is found.

		The function should either raise the error or return a
		packet with the correct version.
		"""
		print "Version Error"
		return objects.Header(h, h[:4])

	def _error(self, packet):
		raise

	############################################
	# Non-blocking helpers
	############################################
	def poll(self):
		"""\
		Checks to see if a command can complete.
		"""
		if not self._noblock():
			raise IOError("Not a non-blocking connection!")

		ret = _continue
		while ret is _continue:
			if len(self.nb) == 0:
				return None
			func, args = self.nb[0]
			ret = func(*args)
			if ret != None:
				self.nb.pop(0)
		return ret

	def _insert(self, function, *args):
		"""\
		*Internal*

		Queues a fuction for polling before the current one.
		"""
		self.nb.insert(0, (function, args))

	def _next(self, function, *args):
		"""\
		*Internal*

		Queues a fuction for polling after the current one.
		"""
		self.nb.insert(1, (function, args))

	def _append(self, function, *args):
		"""\
		*Internal*

		Queues a fuction for polling.
		"""
		self.nb.append((function, args))

	def _pop(self):
		"""\
		*Internal*

		Removes the top of the queue.
		"""
		if self._noblock():
			self.nb.pop(0)
