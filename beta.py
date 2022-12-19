import pyautogui
import tkinter as tk
from tkinter import *
from tkinter import ttk
import threading

# Import the required modules only when necessary
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from pprint import pprint
except ImportError:
    pass

try:
    import win10toast
except ImportError:
    pass

try:
    from PIL import ImageGrab
    from colormap import rgb2hex
    from win32api import GetSystemMetrics
except ImportError:
    pass

def colour_clicker():
    # Create the main window
    master = tk.Tk()
    master.title("Colour Clicker")
    master.geometry("+300+300")
    master.attributes("-topmost", True)
    master.resizable(False, False)
    try:
        master.iconbitmap('favicon.ico')
    except tk.TclError:
        pass

    # Create the Entry widgets and the start button
    ttk.Label(master, text="Enter color in hexadecimals:").grid(row=0, sticky=W)
    ttk.Label(master, text="Enter start cordinate in x axis:").grid(row=1, sticky=W)
    ttk.Label(master, text="Enter stop cordinate in x axis:").grid(row=2, sticky=W)
    ttk.Label(master, text="Enter start cordinate in y axis:").grid(row=3, sticky=W)
    ttk.Label(master, text="Enter end cordinate in y axis:").grid(row=4, sticky=W)
    ttk.Button(master, text="start", command=lambda: start_clicking(color_entry.get(), x_start_entry.get(),
                                                                    x_end_entry.get(), y_start_entry.get(),
                                                                    y_end_entry.get())).grid(row=5, sticky=W)

    color_entry = ttk.Entry(master)
    color_entry.grid(row=0, column=1)
    x_start_entry = ttk.Entry(master)
    x_start_entry.grid(row=1, column=1)
    x_end_entry = ttk.Entry(master)
    x_end_entry.grid(row=2, column=1)
    y_start_entry = ttk.Entry(master)
    y_start_entry.grid(row=3, column=1)
    y_end_entry = ttk.Entry(master)
    y_end_entry.grid(row=4, column=1)

    # Connect the entry widgets with the return button
    color_entry.bind('<Return>', lambda event: start_clicking(color_entry.get(), x_start_entry.get(),
                                                             x_end_entry.get(), y_start_entry.get(),
                                                             y_end_entry.get()))
    x_start_entry.bind('<Return>', lambda event: start_clicking(color_entry.get(), x_start_entry.get(),
                                                             x_end_entry.get(), y_start_entry.get(),
                                                             y_end_entry.get()))
    x_end_entry.bind('<Return>', lambda event: start_clicking(color_entry.get(), x_start_entry.get(),
                                                             x_end_entry.get(), y_start_entry.get(),
                                                             y_end_entry.get()))
    y_start_entry.bind('<Return>', lambda event: start_clicking(color_entry.get(), x_start_entry.get(),
                                                             x_end_entry.get(), y_start_entry.get(),
                                                             y_end_entry.get()))
    y_end_entry.bind('<Return>', lambda event: start_clicking(color_entry.get(), x_start_entry.get(),
                                                             x_end_entry.get(), y_start_entry.get(),
                                                             y_end_entry.get()))

    master.mainloop()

def start_clicking(color, x_start, x_end, y_start, y_end):
    # Convert the values from the Entry widgets to integers
    x_start = int(x_start, 10)
    x_end = int(x_end, 10)
    y_start = int(y_start, 10)
    y_end = int(y_end, 10)

    # Start the main script in a separate thread
    threading.Thread(target=mainscript, args=(color, x_start, x_end, y_start, y_end)).start()

def mainscript(color, x_start, x_end, y_start, y_end):
    # Main script code goes here
        # Main script code goes here
    while True:
        # Capture a screenshot of the specified area of the screen
        screenshot = ImageGrab.grab(bbox=(x_start, y_start, x_end, y_end))
        


        # Convert the screenshot to a list of RGB
        tuplespixels = screenshot.getdata()

        # Iterate over the pixels in the screenshot
        for pixel in pixels:
            # Check if the pixel matches the specified color
            if rgb2hex(pixel) == color:
                # Click the mouse at the current position
                pyautogui.click()
                break

if __name__ == '__main__':
    colour_clicker()
