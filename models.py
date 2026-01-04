from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


class Point(NamedTuple):
    x: int
    y: int


class FieldValue(Enum):
    UNDISCOVERED = -1
    EMPTY = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8


@dataclass(slots=True)
class Field:
    """
    Pos is the absolute position on screen
    field_id is the number of the field, counted from vertical to horizontal
    safe   a flag to identify if the Field contains a Bomb logically or not
    """
    pos_to_screen: Point[int, int]
    pos_to_board: Point[int, int]
    field_id: int
    value: FieldValue = FieldValue.UNDISCOVERED
    safe: bool = False
