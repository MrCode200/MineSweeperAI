import random

from mineSweeperSolver import MineSweeperSolver
from models import FieldValue


def main():
    def next_move(solver: MineSweeperSolver):
        """
        Decide and execute the next move in the game (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

        ═══════════════════════════════════════════════════════════════════════
        🎮 WELCOME TO THE MOVE LOGIC! THIS IS WHERE YOU IMPLEMENT YOUR AI! 🎮
        ═══════════════════════════════════════════════════════════════════════

        📋 ABOUT self.board:
        • solver.board is a 2D list (list[list[Field]]) representing the game board
        • Access fields using: solver.board[row][column]
        • Each Field has these important attributes:
          - field.value: The current state (see FieldValue enum below)
          - field.pos_to_screen: Point(x, y) - screen coordinates for clicking
          - field.safe: Boolean indicating if field is marked as safe

        🔢 FIELD VALUES (what each field can be):
        • FieldValue.UNDISCOVERED  → Hidden field, not yet clicked (ﾟοﾟ人))
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
        1. Analyze solver.board to find safe field
        2. Total amount of mines are listed in solver.total_mines
        3. To Flag/Unflag use solver.toggle_flag(field)
        4. To Click a field use solver.click_field(field)

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
        undiscovered_fields = [
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
        play_games=3,
        next_move_strategy=next_move
    )
    stats = ms_solver.start()
    print(stats)


if __name__ == '__main__':
    import mouse

    print("Right click to start! (Works also when on minesweeper website) ( •̀ ω •́ )✧")
    mouse.wait("right")
    main()
