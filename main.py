import random
from pprint import pprint

import keyboard

from mineSweeperSolver import MineSweeperSolver
from models import FieldValue, Field


def main():
    def next_move(solver: MineSweeperSolver):
        """
        Decide and execute the next move in the game (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

        ═══════════════════════════════════════════════════════════════════════
        🎮 WELCOME TO THE MOVE LOGIC! THIS IS WHERE YOU IMPLEMENT YOUR AI! 🎮
        ═══════════════════════════════════════════════════════════════════════

        📊 SOLVER ATTRIBUTES:
        • solver.moves_made      → Moves made in current game (int)
        • solver.total_moves     → Total moves across all games (int)
        • solver.best_win_moves  → Fewest moves used to win a game (int)
        • solver.game_history    → List of completed games with results (list[GameResult])

        🎲 BOARD CONFIGURATION:
        • solver.columns        → Number of columns in the board (int)
        • solver.rows           → Number of rows in the board (int)
        • solver.total_mines    → Total number of mines on the board (int)
        • solver.board          → 2D grid of Field objects (list[list[Field]])

        📋 ABOUT solver.board:
        • Access fields using: solver.board[row][column]
        • Each Field has these important attributes:
          - field.value          → Current state (see FieldValue enum below)
          - field.pos_to_screen  → Point(x, y) - screen coordinates for clicking
          - field.pos_to_board   → Point(x, y) - coordinates within board image
          - field.id             → Unique identifier: (col + row * solver.columns)

        🔢 FIELD VALUES (what each field can be):
        • FieldValue.UNDISCOVERED  → Hidden field, not yet clicked (ﾟοﾟ人))
        • FieldValue.FLAGGED       → Flagged field which may contain a mine ⊙.☉
        • FieldValue.EMPTY         → Revealed empty field (0 adjacent mines) ＼(^o^)／
        • FieldValue.ONE           → Revealed with 1 adjacent mine
        • FieldValue.TWO           → Revealed with 2 adjacent mines
        • FieldValue.THREE         → Revealed with 3 adjacent mines
        • FieldValue.FOUR          → Revealed with 4 adjacent mines
        • FieldValue.FIVE          → Revealed with 5 adjacent mines
        • FieldValue.SIX           → Revealed with 6 adjacent mines
        • FieldValue.SEVEN         → Revealed with 7 adjacent mines
        • FieldValue.EIGHT         → Revealed with 8 adjacent mines (⊙_⊙;)

        🎯 HOW TO MAKE A MOVE:
        1. Analyze solver.board to find a safe field
        2. Use solver.total_mines to track remaining mines
        3. To flag/unflag a field: solver.toggle_flag(field)
        4. To click a field: solver.click_field(field)

        🔍 HELPER METHODS:
        • solver.check_game_status() → Returns 'win', 'loss', or 'ongoing'
        • solver._field_id(row, col) → Convert row/col to unique field ID

        💡 EXAMPLE STRATEGY (CURRENT):
        The code below shows a RANDOM move strategy - it picks any undiscovered
        field and clicks it. This is just for demonstration! (´｡• ᵕ •｡`)

        Replace this with your smart AI logic! ｡◕‿◕｡
        Good Luck :))
        ═══════════════════════════════════════════════════════════════════════
        """

        # ---------------------------------------------------------------------
        # PRE-MADE CUSTOM AI
        # _____________________________________________________________________
        # This strats win chance is (71! * 10!) / 81!
        # OR 5.32 * 10^-13 = 0.000000000000532 % win probability
        # OR 1 chance in 1.88 trillion
        # CAN YOU DO BETTER ?(‾◡◝)
        undiscovered_fields: list[Field] = [
            field for row in solver.board
            for field in row
            if field.value == FieldValue.UNDISCOVERED
        ]

        if undiscovered_fields:
            # ⚠️ EXAMPLE: Random selection (replace with your smart logic!)
            # This randomly picks an undiscovered field - not a good strategy!
            chosen_field = random.choice(undiscovered_fields)

            solver.click_field(chosen_field)

    # --- Class Configs ---
    ms_solver = MineSweeperSolver(
        difficulty='beginner',
        custom=None,
        play_games=100,
        stop_after_win=True,
    )
    stats = ms_solver.start(
        next_move_strategy=next_move,
        user_enters_username=True
    )
    print()
    pprint(stats, sort_dicts=False)


if __name__ == '__main__':
    print("Right click to start! "
          "(Works also when on minesweeper website: https://minesweeperonline.com/#beginner-200-left) \n"
          "Good Luck ( •̀ ω •́ )✧")
    keyboard.wait("enter")
    main()
