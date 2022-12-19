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

# Create the Entry widget and the label for the number of clicks
ttk.Label(master, text="Enter the number of clicks:").pack()
num_clicks_entry = ttk.Entry(master)
num_clicks_entry.pack()

# Connect the Entry widget with the return button
num_clicks_entry.bind('<Return>', lambda event: start_clicking())

# Define the global variables
global image, image_x, image_y, x_start, x_end, y_start, y_end, num_clicks

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
    # Get the number of clicks from the Entry widget
    num_clicks = int(num_clicks_entry.get())
    # Set the counter to 0
    counter = 0
    # Start the loop
    while counter < num_clicks:
        # Take a screenshot of the search area
        screenshot = ImageGrab.grab(bbox=(x_start, y_start, x_end, y_end))
        # Convert the screenshot to a list of pixels
        pixels = list(screenshot.getdata())
        # Check each pixel in the screenshot
        for pixel in pixels:
            # If the pixel matches the target color, click it
            if pixel == image:
                pyautogui.click(pixel[0], pixel[1])
                # Increment the counter
                counter += 1
                # Break out of the loop
                break
    # Stop the loop
    stop_clicking()

# Define the stop_clicking function
def stop_clicking():
    # Destroy the main window
    master.destroy()

# Run the Tkinter event loop
master.mainloop()
