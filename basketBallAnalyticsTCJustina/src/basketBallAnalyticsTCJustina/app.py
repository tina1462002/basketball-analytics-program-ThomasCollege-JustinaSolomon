"""
This Python application is a Basketball Analytics Tracker built with the tkinter library, designed to record and analyze a team's and individual players' statistics. It allows users to add, remove, and track various on-court events for players, including basic stats (points, assists, rebounds, turnovers, and different shot types), advanced metrics (PER, TS%, A/T ratio, Usage%, and BPM), and specific basketball actions like strike zone passing, cuts, paint touches allowed, and defensive outcomes. All data is persisted to a JSON file, and the application includes features for undoing the last action, editing totals, generating a full team report, and exporting data to a CSV file.
"""

import toga
from toga.style.pack import COLUMN, ROW


class BasketballAnalyticsTCJustinaSolomon(toga.App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = toga.Box()

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()


def main():
    return BasketballAnalyticsTCJustinaSolomon()
