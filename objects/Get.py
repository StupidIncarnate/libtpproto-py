
from xstruct import pack

from Header import Processed

class Get(Processed):
	"""\
	Base class for getting stuff by ID.
	
	Used by:
		* ObjectDesc_Get
		* OrderDesc_Get
		* Object_GetById
	"""
	
	struct = "[j]"

	def __init__(self, sequence, ids):
		Processed.__init__(self, sequence)

		# Length is:
		#  * 4 bytes (uint32 - id)
		#
		self.length = 4 + 4 * len(ids)

		self.ids = ids
	
	def __repr__(self):
		output = Processed.__repr__(self)
		output += pack(self.struct, self.ids)

		return output
		
class GetSlot(Processed):
	"""\
	Base class for getting stuff by ID and slot.
	"""
	
	struct = "I[j]"

	def __init__(self, sequence, id, slots):
		Processed.__init__(self, sequence)

		# Length is:
		#  * 4 bytes (uint32 - id)
		#
		self.length = 4 + 4 + 4 * len(slots)
	
		self.id = id
		self.slots = slots
	
	def __repr__(self):
		output = Processed.__repr__(self)
		output += pack(self.struct, self.id, self.slots)

		return output
