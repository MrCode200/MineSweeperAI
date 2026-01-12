import time
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Literal


class Point(NamedTuple):
    x: int
    y: int


class FieldValue(Enum):
    UNDISCOVERED = -2
    FLAGGED = -1
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
    :param pos_to_screen: Pixel Position relative to screen (the center of the field)
    :param pos_to_board: Position relative to the board
    :param id: Field ID
    :param value: Field Value (Undiscovered, Flagged, Empty, One, two ...)
    """
    pos_to_screen: Point[int, int]
    pos_to_board: Point[int, int]
    id: int
    value: FieldValue = FieldValue.UNDISCOVERED

@dataclass
class GameResult:
    id: int
    result: Literal['win', 'loss']
    total_moves: int
    time_played: float