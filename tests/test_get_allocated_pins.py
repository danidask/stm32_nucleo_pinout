import unittest
from stm32_nucleo_pinout.stm32_nucleo_pinout import get_allocated_pins, remove_suffix_allocated_pins
import os
import json


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
            # with open(report_file + "_temp_before.json", "w") as file:
                # json.dump(allocated_pins, file, indent=4)
            allocated_pins = remove_suffix_allocated_pins(allocated_pins)
            # with open(report_file + "_temp_after.json", "w") as file:
                # json.dump(allocated_pins, file, indent=4)
        

if __name__ == '__main__':
    unittest.main()
