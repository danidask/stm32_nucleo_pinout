from PIL import Image, ImageDraw, ImageFont
import json
import os
import argparse
from time import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOARDS_DIR = os.path.join(SCRIPT_DIR, "..", "boards")
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "..", "templates")

# Global variables to cache some file reads
_functions_alias_cache = None


def get_mcu(report_file_path) -> str:
    """
    Parses the CubeIDE report file to get the MCU identifier.

    Args:
        report_file_path (str): Full path to the CubeIDE report file.

    Returns:
        str: The MCU identifier extracted from the file.

    Raises:
        ValueError: If no line starting with "MCU" is found in the file.
    """
    with open(report_file_path, "r") as file:
        for line in file.readlines():
            if line.startswith("MCU"):
                return line.split("MCU")[1].strip()
    raise ValueError("MCU not found in file")


def get_board(mcu):
    with open(os.path.join(BOARDS_DIR, "boards.json"), "r") as file:
        boards = json.load(file)
    if mcu not in boards:
        raise ValueError(f'MCU "{mcu}" not found in boards.json')
    return boards[mcu]


def get_board_data(board):
    try:
        with open(os.path.join(BOARDS_DIR, board, "pinout.json"), "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def get_template_data(template):
    try:
        with open(os.path.join(TEMPLATES_DIR, template, "info.json")) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def get_template(board):
    with open(os.path.join(TEMPLATES_DIR, "templates.json"), "r") as file:
        templates = json.load(file)
    if board not in templates:
        raise ValueError(f'"{board}" not found in templates.json')
    return templates[board]


def get_allocated_pins(file_path) -> dict:
    """
    Parses the CubeIDE report file to get the allocated pins information.

    Args:
        file_path (str): The full path to the CubeIDE report file.

    Returns:
        dict: A dictionary with the allocated pins information.
    """
    with open(file_path, "r") as file:
        lines = file.readlines()
    # Find the section with the pinout table
    start = -1
    for i, line in enumerate(lines):
        if line == "Pin Nb\tPINs\tFUNCTIONs\tLABELs\n":
            start = i
            break
    pinout_list = []
    for i in range(start+1, len(lines)):
        if lines[i] == "PERIPHERALS	MODES\tFUNCTIONS\tPINS\n":
            break
        pinout_list.append(lines[i].strip())
    output = {}
    for pin in pinout_list:
        # 2       PC13    GPIO_Input      B1 [blue push button]
        tokens = pin.split("\t")
        pin_name = tokens[1]
        pin_number = int(tokens[0])
        functions = tokens[2]
        if len(tokens) > 3:
            labels = tokens[3]
        else:
            labels = ""
        output[pin_name] = {"number": pin_number, "functions": functions, "labels": labels}
    return output


def remove_suffix_allocated_pins(allocated_pins):
    # deal with PG10-NRST PF0-OSC_IN PF1-OSC_OUT PC14-OSC32_IN (OSC32_IN) PC15-OSC32_OUT (OSC32_OUT) PH0-OSC_IN (PH0) PH1-OSC_OUT (PH1)* PC1*
    # "PC15-OSC32_OUT (OSC32_OUT)": {
        # "number": 9,
        # "functions": "RCC_OSC32_OUT",
        # "labels": ""
    # },
    new_allocated_pins = {}
    for pin_name in allocated_pins.keys():
        new_pin_name = pin_name
        if "*" in new_pin_name:
            new_pin_name = new_pin_name.replace("*", "").strip()
        if "-" in new_pin_name:
            new_pin_name = new_pin_name.split("-")[0].strip()
        if "(" in new_pin_name:
            new_pin_name = new_pin_name.split("(")[0].strip()
        new_allocated_pins[new_pin_name] = allocated_pins[pin_name]
    return new_allocated_pins


def get_function_alias(pin_function: str) -> str:
    """
    Retrieve the alias for a given pin function to make it shorter
    ej: GPIO_Output -> OUT

    Args:
        pin_function (str): The name of the pin function to retrieve the alias for.

    Returns:
        str: The alias of the pin function if found, otherwise the original pin function name.
    """
    global _functions_alias_cache
    if _functions_alias_cache is None:
        with open(os.path.join(BOARDS_DIR, "functions_alias.json"), "r") as file:
            _functions_alias_cache = json.load(file)
    # "GPIO_Output": "OUT",
    if pin_function not in _functions_alias_cache:
        return pin_function
    return _functions_alias_cache[pin_function]


def place_text(draw, x, y, text, font, marker_distance, text_side):
    if text_side == "left":
        marker_distance *= -1
    offset_center_alignment = font.size * -0.625
    position = (x+marker_distance, y+offset_center_alignment)
    # background rectangle
    background_position = draw.textbbox(position, text, font=font)  # bounding_box (left, top, right, bottom)
    if text_side == "left":
        # align text to the right, draw.text(align="right") does not work
        start = background_position[0]
        end = background_position[2]
        width = end - start
        background_position = (start-width, background_position[1], start, background_position[3])
        position = (position[0] - width, position[1])
    draw.rectangle(background_position, fill="white")
    draw.text(position, text, fill="black", font=font)


def search_pin_names_in_board_data(connector_key, board_data):
    """ Sometimes several pin_names are associated with the same connector_key """
    pin_names_found = []
    for pin_name in board_data["names"].keys():
        if connector_key in board_data["names"][pin_name]:
            pin_names_found.append(pin_name)
    return pin_names_found


def get_pin_text(board_data, allocated_pins, connector_key) -> str:
    if board_data is None:
        # this is for debugging purposes, return the connector_key
        return connector_key
    pin_names_found = search_pin_names_in_board_data(connector_key, board_data)
    if not pin_names_found:
        # is a NC pin
        return "", False
    if allocated_pins is None:
        # this is for debugging purposes return pin_names
        return " / ".join(pin_names_found), False
    # if not a GPIO, return the name as it is (pin function)
    if not pin_names_found[0].startswith("P"):
        return " / ".join(pin_names_found), False
    pin_text = ""
    for pin_name in pin_names_found:
        if pin_name not in allocated_pins:
            continue
        # "PC13": {
        #     "number": 2,
        #     "functions": "GPIO_Input",
        #     "labels": "B1 [blue push button]"
        # },
        pin_function = get_function_alias(allocated_pins[pin_name]['functions'])
        label = allocated_pins[pin_name]["labels"]
        if allocated_pins[pin_name]["labels"]:
            pin_text += f"{label} ({pin_function})"
        else:
            pin_text += pin_function
        pin_text += "   "
    return pin_text.strip(), True


def place_text_and_point(draw, x, y, text, font, marker_distance, text_side, dot_size, is_user):
    color = "green"  # default color
    if not is_user:
        color = "grey"
    draw.circle((x, y), dot_size, fill=color)
    place_text(draw, x, y, text, font, marker_distance, text_side)


def prepare_image(template_name, image_name, template_data, board_data=None, allocated_pins=None):
    # print(f"{template_name=} {image_name=} {template_data=}")
    debug = False if board_data is not None else True
    img = Image.open(os.path.join(TEMPLATES_DIR, template_name, image_name))
    draw = ImageDraw.Draw(img)
    origin_x = template_data[image_name]["origin_x"]
    origin_y = template_data[image_name]["origin_y"]
    if debug:
        # mark the reference point
        draw.circle((origin_x, origin_y), 10, fill="black")
    for connector in template_data[image_name]["connectors"]:
        x = float(connector["x"])
        y = float(connector["y"])
        x_spacing = float(connector["x_spacing"])
        y_spacing = float(connector["y_spacing"])
        dot_size = float(connector["dot_size"])
        n_pins = int(connector["n_pins"])
        try:
            font = ImageFont.truetype("arial.ttf", connector["font_size"])
        except IOError:
            font = ImageFont.load_default(connector["font_size"])
        text_side = connector["text_side"]
        marker_distance = connector["marker_distance"]
        if not connector["dual_row"]:
            for i in range(n_pins):
                pin = f"{connector['name']}_{i+1}"  # like "CN7_1"
                pin_text, is_user = get_pin_text(board_data, allocated_pins, pin)
                if pin_text:
                    position_x = x+origin_x+x_spacing
                    position_y = y+(i*y_spacing)+origin_y
                    place_text_and_point(draw, position_x, position_y, pin_text, font, marker_distance, text_side, dot_size, is_user)
                # else:
                #     logging.debug(f"Pin {pin} not found in allocated pins")
        else:
            for i in range(0, n_pins, 2):
                # left side
                position_x = x+origin_x  # must be calculated here, because can be used in right side
                position_y = y+((i//2)*y_spacing)+origin_y
                pin = f"{connector['name']}_{i+1}"
                pin_text, is_user = get_pin_text(board_data, allocated_pins, pin)
                if pin_text:
                    place_text_and_point(draw, position_x, position_y, pin_text, font, marker_distance, "left", dot_size, is_user)
                # right side
                pin = f"{connector['name']}_{i+2}"
                pin_text, is_user = get_pin_text(board_data, allocated_pins, pin)
                if pin_text:
                    position_x += x_spacing
                    place_text_and_point(draw, position_x, position_y, pin_text, font, marker_distance, "right", dot_size, is_user)
    return img


def stack_images(imgs):
    # generate a vertical stack of images
    width = max(img.width for img in imgs)
    height = sum(img.height for img in imgs)
    new_img = Image.new("RGB", (width, height))
    offset_y = 0
    for img in imgs:
        new_img.paste(img, (0, offset_y))
        offset_y += img.height
    return new_img


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with the pinout of a board, based on the CubeIDE report",
        epilog="Example usage: stm32_nucleo_pinout path_to_report/my_report.txt -o pinout_image.png"
    )
    parser.add_argument("cubeide_report_file", help="Full path to the CubeIDE report file")
    parser.add_argument("-o", "--output", required=False, help="Save to a output file instead of showing")
    parser.add_argument("-s", "--save", action="store_true", help="Same as output but saves to a default file")
    parser.add_argument("-k", "--skip_check", action="store_true", help="Skip the check for the file modification date")
    args = parser.parse_args()
    if not os.path.exists(args.cubeide_report_file):
        print(f"File {args.cubeide_report_file} not found")
        exit(1)
    if not args.skip_check:
        modification_date = os.path.getmtime(args.cubeide_report_file)
        minutes_old = (time() - modification_date) / 60
        if minutes_old > 5:
            print(f"WARNING!! Report file is {int(minutes_old)} minutes old, consider regenerate it.")
            if input("Do you want to continue? [y/n] ").lower() != "y":
                exit(0)
        else:
            print(f"Report file is {int(minutes_old)} minutes old. Generating pinout image ...")
    else:
        print("Skip check for the report file modification date. Generating pinout image ...")
    if args.output:
        output_file = args.output
    elif args.save:
        cubeide_report_folder = os.path.dirname(args.cubeide_report_file)
        cubeide_report_name_no_ext = os.path.splitext(os.path.basename(args.cubeide_report_file))[0]
        output_file = os.path.join(cubeide_report_folder, f"{cubeide_report_name_no_ext}_pinout.png")
    else:
        output_file = None
    mcu = get_mcu(args.cubeide_report_file)
    allocated_pins = get_allocated_pins(args.cubeide_report_file)
    allocated_pins = remove_suffix_allocated_pins(allocated_pins)
    board = get_board(mcu)
    board_data = get_board_data(board)
    template = get_template(board)
    template_data = get_template_data(template)
    # Generate the images
    imgs = []
    for image_name in template_data.keys():
        imgs.append(prepare_image(template, image_name, template_data, board_data, allocated_pins))
    img = stack_images(imgs)
    # Output data
    if output_file is not None:
        img.save(output_file)
        print(f"Image saved to {output_file}")
    else:
        img.show()


if __name__ == "__main__":
    main()
