from stm32_nucleo_pinout import prepare_image, get_template_data
from tkinter import Tk, Label
from PIL import ImageTk
import os
import argparse
import sys


class ImageViewer:
    def __init__(self, image, origin_x, origin_y):
        self.image = image
        self.root = Tk()
        self.root.title("Image Viewer")
        self.last_x = 0
        self.last_y = 0
        self.origin_x = origin_x
        self.origin_y = origin_y

        # Create a label to display the image
        self.photo = ImageTk.PhotoImage(self.image)
        self.image_label = Label(self.root, image=self.photo)
        self.image_label.pack()

        # Create a label to display the coordinates
        self.coords_label = Label(self.root, text="Coordinates: (0, 0)")
        self.coords_label.pack()

        # Bind the mouse motion and click events
        self.image_label.bind('<Motion>', self.mouse_motion)
        self.image_label.bind('<Button-1>', self.mouse_click)

    def mouse_motion(self, event):
        x, y = event.x, event.y
        self.coords_label.config(text=f"Coordinates: ({x}, {y})")

    def mouse_click(self, event):
        x, y = event.x, event.y
        print(f"Mouse clicked at: {x}, {y} with origin : {x-self.origin_x}, {y-self.origin_y} distance from last click: {x - self.last_x}, {y - self.last_y}")
        self.last_x = x
        self.last_y = y

    def show(self):
        # Start the Tkinter event loop
        self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check templates",
        epilog="Example usage: python check_template.py nucleo64 morpho_right.png"
    )
    parser.add_argument("template", help="The template folder name")
    parser.add_argument("image", help="The image file to test")
    parser.add_argument("-c", "--coordinates", action="store_true", help="Allows to click on the image and get the coordinates")
    args = parser.parse_args()

    template_data = get_template_data(args.template)
    if template_data is None:
        print(f"Template {args.template} not found")
        sys.exit(1)

    # check if the image exists
    if not os.path.exists(os.path.join("templates", args.template, args.image)):
        print(f"Image {args.image} not found in template {args.template}")
        sys.exit(1)

    img = prepare_image(args.template, args.image, template_data)
    if args.coordinates:
        origin_x = template_data[args.image]["origin_x"]
        origin_y = template_data[args.image]["origin_y"]
        viewer = ImageViewer(img, origin_x, origin_y)
        viewer.show()
    else:
        img.show()
