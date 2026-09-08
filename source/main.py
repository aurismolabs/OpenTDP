# main.py
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TDP Package Builder")

    # Load application icon from same directory as main.py
    base = os.path.dirname(os.path.abspath(__file__))
    ico  = os.path.join(base, "tdp_builder.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
