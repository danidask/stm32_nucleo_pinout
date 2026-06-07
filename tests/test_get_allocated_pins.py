import unittest
from stm32_nucleo_pinout.stm32_nucleo_pinout import get_allocated_pins, remove_suffix_allocated_pins
import os
import re


class Test_get_allocated_pins(unittest.TestCase):

    def setUp(self):
        # file_path = "git_exclude\example_report_01.txt"
        self.example_reports_path = "git_exclude"
        self.example_reports_name_template = "example_report_{:02}.txt"

    def test_01(self):
        report_number = 0
        while True:
            report_number += 1
            report_file = os.path.join(self.example_reports_path, self.example_reports_name_template.format(report_number))
            if not os.path.exists(report_file):
                break
            print(report_file)
            allocated_pins = get_allocated_pins(report_file)
            self.assertIsInstance(allocated_pins, dict)
            self.assertGreater(len(allocated_pins), 0)
            allocated_pins = remove_suffix_allocated_pins(allocated_pins)
            self.assertIsInstance(allocated_pins, dict)
            self.assertGreater(len(allocated_pins), 0)
            # After normalization all keys must be plain pin names (e.g. PA5, PC13)
            for pin_name in allocated_pins.keys():
                self.assertRegex(pin_name, r'^P[A-Z]\d+$', f"Unexpected pin name '{pin_name}' after normalization")


if __name__ == '__main__':
    unittest.main()
