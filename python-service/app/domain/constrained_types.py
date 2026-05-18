from typing import Annotated
from pydantic import Field

Percentage = Annotated[float, Field(ge=0, le=100)]
