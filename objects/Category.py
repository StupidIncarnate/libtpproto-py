
from xstruct import pack

from Header import Processed

class Category(Processed):
	"""\
	The Category packet consists of:
	    * a UInt32, Category ID
	    * a String, name of the category
    	* a String, description of the category
	"""
	no = 30
	struct = "ISS"

	def __init__(self, sequence, id, name, desc):
		Processed.__init__(self, sequence)

		# Length is:
		#
		self.length = 4 + \
				4 + len(name) + 1 + \
				4 + len(desc) + 1

		self.id = id
		self.name = name
		self.desc = desc
	
	def __repr__(self):
		output = Processed.__repr__(self)
		output += pack(self.struct, self.id, self.name, self.desc)

		return output