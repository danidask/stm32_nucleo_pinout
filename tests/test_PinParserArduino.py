import unittest
from stm32_nucleo_pinout.generate_pinout import PinParserArduino, PinParserMorpho, read_tsv_file, get_arduino_connectors
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOARDS_DIR = os.path.join(SCRIPT_DIR, "..", "boards")


class TestPinParserArduino(unittest.TestCase):

    def setUp(self):
        # Setup any necessary initial state or objects
        self.all_boards = []
        for board_dir in os.listdir(BOARDS_DIR):
            if os.path.isdir(os.path.join(BOARDS_DIR, board_dir)):
                self.all_boards.append(board_dir)

    def test_01(self):
        for board in self.all_boards:
            print(f"Processing {board}")
            arduino_connectors = get_arduino_connectors(board)
            for connector_file in arduino_connectors:
                df = read_tsv_file(os.path.join("boards", board, f"{connector_file}.tsv"))
                pin_parser = PinParserArduino(df, os.path.join("boards", board, "arduino_footnotes.txt"), connector_file)

    def test_02(self):
        for board in self.all_boards:
            print(f"Processing {board}")
            df = read_tsv_file(os.path.join("boards", board, "morpho.tsv"))
            pin_parser = PinParserMorpho(df, os.path.join("boards", board, "morpho_footnotes.txt"), "morpho")


if __name__ == '__main__':
    unittest.main()