import pandas as pd
import json
import re
import sys
import os
import logging
import argparse
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class PinParserBase:
    def __init__(self, pins_df, notes_file_path, connector_name):
        self.connector_name = connector_name
        self.notes = self.parse_notes_file(notes_file_path)  # will be used by add_pin_location
        self.output = {
            "names": {},
            "notes": {},
        }
        self.parser(pins_df)

    def parser(self, pins_df):
        pass  # must be implemented by the subclass

    def add_pin_location(self, group, pin_number, pin_name):
        location = f"{group}_{pin_number}"  # location key is something like 'CN7_1'
        pin_name, note_number_str = self.split_note_numbers(pin_name)
        pin_name = self.format_pin_name(pin_name)
        # handle the case where pin name is 'PC1 or PB9', convert into list
        # also the case where pin name is empty
        for name in self.pin_name_to_list(pin_name):
            if name not in self.output["names"]:
                self.output["names"][name] = []
            self.output["names"][name].append(location)
        # add the footnotes to the dict
        if note_number_str:
            if note_number_str not in self.notes:
                logging.error(f"Footnote {note_number_str} not found in notes file")
            else:
                self.output["notes"][location] = self.notes[note_number_str]

    @staticmethod
    def split_note_numbers(name):
        # check if has a note like (1) (2) (3) etc
        match = re.search(r"\((\d+)\)", name)
        note_number_str = ""
        if match:
            note_number_str = match.group(1)
            stripped_name = name.replace(f"({note_number_str})", "").strip()
            logging.debug(f"Stripping '{name}' into '{stripped_name}'")
            name = stripped_name
        return name, note_number_str

    @staticmethod
    def format_pin_name(name):
        if not name or name == "-" or name.upper() == "NC":
            logging.debug(f"Omitting NC pin '{name}'")
            return ""  # NC pins
        return name.strip()

    @staticmethod
    def pin_name_to_list(name):
        if not name:
            return []
        elif " OR " in name.upper():
            names_list = name.upper().split(" OR ")
        elif "/" in name:
            names_list = name.split("/")
        else:
            return [name]
        names_list = [n.strip() for n in names_list]
        logging.debug(f"Splitting '{name}' into {names_list}")
        return names_list

    @staticmethod
    def parse_notes_file(notes_file_path):
        notes = {}
        with open(notes_file_path, "r") as f:
            last_line_number = 0
            for line in f:
                # the file must have the same format as the datasheet, i.e. '1. comment'
                point_index = line.find(".")
                if point_index == -1 or point_index > 4:
                    # point not found, so either it's not the correct format, or is a multi line comment
                    if last_line_number == 0:
                        logging.error(f"Error parsing line: {line} of {notes_file_path}\nFootnotes must be in the format '1. comment' as in the datasheet")
                        sys.exit(1)
                    else:
                        notes[last_line_number] += f"\n{line}"
                        continue
                number_str, comment = line.split(".", 1)
                number_str = number_str.strip()
                notes[number_str] = comment.strip()
                last_line_number = number_str
        return notes

    def print_output(self):
        print(self.output)

    def save_json(self, filename):
        with open(filename, "w") as f:
            f.write(json.dumps(self.output, indent=4))


class PinParserMorpho(PinParserBase):
    def parser(self, pins_df):
        if not all(re.match(r"CN\d+_[OE]_", col) for col in pins_df.columns):
            logging.error("Columns must be in the format CN11_O_pin CN11_E_name  CN11_O_pin CN11_E_name etc. See how_to_create_new_board.md")
            sys.exit(1)
        # Extract unique connectors
        pattern = re.compile(r'(CN\d+)')
        connectors = set()
        for column in pins_df.columns:
            match = pattern.match(column)
            if match:
                connectors.add(match.group(1))
        # {'CN12', 'CN11'}
        for _, row in pins_df.iterrows():
            for connector in connectors:
                self.add_pin_location(connector, row[f"{connector}_O_pin"], row[f"{connector}_O_name"])
                self.add_pin_location(connector, row[f"{connector}_E_pin"], row[f"{connector}_E_name"])


