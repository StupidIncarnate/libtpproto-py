
from xstruct import pack
from objects import Order

class Move(Order):
	"""\
	Move to a place in space.
	"""
	subtype = 1
	substruct = "qqq"

	def __init__(self, sequence, \
					id,	type, slot, turns, resources, \
					x, y, z):
		Order.__init__(self, sequence, \
					id, type, slot, turns, resources,
					x, y, z)

		self.length += 3*8
		self.pos = (x, y, z)

	def __repr__(self):
		output = Order.__repr__(self)
		output += pack(self.substruct, self.pos[0], self.pos[1], self.pos[2])

		return output