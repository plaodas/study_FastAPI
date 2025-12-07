import pydantic
from pydantic import BaseModel, constr


def _pydantic_is_v2() -> bool:
    try:
        ver = tuple(int(x) for x in pydantic.__version__.split("."))
        return ver[0] >= 2
    except Exception:
        return False


class ItemCreate(BaseModel):
    name: constr(min_length=1, max_length=100)


if _pydantic_is_v2():

    class ItemRead(BaseModel):
        id: int
        name: str

        model_config = {"from_attributes": True}

else:

    class ItemRead(BaseModel):
        id: int
        name: str

        class Config:
            orm_mode = True