class PinParserArduino(PinParserBase):
    def parser(self, pins_df):
        # check that pins_df contains the expected columns
        required_columns = ["Pin", "Pin name", "STM32 pin"]
        if not all(col in pins_df.columns for col in required_columns):
            logging.error(f"Columns {required_columns} are required in {self.connector_name}.tsv file. See how_to_create_new_board.md")
            sys.exit(1)
        for _, row in pins_df.iterrows():
            pin_name = row["STM32 pin"]
            # if the STM32 pin is empty, use the pin name
            if not pin_name or pin_name == "-":
                pin_name = row["Pin name"]
            self.add_pin_location(self.connector_name, row["Pin"], pin_name)


def get_arduino_connectors(board) -> list:
    output = []
    board_path = os.path.join("boards", board)
    for file_name in os.listdir(board_path):
        if file_name.startswith("CN") and file_name.endswith(".tsv"):
            output.append(os.path.splitext(file_name)[0])  # filename without extension
    return output


def remove_previous_partial_files(board):
    board_path = os.path.join("boards", board)
    for partial_file_path in os.listdir(board_path):
        if partial_file_path.startswith("partial_"):
            os.remove(os.path.join(board_path, partial_file_path))


def join_partial_files(board):
    output = {
        "comment": "THIS FILE WAS GENERATED BY A SCRIPT. SEE info.txt",
        "names": {},
        "notes": {},
    }
    board_path = os.path.join("boards", board)
    for partial_file_path in os.listdir(board_path):
        if not partial_file_path.startswith("partial_") or not partial_file_path.endswith(".json"):
            continue
        with open(os.path.join(board_path, partial_file_path), "r") as f:
            partial_json = json.load(f)
        for key, value in partial_json["names"].items():
            if key not in output["names"]:
                output["names"][key] = []
            output["names"][key] += value  # both are lists so concatenate
        for key, value in partial_json["notes"].items():
            output["notes"][key] = value
    ordered_output = sort_pinout_dict(output)
    with open(os.path.join(board_path, "pinout.json"), "w") as f:
        json.dump(ordered_output, f, indent=4)


def sort_pinout_dict(d):
    """ This mess to ensure a deterministic pinout.json output """
    if isinstance(d, dict):
        sorted_dict = OrderedDict()
        for k, v in sorted(d.items()):
            if k == "names" and isinstance(v, dict):
                sorted_dict[k] = OrderedDict((sub_k, sorted(sub_v)) for sub_k, sub_v in sorted(v.items()))
            else:
                sorted_dict[k] = sort_pinout_dict(v)
        return sorted_dict
    elif isinstance(d, list):
        return [sort_pinout_dict(i) for i in d]
    else:
        return d


def read_tsv_file(file_path):
    try:
        df = pd.read_csv(file_path, sep="\t")
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        sys.exit(1)
    return df


def generate_pinout(board):
    if not os.path.exists(os.path.join("boards", board)):
        logging.error(f"Board {board} not found in the 'boards' directory")
        sys.exit(1)
    remove_previous_partial_files(board)
    # Arduino part
    arduino_connectors = get_arduino_connectors(board)
    logging.info(f"Arduino connectors found: {arduino_connectors}")
    for connector_file in arduino_connectors:
        df = read_tsv_file(os.path.join("boards", board, f"{connector_file}.tsv"))
        pin_parser = PinParserArduino(df, os.path.join("boards", board, "arduino_footnotes.txt"), connector_file)
        pin_parser.save_json(os.path.join("boards", board, f"partial_{connector_file}.json"))
    # Morpho part
    morpho_file = os.path.join("boards", board, "morpho.tsv")
    if not os.path.exists(morpho_file):
        logging.warning(f"File {morpho_file} not found. Skipping ...")
    else:
        df = read_tsv_file(os.path.join("boards", board, "morpho.tsv"))
        pin_parser = PinParserMorpho(df, os.path.join("boards", board, "morpho_footnotes.txt"), "morpho")
        pin_parser.save_json(os.path.join("boards", board, "partial_morpho.json"))
    # Join the partial json files
    join_partial_files(board)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check templates",
        epilog="Example usage: python generate_pinout.py G474"
    )
    parser.add_argument("board", help="The board name")
    args = parser.parse_args()
    generate_pinout(args.board)
    print(f"\nPinout boards/{args.board}/pinout.json generated successfully")
    print(f"Use 'python check_board.py {args.board}' to check it")
