# 💣 Minesweeper AI Solver

An automated Minesweeper bot that plays the game on [minesweeperonline.com](https://minesweeperonline.com) using screen capture and pixel color analysis.

## What It Does

This program automatically plays Minesweeper by:
- Capturing the game board from your screen in real-time
- Detecting field states (numbers, empty, undiscovered) through pixel color matching
- Making moves by simulating mouse clicks
- Tracking game outcomes (wins/losses)

## How It Works

1. **Initialization** - Locates the game board on screen using image recognition
2. **Game Loop** - Continuously captures the board, analyzes field states, and makes moves
3. **Move Logic** - Currently uses random selection (implement your own AI strategy here!)
4. **State Detection** - Checks the smiley face to determine if game is won, lost, or ongoing

## Customize the AI

The `make_move()` method contains the decision logic. Replace the random selection with your own Minesweeper-solving algorithm to create a smarter AI.

---

*A framework for building and testing Minesweeper AI strategies* (◕‿◕)