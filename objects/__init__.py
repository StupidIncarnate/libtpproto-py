# Mapping to store between type numbers and classes
mapping = {}

# Constants
import constants
constants = constants

# Header
from objects.Header import Header, Processed, SetVersion, GetVersion
Header = Header
Header.mapping = mapping

Processed = Processed
SetVersion = SetVersion
GetVersion = GetVersion

# Special Description Stuff
from objects.Description import DescriptionError, Describable, Description
DescriptionError = DescriptionError
Describable = Describable
Description = Description

# Generic Responses
from objects.OK import OK
OK = OK
mapping[OK.no] = OK

from objects.Fail import Fail
Fail = Fail
mapping[Fail.no] = Fail

from objects.Sequence import Sequence
Sequence = Sequence
mapping[Sequence.no] = Sequence

# Connecting
from objects.Connect import Connect
Connect = Connect
mapping[Connect.no] = Connect

from objects.Login import Login
Login = Login
mapping[Login.no] = Login

from objects.Ping import Ping
Ping = Ping
mapping[Ping.no] = Ping

# Objects
from objects.Object_GetById import Object_GetById
Object_GetById = Object_GetById
mapping[Object_GetById.no] = Object_GetById


from objects.Object import Object
Object = Object
mapping[Object.no] = Object

from objects.Object_GetID import Object_GetID
Object_GetID = Object_GetID
mapping[Object_GetID.no] = Object_GetID

from objects.Object_GetID_ByPos import Object_GetID_ByPos
Object_GetID_ByPos = Object_GetID_ByPos
mapping[Object_GetID_ByPos.no] = Object_GetID_ByPos

from objects.Object_GetID_ByContainer import Object_GetID_ByContainer
Object_GetID_ByContainer = Object_GetID_ByContainer
mapping[Object_GetID_ByContainer.no] = Object_GetID_ByContainer

from objects.ObjectDesc import descriptions
ObjectDescs = descriptions

# Orders
from objects.OrderDesc_Get import OrderDesc_Get
OrderDesc_Get = OrderDesc_Get
mapping[OrderDesc_Get.no] = OrderDesc_Get

from objects.OrderDesc import OrderDesc, descriptions
OrderDesc = OrderDesc
OrderDescs = descriptions
mapping[OrderDesc.no] = OrderDesc

from objects.Order_Get import Order_Get
Order_Get = Order_Get
mapping[Order_Get.no] = Order_Get

from objects.Order import Order
Order = Order
mapping[Order.no] = Order

from objects.Order_Insert import Order_Insert
Order_Insert = Order_Insert
mapping[Order_Insert.no] = Order_Insert

from objects.Order_Remove import Order_Remove
Order_Remove = Order_Remove
mapping[Order_Remove.no] = Order_Remove

from objects.Order_Probe import Order_Probe
Order_Probe = Order_Probe
mapping[Order_Probe.no] = Order_Probe

## Time
from objects.TimeRemaining_Get import TimeRemaining_Get
TimeRemaining_Get = TimeRemaining_Get
mapping[TimeRemaining_Get.no] = TimeRemaining_Get

from objects.TimeRemaining import TimeRemaining
TimeRemaining = TimeRemaining
mapping[TimeRemaining.no] = TimeRemaining

## Message

from objects.Board_Get import Board_Get
Board_Get = Board_Get
mapping[Board_Get.no] = Board_Get

from objects.Board import Board
Board = Board
mapping[Board.no] = Board

from objects.Message_Get import Message_Get
Message_Get = Message_Get
mapping[Message_Get.no] = Message_Get

from objects.Message import Message
Message = Message
mapping[Message.no] = Message

from objects.Message_Insert import Message_Insert
Message_Insert = Message_Insert
mapping[Message_Insert.no] = Message_Insert

from objects.Message_Remove import Message_Remove
Message_Remove = Message_Remove
mapping[Message_Remove.no] = Message_Remove

# Design Stuff
from objects.Category_Get import Category_Get
Category_Get = Category_Get
mapping[Category_Get.no] = Category_Get

from objects.Category import Category
Category = Category
mapping[Category.no] = Category

from objects.Component_Get import Component_Get
Component_Get = Component_Get
mapping[Component_Get.no] = Component_Get

from objects.Component import Component
Component = Component
mapping[Component.no] = Component

from objects.Component import Component
Component = Component
mapping[Component.no] = Component

from objects.Component_Insert import Component_Insert
Component_Insert = Component_Insert
mapping[Component_Insert.no] = Component_Insert

from objects.Component_Remove import Component_Remove
Component_Remove = Component_Remove
mapping[Component_Remove.no] = Component_Remove
