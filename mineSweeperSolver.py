import warnings
from pathlib import Path
from typing import Literal, Optional, Callable

import mouse
import mss
import mss.tools
from mouse import RIGHT
from pyautogui import locateCenterOnScreen, ImageNotFoundException

from models import Field, FieldValue, Point

IMAGE_DIR = Path(__file__).parent / "images"


class MineSweeperSolver:
    """
    Automated Minesweeper solver that interacts with the online Minesweeper game.

    This class uses screen capture and image recognition to play Minesweeper automatically.
    It captures the game board, analyzes field states, and makes moves by simulating mouse clicks.

    Attributes:
        DIFFICULTY_TO_SIZE: Mapping of difficulty levels to (columns, rows, mines) tuples
        SMILEY_RAD: Radius in pixels of the smiley face button
        COLOR_TO_FIELD_VALUE: Mapping of RGB colors to field values (numbers 1-8, empty, etc.)
    """

    # Board dimensions for each difficulty level (COLUMNS, ROWS, MINES)
    DIFFICULTY_TO_SIZE = {
        "beginner": (9, 9, 10),
        "intermediate": (16, 16, 40),
        "expert": (30, 16, 99)
    }

    # Smiley button dimensions (cube radius)
    SMILEY_RAD = 17

    # Pixel positions for checking game state (RELATIVE TO THE SMILEY IMG)
    DEAD_SMILEY_MOUTH_CORNER_POS = Point(8, 25)  # Position to check if game is lost
    COOL_SMILEY_GLASSES_CENTER_POS = Point(16, 11)  # Position to check if game is won

    # Offset from field center to check the upper edge color
    UNDISCOVERED_FIELD_BORDER_DY = 12

    # Color constants
    BLACK = (0, 0, 0)

    # RGB color to field value mapping
    # Each number (1-8) has a unique color, empty fields are represented by specific colors
    COLOR_TO_FIELD_VALUE = {
        (255, 255, 255): FieldValue.UNDISCOVERED,  # White upper edge = undiscovered field
        (0, 0, 255): FieldValue.ONE,  # Blue
        (0, 123, 0): FieldValue.TWO,  # Green
        (255, 0, 0): FieldValue.THREE,  # Red
        (0, 0, 123): FieldValue.FOUR,  # Dark blue
        (128, 0, 0): FieldValue.FIVE,  # Dark red
        (19, 130, 130): FieldValue.SIX,  # Teal
        (0, 0, 0): FieldValue.SEVEN,  # Black
        (123, 123, 123): FieldValue.EIGHT,  # Gray
    }

    def __init__(
            self,
            difficulty: Literal["beginner", "intermediate", "expert"] = "beginner",
            custom: Optional[tuple[int, int, int]] = None,
            play_games: int = 1,
            stop_after_win: bool = True,
    ) -> None:
        """
        Initialize the Minesweeper solver with board detection and configuration.

        This constructor locates the game board on screen, sets up board dimensions,
        and initializes all fields with their screen positions.

        :param difficulty: The difficulty level ("beginner", "intermediate", or "expert")
        :param custom: Override difficulty with custom dimensions (columns, rows, mines)
        :param play_games: Number of games to play (-1 for infinite until won)
        :param stop_after_win: Stop after winning a game
        :raises ValueError: If game elements cannot be located on screen
        """
        warnings.warn(
            "MineSweeperSolver is made to work mainly on https://minesweeperonline.com/#beginner-200"
            "\nDifficulty can be changed, however not zoom-size",
            UserWarning
        )

        # Locate key game elements on screen
        self.play_games = play_games
        self.stop_after_win = stop_after_win

        self.origin_square_pos: Point[int, int] = self.locate_image('first_field')
        self.smiley_pos: Point[int, int] = self.locate_image('happy_smiley')
        if self.origin_square_pos is None or self.smiley_pos is None:
            raise RuntimeError(
                "Failed to detect Minesweeper game window.\n"
                "Please ensure:\n"
                "1. The game window is open and visible\n"
                "2. You're using a supported version of Minesweeper\n"
                "3. The game is in a fresh/starting state\n"
                "4. The window is not minimized or covered by other windows"
            )

        # Board cell dimensions in pixels
        self.square_px_diameter = 32

        # Determine board dimensions based on difficulty or custom settings
        self.columns: int = self.DIFFICULTY_TO_SIZE[difficulty][0] if not custom else custom[0]
        self.rows: int = self.DIFFICULTY_TO_SIZE[difficulty][1] if not custom else custom[1]
        self.total_mines: int = self.DIFFICULTY_TO_SIZE[difficulty][2] if not custom else custom[2]

        # stats
        self.play_games = play_games
        self.moves_made: int = 0
        self.total_moves: int = 0
        self.wins: int = 0

        def _compute_field_positions_rel_to_board(screen_pos_x: int, screen_pos_y: int) -> Point:
            """
            Convert absolute screen coordinates to relative board image coordinates.

            This is needed because we capture the board region and need to map field positions
            to pixel coordinates within that captured image.
            """
            center_rel_to_board_img: Point = Point(
                screen_pos_x - self.origin_square_pos.x + self.square_px_rad,
                screen_pos_y - self.origin_square_pos.y + self.square_px_rad
            )
            return center_rel_to_board_img

        self.square_px_rad = int(self.square_px_diameter / 2)

        # Initialize the game board with all fields
        # Each field knows its position on screen and within the board image
        self.board: list[list[Field]] = [
            [Field(
                pos_to_screen=Point(*self.get_center_field_pos(r, c)),
                pos_to_board=_compute_field_positions_rel_to_board(*self.get_center_field_pos(r, c)),
                id=self.id_from_rc(r, c),
            ) for c in range(self.columns)]
            for r in range(self.rows)
        ]

        # Define the screen region to capture for the game board
        self.board_region = {
            "left": self.origin_square_pos.x - self.square_px_rad,
            "top": self.origin_square_pos.y - self.square_px_rad,
            "width": self.columns * self.square_px_diameter,
            "height": self.rows * self.square_px_diameter
        }

        # Define the screen region to capture for the smiley button
        self.smiley_region = {
            "left": self.smiley_pos.x - self.SMILEY_RAD,
            "top": self.smiley_pos.y - self.SMILEY_RAD,
            "width": 34,
            "height": 34
        }

        # Game statistics storage (moves played, wins/losses, etc.)
        self.game_history: dict[int, dict[str, int | bool]] = {}

        self.sct = mss.mss()

    def id_from_rc(self, row: int, col: int) -> int:
        return col + row * self.columns

    def get_center_field_pos(self, row: int, column: int) -> tuple[int, int]:
        """
        Calculate the absolute screen pixel position for the center of a field.

        :param row: The row index of the field (0-indexed)
        :param column: The column index of the field (0-indexed)
        :return: Tuple of (x, y) screen coordinates
        """
        x_screen_pos: int = int(self.origin_square_pos.x + (column * self.square_px_diameter))
        y_screen_pos: int = int(self.origin_square_pos.y + (row * self.square_px_diameter))
        return x_screen_pos, y_screen_pos

    def reset_board(self, smiley_pos: Point[int, int]):
        mouse.move(smiley_pos.x, smiley_pos.y)
        mouse.click()

        self._reset_board()
        self.moves_made = 0

    def start(self, next_move_strategy: Optional[Callable[["MineSweeperSolver"], None]] = None) -> dict[
        int, dict[str, int | bool]]:
        """
        Main game loop that plays the specified number of Minesweeper games.

        This method continuously:
        1. Makes a move
        2. Checks the game status
        3. Updates the board state or resets if game ended

        :return: Dictionary containing game history and statistics
        :raises ValueError: If smiley button cannot be located
        """
        games_completed = 0

        smiley_pos = self.locate_image('happy_smiley')
        if smiley_pos is None:
            raise ValueError("Smiley not found")

        # Main game loop
        while games_completed < self.play_games:
            next_move_strategy(self)
            self.moves_made += 1
            self.total_moves += 1

            game_status = self.check_game_status()
            match game_status:
                case 'ongoing':
                    # Game still in progress, update board state
                    self._update_board()

                case 'lost':
                    games_completed += 1
                    self.reset_board(smiley_pos)
                    print(f"{games_completed}'s Game Lost ( ´･･)ﾉ(._.`), Restarting... ")

                case 'won':
                    games_completed += 1
                    self.wins += 1
                    print(f"{games_completed}'s Game Won, Congrats (〃￣︶￣)人(￣︶￣〃)")

                    if self.stop_after_win:
                        return self.game_history
                    self.reset_board(smiley_pos)

    # --- Static Utility Methods ---
    @staticmethod
    def click_field(field: Field):
        # Get the screen coordinates of the chosen field
        click_x, click_y = field.pos_to_screen

        # Move mouse to the field and click it
        mouse.move(click_x, click_y)
        mouse.click()

    @staticmethod
    def toggle_flag(field: Field):
        field.value = FieldValue.FLAGGED if field.value != FieldValue.FLAGGED else FieldValue.UNDISCOVERED

        # Get the screen coordinates of the chosen field
        click_x, click_y = field.pos_to_screen

        # Move mouse to the field and click it
        mouse.move(click_x, click_y)
        mouse.click(RIGHT)

    # -------------------------------

    def _update_board(self):
        """
        Capture the current game board and update internal field states.

        This method:
        1. Takes a screenshot of the board region
        2. Analyzes each undiscovered field by checking pixel colors
        3. Updates field values based on colors (numbers, empty, etc.)

        Color detection works by checking:
        - Edge color to see if field is still undiscovered
        - Center color to determine the number or if it's empty
        """
        # Capture the current board state from screen
        board_screenshot = self.sct.grab(self.board_region)
        # Optional: Save screenshot for debugging
        # mss.tools.to_png(board_screenshot.rgb, board_screenshot.size, output="screenshot.png")

        undiscovered_fields = [
            field for row in self.board
            for field in row
            if field.value == FieldValue.UNDISCOVERED
        ]

        for field in undiscovered_fields:
            # Check the upper edge color to see if field is still covered
            edge_color: tuple[int, int, int] = board_screenshot.pixel(
                field.pos_to_board.x,
                field.pos_to_board.y - self.UNDISCOVERED_FIELD_BORDER_DY
            )

            # If edge is still white/undiscovered color, skip this field
            if MineSweeperSolver.COLOR_TO_FIELD_VALUE.get(edge_color, None) == FieldValue.UNDISCOVERED:
                continue

            center_color: tuple[int, int, int] = board_screenshot.pixel(
                field.pos_to_board.x,
                field.pos_to_board.y
            )

            field.value = MineSweeperSolver.COLOR_TO_FIELD_VALUE.get(
                center_color,
                FieldValue.EMPTY
            )

    @staticmethod
    def locate_image(
            image_name: Literal['cool_smiley', 'dead_smiley', 'first_field', 'happy_smiley'],
            region: Optional[dict[str, int]] = None
    ) -> Point | None:
        """
        Find an image on the screen and return its center position.

        Uses template matching to locate specific game elements like the smiley button
        or the first field of the board.

        :param image_name: Name of the image to locate (from images/ folder)
        :param region: Optional screen region to search within
                      {"left": int, "top": int, "width": int, "height": int}
        :return: Point(x, y) of the image center, or None if not found
        """
        try:
            image_path = str(IMAGE_DIR / f"{image_name}.png")

            center_position = locateCenterOnScreen(image_path, region=region)
            return center_position
        except ImageNotFoundException:
            return None

    def check_game_status(self) -> Literal['won', 'lost', 'ongoing']:
        """
        Determine the current game state by analyzing the smiley button.

        The smiley face changes based on game state:
        - Happy smiley (😊) → Game ongoing
        - Dead smiley (😵) → Game lost (hit a mine)
        - Cool smiley (😎) → Game won!

        Detection works by checking specific pixels on the smiley image:
        - Dead: Check mouth corner for black pixel
        - Cool: Check glasses center for black pixel

        :return: 'won' if game is won, 'lost' if hit a mine, 'ongoing' if still playing
        """
        smiley_screenshot = self.sct.grab(self.smiley_region)

        dead_smiley_pixel = smiley_screenshot.pixel(*self.DEAD_SMILEY_MOUTH_CORNER_POS)
        if dead_smiley_pixel == self.BLACK:
            return 'lost'

        cool_smiley_pixel = smiley_screenshot.pixel(*self.COOL_SMILEY_GLASSES_CENTER_POS)
        if cool_smiley_pixel == self.BLACK:
            return 'won'

        return 'ongoing'

    def log_game(self):
        """
        Log game statistics and history (not yet implemented).

        Intended to track:
        - Move order and sequence
        - Number of moves made
        - Game result (won/lost)
        - Time to completion
        """
        ...

    def _reset_board(self):
        """
        Reset the internal board state after a game ends.

        This resets all fields to undiscovered state, preparing for a new game.
        Called after clicking the smiley button to restart.
        """
        undiscovered_val = FieldValue.UNDISCOVERED

        for row in self.board:
            for field in row:
                field.value = undiscovered_val


if __name__ == '__main__':
    import random
    from line_profiler import LineProfiler


    def next_move(solver: MineSweeperSolver):
        undiscovered_fields = [
            field for row in solver.board
            for field in row
            if field.value == FieldValue.UNDISCOVERED
        ]

        if undiscovered_fields:
            chosen_field = random.choice(undiscovered_fields)

            solver.click_field(chosen_field)


    ms_solver = MineSweeperSolver(
        difficulty="beginner",
        play_games=260,
    )

    # Option 1: Run normally
    # solver.start()

    # Option 2: Run with profiling to analyze performance

    profiler = LineProfiler()
    profiler.add_class(cls=MineSweeperSolver)

    profiler.run('ms_solver.start(next_move_strategy=next_move)')
    profiler.print_stats(output_unit=1.0)
