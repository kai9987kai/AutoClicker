import pyautogui
import tkinter as tk
from tkinter import filedialog

# Create the main window
master = tk.Tk()
master.title("Auto Clicker")

# Create the File menu
menu = tk.Menu(master)
master.config(menu=menu)
filemenu = tk.Menu(menu)
menu.add_cascade(label="File", menu=filemenu)
filemenu.add_command(label="Open", command=open_file)

# Create the Open button
open_button = tk.Button(master, text="Open", command=open_file)
open_button.pack()

# Create the Start button
start_button = tk.Button(master, text="Start", command=start_clicking)
start_button.pack()

# Define the global variables
global image, image_x, image_y, x_start, x_end, y_start, y_end

# Define the open_file function
def open_file():
    # Open a file dialog to select the image
    filepath = filedialog.askopenfilename()
    # Load the image
    image = tk.PhotoImage(file=filepath)
    # Get the image dimensions
    image_x = image.width()
    image_y = image.height()
    # Set the search area to the entire screen
    x_start = 0
    x_end = GetSystemMetrics(0)
    y_start = 0
    y_end = GetSystemMetrics(1)

# Define the start_clicking function
def start_clicking():
    # Take a screenshot of the search area
    screenshot = ImageGrab.grab(bbox=(x_start, y_start, x_end, y_end))
    # Iterate over the pixels in the screenshot
    for y in range(y_start, y_end - image_y):
        for x in range(x_start, x_end - image_x):
            # Check if the image is found at the current position
            if screenshot.crop((x, y, x + image_x, y + image_y)) == image:
                # Perform the click action
                pyautogui.click(x, y)

# Run the main loop
master.mainloop()
