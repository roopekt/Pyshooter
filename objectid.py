from typing import NewType
from random import randbytes

ObjectId = NewType("ObjectId", int)
def get_new_object_id():
    return ObjectId(int.from_bytes(randbytes(4), "big"))