from stm32_nucleo_pinout import prepare_image, get_board_data, get_template_data, get_template, stack_images
import argparse
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check boards",
        epilog="Example usage: python check_board.py G474"
    )
    parser.add_argument("board", help="The board folder name")
    args = parser.parse_args()

    board_data = get_board_data(args.board)
    if board_data is None:
        print(f"Board {args.board} not found")
        sys.exit(1)

    template = get_template(args.board)
    template_data = get_template_data(template)

    # Generate the images
    imgs = []
    for image_name in template_data.keys():
        imgs.append(prepare_image(template, image_name, template_data, board_data))
    img = stack_images(imgs)
    img.show()
