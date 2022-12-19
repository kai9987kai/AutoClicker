import pyautogui
import tkinter as tk
from tkinter import ttk
import threading

try:
    from PIL import ImageGrab
    from colormap import rgb2hex
except ImportError:
    pass

def colour_clicker():
    # Create the main window
    master = tk.Tk()
    master.title("Colour Clicker")
    master.geometry("+300+300")
    master.attributes("-topmost", True)
    master.resizable(False, False)

    # Create the Entry widgets and the start button
    ttk.Label(master, text="Enter color in hexadecimals:").grid(row=0, sticky=tk.W)
    ttk.Label(master, text="Enter start cordinate in x axis:").grid(row=1, sticky=tk.W)
    ttk.Label(master, text="Enter stop cordinate in x axis:").grid(row=2, sticky=tk.W)
    ttk.Label(master, text="Enter start cordinate in y axis:").grid(row=3, sticky=tk.W)
    ttk.Label(master, text="Enter end cordinate in y axis:").grid(row=4, sticky=tk.W)
    ttk.Button(master, text="start", command=lambda: start_clicking(color_entry.get(), x_start_entry.get(),
                                                                    x_end_entry.get(), y_start_entry.get(),
                                                                    y_end_entry.get())).grid(row=5, sticky=tk.W)

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
    x_end_entry.bind('<Return>', lambda event: start_clicking(color_entry.get())), x_start_entry.get(),
    x_end_entry.get(), y_start_entry.get
    def start_clicking(color, x_start, x_end, y_start, y_end):
        # Start the main script in a new thread
        main_thread = threading.Thread(target=mainscript, args=(color, x_start, x_end, y_start, y_end))
        main_thread.start()
        
def mainscript(color, x_start, x_end, y_start, y_end):
    # Define the global variables
    global stop_clicking, pixels, stop_clicking_thread
    # Initialize the pixels variable
    pixels = []
    # Convert the coordinates to integers
    x_start = int(x_start)
    x_end = int(x_end)
    y_start = int(y_start)
    y_end = int(y_end)
    # Take a screenshot of the selected area
    screenshot = ImageGrab.grab(bbox=(x_start, y_start, x_end, y_end))
    # Iterate over the pixels in the screenshot
    for pixel in pixels:
        # Check if the pixel matches the color
        if rgb2hex(pixel) == color:
            # Perform the click action
            pyautogui.click(x_start + pixels.index(pixel) % (x_end - x_start),
                            y_start + pixels.index(pixel) // (x_end - x_start))

                # Sleep for 0.01 seconds
            pyautogui.sleep(0.01)
                # Check if the stop_clicking flag is set
        if stop_clicking:
            
            # Set the stop_clicking flag to False
            stop_clicking = False
            # Join the stop_clicking_thread
            stop_clicking_thread.join()

def stop_clicking():
    # Define the global variables
    global stop_clicking, pixels, stop_clicking_thread
    # Set the stop_clicking flag to True
    stop_clicking = True
    # Create a new thread
    stop_clicking_thread = threading.Thread(target=stop_clicking_func)
    # Start the thread
    stop_clicking_thread.start()

def stop_clicking_func():
    # Sleep for 1 second
    pyautogui.sleep(1)
    # Set the stop_clicking flag to False
    stop_clicking = False

# Run the colour_clicker function
colour_clicker()
