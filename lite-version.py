import pyautogui
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import webbrowser
import threading
import keyboard


class AutoClickerGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("AutoClicker")
        self.geometry("+300+300")
        self.attributes("-topmost", True)

        self.inputX = ttk.Entry(self)
        self.inputY = ttk.Entry(self)
        self.cmb = ttk.Combobox(self, values=["Left Click", "Right Click", "Middle Click"])

        ttk.Label(self, text="Enter X Coordinate:").grid(row=0, column=0)
        self.inputX.grid(row=0, column=1)
        ttk.Label(self, text="Enter Y Coordinate:").grid(row=1, column=0)
        self.inputY.grid(row=1, column=1)
        ttk.Label(self, text="Select Mouse Button:").grid(row=2, column=0)
        self.cmb.grid(row=2, column=1)

        ttk.Button(self, text="Start", command=self.start_clicking).grid(row=3, columnspan=2,
                                                                        pady=(10, 0), ipadx=50)

    def start_clicking(self):
        
       
            x = int(self.inputX.get())
            y = int(self.inputY.get())
            
            button = self.cmb.get()

            threading.Thread(target=self.click_coordinates,
                             args=(x, y),
                             kwargs={"button": button},
                             daemon=True).start()
        

    def click_coordinates(self, x, y, button):
         try:   

            

                running = True

                while running:
                    pyautogui.FAILSAFE = False
                    
                    if button == "Left Click":
                        pyautogui.click(x, y)
                    elif button == "Right Click":
                        pyautogui.rightClick(x, y)
                    elif button == "Middle Click":
                        pyautogui.middleClick(x, y)
                    
                    if keyboard.is_pressed("q"):  # Press 'q' to stop clicking
                        running = False

         except Exception as e:
             messagebox.showerror("Error", str(e))


# Create GUI instance and start the application loop
if __name__ == "__main__":
    app = AutoClickerGUI()
    app.mainloop()
