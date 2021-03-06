
from xstruct import pack

from Header import Processed

class Design(Processed):
	"""\
	The Design packet consists of:
		* a SInt32, design ID
		* a SInt64, the last modified time
		* a list of,
			* a UInt32, category this design is in
		* a String, name of the design
		* a String, description of the design
		* a SInt32, number of times in use
		* a SInt32, owner of the design
		* a list of,
			* a UInt32, the ID of the component
			* a UInt32, the number of this component
		* a String, design feedback
		* a list of,
			* a UInt32, property id
			* a String, property display string
	"""
	no = 48
	struct = "jT[I]SSjj[II]S[IS]"

	def __init__(self, sequence, id, modify_time, categories, name, desc, used, owner, components, feedback, properties):
		Processed.__init__(self, sequence)

		self.id = id
		self.modify_time = modify_time
		self.categories = categories
		self.name = name
		self.desc = desc
		self.used = used
		self.owner = owner
		self.components = components
		self.feedback = feedback
		self.properties = properties
		
	def pack(self):
		output = Processed.pack(self)
		output += pack(self.struct, self.id, self.modify_time, self.categories, self.name, self.desc, self.used, self.owner, self.components, self.feedback, self.properties)
		
		return output
