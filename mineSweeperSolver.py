import time
import warnings
from itertools import groupby
from pathlib import Path
from typing import Literal, Optional, Callable

import keyboard
import mouse
import mss
import mss.tools
from mouse import RIGHT
from pyautogui import locateCenterOnScreen, ImageNotFoundException

from models import Field, FieldValue, Point, GameResult

IMAGE_DIR = Path(__file__).parent / "images"


class MineSweeperSolver:
    """
    Automated Minesweeper solver that interacts with the online Minesweeper game.

    This class uses screen capture and image recognition to play Minesweeper automatically.
    It captures the game board, analyzes field states, and makes moves by simulating mouse clicks.

    Attributes:
        DIFFICULTY_TO_SIZE: Mapping of difficulty levels to (columns, rows, mines) tuples
        SMILEY_RAD: Radius in pixels of the smiley face button
        COLOR_MAP: Mapping of RGB colors to field values (numbers 1-8, empty, etc.)
    """

    # Board dimensions for each difficulty level (COLUMNS, ROWS, MINES)
    DIFFICULTY_TO_SIZE = {
        "beginner": (9, 9, 10),
        "intermediate": (16, 16, 40),
        "expert": (30, 16, 99)
    }

    # Smiley button dimensions (cube radius)
    SMILEY_RAD = 17
    FIELD_DIAMETER = 32

    # Offset from field center to check the upper edge color
    FIELD_BORDER_OFFSET = 12

    # Pixel positions for checking game state (RELATIVE TO THE SMILEY IMG)
    DEAD_SMILEY_MOUTH_CORNER_POS = Point(8, 25)  # Position to check if game is lost
    COOL_SMILEY_GLASSES_CENTER_POS = Point(16, 11)  # Position to check if game is won

    # Color constants
    BLACK = (0, 0, 0)

    # RGB to field value mapping
    COLOR_MAP = {
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
        Initialize the solver and detect the game board on screen.

        Args:
            difficulty: Game difficulty level
            custom: Custom dimensions (columns, rows, mines) to override difficulty
            play_games: Number of games to play
            stop_after_win: Whether to stop after first win

        Raises:
            RuntimeError: If game elements cannot be detected on screen
        """
        warnings.warn(
            "MineSweeperSolver works best with https://minesweeperonline.com/#beginner-200-left\n"
            "Difficulty can be changed, but not zoom or side position",
            UserWarning
        )
        # Locate game elements
        self.origin_field_pos = self._locate_image('first_field')
        self.smiley_pos = self._locate_image('happy_smiley')

        if not self.origin_pos or not self.smiley_pos:
            raise RuntimeError(
                "Failed to detect Minesweeper game window.\n"
                "Ensure:\n"
                "1. Game window is open and visible\n"
                "2. Using a supported Minesweeper version\n"
                "3. Game is in starting state\n"
                "4. Window is not minimized or obscured"
            )
        # Board configuration
        size = custom if custom else self.DIFFICULTY_TO_SIZE[difficulty]
        self.columns, self.rows, self.total_mines = size
        field_radius = self.FIELD_DIAMETER // 2

        # Game settings
        self.play_games = play_games
        self.stop_after_win = stop_after_win

        # Statistics tracking
        self.moves_made = 0
        self.total_moves = 0
        self.best_win_moves = self.rows * self.columns + 1
        self.game_history: list[GameResult] = []

        # Initialize the game board with all fields
        # Each field knows its position on screen and within the board image
        self.board: list[list[Field]] = self._initialize_game_board(field_radius)

        # Define screen regions for capture
        self.board_region = {
            "left": self.origin_field_pos.x - field_radius,
            "top": self.origin_field_pos.y - field_radius,
            "width": self.columns * self.FIELD_DIAMETER,
            "height": self.rows * self.FIELD_DIAMETER
        }
        self.smiley_region = {
            "left": self.smiley_pos.x - self.SMILEY_RAD,
            "top": self.smiley_pos.y - self.SMILEY_RAD,
            "width": 34,
            "height": 34
        }

        # Game statistics storage (moves played, wins/losses, etc.)
        self.stats: dict[int, dict[str, int | bool]] = {}

        self.sct = mss.mss()

    def _initialize_game_board(self, field_radius: int):
        def _compute_field_positions_rel_to_board(screen_pos_x: int, screen_pos_y: int) -> Point:
            """
            Convert absolute screen coordinates to relative board image coordinates.

            This is needed because we capture the board region and need to map field positions
            to pixel coordinates within that captured image.
            """
            center_rel_to_board_img: Point = Point(
                screen_pos_x - self.origin_field_pos.x + field_radius,
                screen_pos_y - self.origin_field_pos.y + field_radius
            )
            return center_rel_to_board_img

        return [
            [Field(
                pos_to_screen=Point(*self._get_center_field_pos(r, c)),
                pos_to_board=_compute_field_positions_rel_to_board(*self._get_center_field_pos(r, c)),
                id=self.id_from_rc(r, c),
            ) for c in range(self.columns)]
            for r in range(self.rows)
        ]

    def id_from_rc(self, row: int, col: int) -> int:
        return col + row * self.columns

    def _get_center_field_pos(self, row: int, column: int) -> tuple[int, int]:
        """
        Calculate the absolute screen pixel position for the center of a field.

        :param row: The row index of the field (0-indexed)
        :param column: The column index of the field (0-indexed)
        :return: Tuple of (x, y) screen coordinates
        """
        x_screen_pos: int = int(self.origin_field_pos.x + (column * self.FIELD_DIAMETER))
        y_screen_pos: int = int(self.origin_field_pos.y + (row * self.FIELD_DIAMETER))
        return x_screen_pos, y_screen_pos

    def start(
            self,
            next_move_strategy: Optional[Callable[["MineSweeperSolver"], None]],
            user_enters_username: bool = True,
            window_size: Optional[int] = None
    ) -> dict[str, any]:
        """
            Execute the interactive Minesweeper solver loop until the configured number
            of games has been completed, tracking performance along the way.

            The solver repeatedly:
              1. Chooses a move (by calling next_move_strategy or internal logic)
              2. Applies that move to the Minesweeper board
              3. Detects win/loss state
              4. Records game results and resets the board between rounds

            When all iterations are finished, the function returns a summary containing:
              - Per-game history (inputs, moves, results)
              - Aggregate statistics computed by `create_stats`

            Return dictionary structure:
            {
                "history": list[GameResult]
                    Ordered sequence of game objects, one per completed board.

                "stats": dict
                    The statistics dictionary returned by create_stats(), including:
                    total games, wins/losses, win rate, streaks, move totals and averages,
                    and placeholders for timing and consistency.
            }

            :param next_move_strategy:
                Optional callback invoked each cycle to determine what move the solver should take.
                If None, the solver must implement its own selection heuristic.

            :param user_enters_username:
                If True, waits for user input after a win so the user can declare a username
                (for scoreboards, logging, or UI). If False, execution proceeds automatically.

            :param window_size:
                Window size for calculating rolling consistency. If None, it is automatically chosen
                as max(games_completed // 30, 3) to ensure a meaningful number of windows.

            :return:
                Dictionary with keys 'history' and 'stats'. These represent raw per-game data
                and processed metrics, respectively.
                For more information, check the docstring of MineSweeperSolver.create_stats out.

            :raises ValueError:
                If UI navigation fails (example: failed to detect smiley/reset controls).
            """
        if user_enters_username and not self.stop_after_win:
            raise AttributeError("user_enters_username = True only works if stop_after_win = True")
        if user_enters_username:
            warnings.warn(
                "This may falsify the statistics, as the last game will only end, "
                "after the user has entered their Username."
                "Meanwhile the solver continues to run in the background..."
            )

        games_completed = 0
        game_start_time = None
        last_game_status = ""

        smiley_pos = self._locate_image('happy_smiley')
        if smiley_pos is None:
            raise ValueError("Smiley not found")

        # Main game loop
        while games_completed < self.play_games:
            status = self.check_game_status()
            if status == 'ongoing' and last_game_status != 'ongoing':
                game_start_time = time.time()

            # Prevent double-counting due to timing (the solver is too fast hehehe...)
            if status == last_game_status and status != 'ongoing':
                continue
            last_game_status = status

            next_move_strategy(self)
            self.moves_made += 1
            self.total_moves += 1

            # In case you beat highscore press 'esc' to be able to view new status
            if not user_enters_username:
                keyboard.press('esc')

            # --- status logic ---
            if status == 'ongoing':
                self._update_board()
                continue

            games_completed += 1
            game_duration = time.time() - game_start_time if game_start_time else 0
            self._log_game(game_id=games_completed, game_result='win', game_duration=game_duration)
            game_start_time = 0
            self.moves_made = 0

            if status == 'loss':
                print(f"{games_completed}'s Game Lost ( ´･･)ﾉ(._.`), Restarting... ")

            elif 'win':
                print(
                    f"{games_completed}'s Game Won in {game_duration:.2f} seconds, in {self.moves_made} moves."
                    f"\nCongrats (〃￣︶￣)人(￣︶￣〃)"
                )

                self.best_win_moves = min(self.moves_made, self.best_win_moves)
                if self.stop_after_win:
                    break

            self.reset_board(smiley_pos)

        return self.create_stats(games_completed, window_size)

    def reset_board(self, smiley_pos: Point[int, int]):
        mouse.move(smiley_pos.x, smiley_pos.y)
        mouse.click()

        undiscovered_val = FieldValue.UNDISCOVERED

        for row in self.board:
            for field in row:
                field.value = undiscovered_val

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
        screenshot = self.sct.grab(self.board_region)
        # Optional: Save screenshot for debugging
        # mss.tools.to_png(board_screenshot.rgb, board_screenshot.size, output="screenshot.png")

        undiscovered = [
            field for row in self.board
            for field in row
            if field.value == FieldValue.UNDISCOVERED
        ]

        for field in undiscovered:
            # Check the upper edge color to see if field is still covered
            border_color = screenshot.pixel(
                field.pos_to_board.x,
                field.pos_to_board.y - self.FIELD_BORDER_OFFSET
            )

            # If edge is still white/undiscovered color, skip this field
            if self.COLOR_MAP.get(border_color, None) == FieldValue.UNDISCOVERED:
                continue

            center_color = screenshot.pixel(
                field.pos_to_board.x,
                field.pos_to_board.y
            )

            field.value = self.COLOR_MAP.get(center_color, FieldValue.EMPTY)

    def check_game_status(self) -> Literal['win', 'loss', 'ongoing']:
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
        screenshot = self.sct.grab(self.smiley_region)

        if screenshot.pixel(*self.DEAD_SMILEY_MOUTH_CORNER_POS) == self.BLACK:
            return 'win'

        if screenshot.pixel(*self.COOL_SMILEY_GLASSES_CENTER_POS) == self.BLACK:
            return 'loss'

        return 'ongoing'

    def _log_game(self, game_id: int, game_result: Literal['win', 'loss'], game_duration: float):
        """Record game result in history."""
        self.game_history.append(
            GameResult(
                id=game_id,
                result=game_result,
                total_moves=self.moves_made,
                time_played=game_duration
            )
        )

    def create_stats(self, games_completed: int, window_size: Optional[int]) -> dict[str, any]:
        """
        Compute and return summary statistics for all completed games.

        Parameters
        ----------
        games_completed : int
            Total number of games played in this run. Should match the size of `self.game_history`.
        window_size : int, optional
            Window size for calculating rolling consistency. If None, it is automatically chosen
            as max(games_completed // 30, 3) to ensure a meaningful number of windows.

        Returns
        -------
        dict[str, any]
            Nested dictionary of aggregated statistics with the following structure:

            "games_played" : int
                Total number of games executed in this run.

            "wins" : int
                Number of games where the final result was a win.

            "losses" : int
                Number of games lost (games_played - wins).

            "win_rate" : float
                Fraction of games won over all games played.

            "longest_win_streak" : int
                Maximum consecutive wins in order of play.

            "longest_loss_streak" : int
                Maximum consecutive losses in order of play.

            "moves" : dict
                Movement-related metrics:
                    "total_moves" : int
                        Sum of all moves taken across all games.
                    "total_moves_wins" : int
                        Sum of moves taken in winning games.
                    "avg_moves_win" : float
                        Average number of moves required to win.
                    "total_moves_losses" : int
                        Sum of moves taken in losing games.
                    "avg_moves_loss" : float
                        Average number of moves required to lose.

            "best_results" : dict
                Individual notable outcomes:
                    "least_moves_played_win" : int
                        Fewest moves required in any winning game.
                    "fastest_win_time" : float
                        Shortest duration of a winning game (in seconds).

            "timing" : dict
                Execution time metrics:
                    "total_time" : float
                        Total time spent playing all games (seconds).
                    "avg_time_per_game" : float
                        Average duration per game (seconds).
                    "fastest_game" : float
                        Duration of the fastest game (seconds).
                    "slowest_game" : float
                        Duration of the slowest game (seconds).

            "consistency" : float
                Rolling-window consistency metric. Calculated using a sliding window of size
                "consistency_window". Values close to 0 indicate stable performance across games;
                larger absolute values indicate more variability between windows.

            "window_size" : int
                The window size used for rolling win-rate calculation. Automatically selected
                if not provided. Used in computing "consistency".
        """
        wins = sum(1 for game in self.game_history if game.result == "win")
        total_moves = sum(game.total_moves for game in self.game_history)
        total_win_moves = sum(game.total_moves for game in self.game_history if game.result == "win")

        losses = games_completed - wins
        total_loss_moves = total_moves - total_win_moves

        # Build streaks
        streaks = [
            (result, len(list(group)))
            for result, group in groupby(game.result for game in self.game_history)
        ]

        max_win_streak = max((run for res, run in streaks if res == "win"), default=0)
        max_loss_streak = max((run for res, run in streaks if res == "loss"), default=0)

        # Time Calculations
        total_time = sum(game.time_played for game in self.game_history)
        avg_time = total_time / games_completed if games_completed > 0 else 0
        fastest_game = min(
            (game.time_played for game in self.game_history),
            default=None
        )
        slowest_game = max(
            (game.time_played for game in self.game_history),
            default=None
        )
        fastest_win_time = min(
            (game.time_played for game in self.game_history if game.result == 'win'),
            default=None
        )

        # Calculating consistency
        window_size = max(games_completed // 30, 3) if not window_size else window_size
        consistency = self.calculate_consistency([1 if g.result == 'win' else -1 for g in self.game_history ])
        stats = {
            "games_played": games_completed,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / games_completed,
            "longest_win_streak": max_win_streak,
            "longest_loss_streak": max_loss_streak,

            "moves": {
                "total_moves": total_moves,
                "total_moves_wins": total_win_moves,
                "avg_moves_win": total_win_moves / wins if wins else 0,
                "total_moves_losses": total_loss_moves,
                "avg_moves_loss": total_loss_moves / losses if losses else 0,
            },

            "best_results": {
                "least_moves_played_win": self.best_win_moves,
                "fastest_win_time": fastest_win_time,
            },

            "timing": {
                "total_time": total_time,
                "avg_time_per_game": avg_time,
                "fastest_game": fastest_game,
                "slowest_game": slowest_game,
            },
            "consistency": consistency,
            "window_size": window_size
        }

        return stats

    # --- Static Utility Methods ---
    @staticmethod
    def click_field(field: Field) -> None:
        """Execute left-click on the specified field."""
        mouse.move(*field.pos_to_screen)
        mouse.click()

    @staticmethod
    def toggle_flag(field: Field) -> None:
        """Toggle flag on the specified field via right-click."""
        field.value = (
            FieldValue.FLAGGED if field.value != FieldValue.FLAGGED
            else FieldValue.UNDISCOVERED
        )
        mouse.move(*field.pos_to_screen)
        mouse.click(RIGHT)

    @staticmethod
    def _locate_image(
            image_name: Literal['cool_smiley', 'dead_smiley', 'first_field', 'happy_smiley'],
            region: Optional[dict[str, int]] = None
    ) -> Optional[Point]:
        """
        Locate an image on screen using template matching.

        Args:
            image_name: Name of image file (without .png extension)
            region: Optional screen region to search within

        Returns:
            Point coordinates of image center, or None if not found
        """
        try:
            image_path = str(IMAGE_DIR / f"{image_name}.png")
            return locateCenterOnScreen(image_path, region=region)
        except ImageNotFoundException:
            return None

    @staticmethod
    def calculate_consistency(result, k=5):
        """Calculates the average deviation using a rolling window (k)"""
        rates = []
        for i in range(len(result) - k + 1):
            window = result[i:i+k]
            rate = sum(window)/k
            rates.append(rate)

        mean = sum(rates) / len(rates)
        return sum((r-mean)for r in rates)/len(rates)


if __name__ == '__main__':
    import random
    from line_profiler import LineProfiler


    def next_move(solver: MineSweeperSolver):
        """Random move strategy for testing."""
        undiscovered = [
            field for row in solver.board for field in row
            if field.value == FieldValue.UNDISCOVERED
        ]

        if undiscovered:
            solver.click_field(random.choice(undiscovered))


    ms_solver = MineSweeperSolver(
        difficulty="beginner",
        play_games=260,
    )

    # Option 1: Run normally
    # ms_solver.start(next_move_strategy=next_move)

    # Option 2: Run with profiling
    profiler = LineProfiler()
    profiler.add_class(cls=MineSweeperSolver)
    profiler.run('ms_solver.start(next_move_strategy=next_move)')
    profiler.print_stats(output_unit=1.0)
