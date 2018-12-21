#from PIL import ImageGrab, ImageOps
import pyautogui
import time
import tkinter as tk
from numpy import *

class Coordinates():
    replayBtn = (100,350)
class YourGUI(tk.Tk):
    def __init__(self):
        # inherit tkinter's window methods
        tk.Tk.__init__(self)
#Enter X field and label ⬇
        tk.Label(self, text="ENTER X:").grid(row=0, column=3)
        self.inputX = tk.Entry(self)
        self.inputX.grid(row=0, column=1)
#Enter Y field and label ⬇
        tk.Label(self, text="ENTER Y:").grid(row=0, column=0)
        self.inputY = tk.Entry(self)
        self.inputY.grid(row=0, column=4)
        # Start Button ⬇
        tk.Button(self, text="start", command=self.do_conversion).grid(row=3, column=0, columnspan=2)
        # close button ⬇
        tk.Button(self, text="exit!", command=self.EXITME).grid(row=4, column=0, columnspan=2)

    def EXITME(self):
        exit(0)  # crashed prog so it closes
        # strtoint("crashmE!")

    def do_conversion(self):
        y = self.inputY.get()
        x = self.inputX.get()

        running = True
        try:
            x = int(x)
            y = int(y)
        except:
            print("Invalid point")
            exit(0)
            # strtoint("crashmE!")
        while running:
            pyautogui.click(x, y)

if __name__ == '__main__':
    your_gui = YourGUI()
    your_gui.title('Macro Clicker') # Set title
    your_gui.mainloop()
