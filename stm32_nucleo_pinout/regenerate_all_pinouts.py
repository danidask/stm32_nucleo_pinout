from generate_pinout import generate_pinout
import os
import logging


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOARDS_DIR = os.path.join(SCRIPT_DIR, "..", "boards")


if __name__ == "__main__":
    for board_dir in os.listdir(BOARDS_DIR):
        if not os.path.isdir(os.path.join(BOARDS_DIR, board_dir)):
            continue
        logging.info(f"Processing {board_dir}")
        generate_pinout(board_dir)
