import pyautogui
import time
import tkinter as tk
import webbrowser
from tkinter import *
from tkinter import messagebox
import keyboard
from tkinter import ttk
import os
import sys
import datetime
import threading
try:
    import win10toast #This module only works on windows
except:
    pass
################################################################################
#     /\  | |  | |__   __/ __ \   / ____| |    |_   _/ ____| |/ /  ____|  __ \ #
#    /  \ | |  | |  | | | |  | | | |    | |      | || |    | ' /| |__  | |__) |#
#   / /\ \| |  | |  | | | |  | | | |    | |      | || |    |  < |  __| |  _  / #
#  / ____ \ |__| |  | | | |__| | | |____| |____ _| || |____| . \| |____| | \ \ #
# /_/    \_\____/   |_|  \____/   \_____|______|_____\_____|_|\_\______|_|  \_\#
################################################################################
def NOTIFICATION():
    try:
        toaster = win10toast.ToastNotifier()
        toaster.show_toast("AutoClicker", "V4.0", duration=5, threaded=True, icon_path ="favicon.ico")
        messagebox.showinfo('AutoClicker', 'V4.0')
    except:
        pass


def tutorial():
    window = Tk()
    window.title("Tutorial")
    window.geometry('770x50')
    tab_control = ttk.Notebook(window)
    tab1 = ttk.Frame(tab_control)
    tab2 = ttk.Frame(tab_control)
    tab_control.add(tab1, text='First Step')
    tab_control.add(tab2, text='Second Step')
    lbl1 = Label(tab1, anchor=W,
                 text='First get the coordinates, click on Find Coordinates the first number is the x coordinate and the second is the y coordinate.')
    lbl1.grid(column=0, row=0)
    lbl2 = Label(tab2,
                 text='Input the X and Y coordinates into the X and Y entry boxes set a key as the stop key and press start you can use the stop key to stop the clicking.')
    lbl2.grid(column=0, row=0)
    tab_control.pack(expand=1, fill='both')
    try:
        window.iconbitmap('favicon.ico')
    except:
        pass
    
    
    window.attributes("-topmost", True)
    window.resizable(False, False)
    window.geometry("+300+300")
    window.mainloop()


class Coordinates():
    replayBtn = (100, 350)


def MAINWINDOW_NEWSTYLE():
    class YourGUI(tk.Tk):
        def __init__(self):
            tk.Tk.__init__(self)
            ttk.Label(self, text="ENTER Y:", background="#ebdbff", anchor=E).grid(row=0, column=2)
            ttk.Label(self, text="Delay Between clicks", background="#ebdbff", anchor=E).grid(row=5, column=0)
            self.inputdelayentry = tk.StringVar()


            
            self.inputdelayentry.set("0")
        
            
            self.inputdelay = ttk.Entry(self, textvariable= self.inputdelayentry).grid(row=5, column=1)
            
             
            
            
            self.inputX = ttk.Entry(self)
            self.inputX.grid(row=0, column=1)
            
            self.cmb = ttk.Combobox(self, width="10", values=("Left Click","Right Click"))
            
            class TableDropDown(ttk.Combobox):
                def __init__(self, parent):
                    
                    self.current_table = tk.StringVar() # create variable for table
                    ttk.Combobox.__init__(self, parent)#  init widget
                    self.config(textvariable = self.current_table, state = "readonly", values = ["Customers", "Pets", "Invoices", "Prices"])
                    self.current(0) # index of values for current table
                    self.place(x = 50, y = 50, anchor = "w") # place drop down box

            ttk.Label(self, text="""Choose the left or
right mouse button""", background="#ebdbff", anchor=E).grid(row=1, column=0)
            self.cmb.grid(row=1, column=1, sticky="ew")
            self.cmb.current(0)



            
    
            
            tk.Label(self, text="ENTER X:", background="#ebdbff").grid(row=0, column=0)
            self.inputY = ttk.Entry(self)
            self.inputY.grid(row=0, column=3)
            # Start Button ⬇
            ttk.Button(self, text="start", command=self.startclick).grid(row=6, column=0)
            # close button ⬇
            ttk.Button(self, text="exit!", command=self.EXITME).grid(row=7, column=0)
            self.inputhotkey = ttk.Entry(self)
            self.inputhotkey.grid(row=1, column=3, columnspan=1)


            def callback():
                webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

            def callback2():
                webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

            ttk.Button(self, text="ABOUT", command=callback).grid(row=5, column=3, sticky="ew")

            def clicked3():
                your_gui.destroy()
                pyautogui.PAUSE = 0.50
                pyautogui.FAILSAFE = True

                things = []
                root = Tk()
                root.geometry("500x350")

                list_box = Listbox(root, font=(12))
                list_box.config(width=30, height=18)
                list_box.place(x=0, y=0)

                run_btn = ttk.Button(root, text="Run List", command=lambda: run_list())
                run_btn.place(x=350, y=20)
                run_btn.config(width=15)

                del_btn = ttk.Button(root, text="Delete", command=lambda: delete(list_box))
                del_btn.place(x=350, y=80)
                del_btn.config(width=15)

                add_btn = ttk.Button(root, text="Add", command=lambda: add())
                add_btn.place(x=350, y=50)
                add_btn.config(width=15)

                x_txt = StringVar()
                y_txt = StringVar()

                x_label = Label(root, text="x", font=(12))
                x_label.place(x=320, y=150)

                x = ttk.Entry(root, textvariable=x_txt)
                x.place(x=350, y=150)

                x_txt.set('')
                y_label = Label(root, text="y", font=(12))
                y_label.place(x=320, y=170)

                y = ttk.Entry(root, textvariable=y_txt)
                y.place(x=350, y=170)
                y_txt.set('')
                root.title("AutoClicker - list of coordinates")
                try:
                    root.iconbitmap('favicon.ico')
                except:
                    pass
                root.resizable(False, False)
                root.attributes("-topmost", True)

                def add():
                    content_x = x_txt.get()
                    content_y = y_txt.get()
                    closed_str = [content_x, content_y]
                    things.append(closed_str)
                    list_box.delete(0, 'end')
                    for i in range(len(things)):
                        list_box.insert(END, things[i])

                def run_list():
                    x_cords = [item[0] for item in things]
                    y_cords = [item[1] for item in things]

                    for i in range(len(things)):
                        screenWidth, screenHeight = pyautogui.size()
                        currentMouseX, currentMouseY = pyautogui.position()
                        pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                        # print("Gonna Click",x_cords[i],y_cords[i])
                        pyautogui.click()

                def delete(listbox):
                    global things
                    # Delete from Listbox
                    selection = list_box.curselection()
                    list_box.delete(selection[0])
                    # Delete from list that provided it
                    value = eval(list_box.get(selection[0]))
                    ind = things.index(value)
                    del (things[ind])

                popup = Menu(root, tearoff=0)
                popup.add_command(label='Run list', command=run_list)
                popup.add_command(label='Exit', command=self.EXITME)

                def do_popup(event):
                    # display the popup menu
                    try:
                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        # make sure to release the grab (Tk 8.0a1 only)
                        popup.grab_release()

                root.bind("<Button-3>", do_popup)

                root.mainloop()

            def clicked():
                try:
                    os.startfile("AutoClickerContactPage.exe")
                except:
                    messagebox.showerror("ERROR", "AutoClickerContactPage.exe is missing")
                    pass

            def clicked2():
                try:
                    os.startfile("AutoClickerMegaSpam.exe")
                except:
                    messagebox.showerror("Error", "AutoClickerMegaSpam.exe is missing")
                    pass
            def Finder():
                try:
                    os.startfile("MousePos.exe")
                except:
                    messagebox.showerror("ERROR", "MousePos.exe is missing")
                    pass
                

            ttk.Button(self, text="List Coordinates", command=clicked3).grid(row=7, column=3, sticky="ew")
            ttk.Button(self, text="Find Coordinates", command=Finder).grid(row=6, column=3, sticky="ew")

            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('259x94')
                try:
                    window.iconbitmap('favicon.ico')
                except:
                    pass
                window.resizable(False, False)
                window.geometry("+0+0")
                window.attributes("-topmost", True)


                def callBackFunc():
                    your_gui.overrideredirect(True)
                    window.destroy()

                def ExitWindow():
                    window.destroy()

                def Full_screen():
                    your_gui.attributes('-fullscreen', True)
                    your_gui.bind('<Escape>', lambda e: root.destroy())
                    window.destroy()
                def Exit_Full_Screen():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                def Show_Title_bar():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)

                ttk.Label(window, text="Settings").grid(column=0, row=1, sticky="ew")
                ttk.Button(window, text="               Exit Settings               ", command=ExitWindow).grid(column=0, row= 6)
                ttk.Button(window, text="‍‍FullScreen", command=Full_screen).grid(column=0, row=3, sticky="ew")
                ttk.Button(window, text="Exit FullScreen", command=Exit_Full_Screen).grid(column=1, row=3, sticky="ew")
                ttk.Button(window, text="Hide Title Bar ", command=callBackFunc).grid(column=0, row=5, sticky="ew")
                ttk.Button(window, text="Show Title Bar", command=Show_Title_bar).grid(column=1, row=5, sticky="ew")
                ttk.Button(window, text="Restart program", command=Show_Title_bar).grid(column=1, row=6, sticky="ew")

                popup = Menu(your_gui, tearoff=0)
                popup.add_command(label="FullScreen", command=Full_screen)
                popup.add_command(label="Exit FullScreen", command=Exit_Full_Screen)
                popup.add_command(label="Hide Title Bar", command=callBackFunc)
                popup.add_command(label="Show Title Bar", command=Show_Title_bar)
                popup.add_command(label="Restart program", command=Show_Title_bar)
                popup.add_command(label="Exit Settings", command=ExitWindow)

                def do_popup(event):

                    try:

                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        popup.grab_release()

                window.bind("<Button-3>", do_popup)

                window.mainloop()

            def OpenOldWindow():
                your_gui.destroy()
                OldStyleGUI()

            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='About', command=callback)
            new_item.add_command(label='Github Page', command=callback2)
            new_item.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            new_item.add_command(label='Version Number', command=NOTIFICATION)
            new_item.add_command(label='Old Style GUI', command=OpenOldWindow)
            new_item.add_command(label='Settings', command=settings)
            new_item.add_command(label='List of Coordinates', command=clicked3)
            new_item.add_command(label='Coordinates Finder', command=Finder)
            new_item.add_separator()
            new_item.add_command(label='Start', command=self.do_conversion)
            new_item.add_command(label='Exit', command=self.EXITME)

            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            menu.add_cascade(label='Help', menu=new_item2)
            new_item2.add_command(label='Contact', command=clicked)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#ebdbff").grid(row=1, column=2)
            popup = Menu(self, tearoff=0)
            popup.add_command(label="About", command=callback)  # , command=next) etc...
            popup.add_command(label='GitHub Page', command=callback2)
            popup.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            popup.add_command(label='Version Number', command=NOTIFICATION)
            popup.add_command(label='Old Style Gui', command=OpenOldWindow)
            popup.add_command(label='Settings', command=settings)
            popup.add_command(label='List of coordinates', command=clicked3)
            popup.add_command(label='Find Coordinates', command=Finder)
            popup.add_separator()
            popup.add_command(label='Start', command=self.do_conversion)
            popup.add_command(label='Exit', command=self.EXITME)

            def do_popup(event):
                # display the popup menu
                try:
                    popup.tk_popup(event.x_root, event.y_root, 0)
                finally:
                    # make sure to release the grab (Tk 8.0a1 only)
                    popup.grab_release()

            self.bind("<Button-3>", do_popup)

        def EXITME(self):
            YourGUI.destroy(self)

        def startclick(self):
            
            x1 = threading.Thread(target=self.do_conversion, daemon=True)
            x1.start()   
        def do_conversion(self):

     
            if self.cmb.get() == "Left Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                    
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:
                    
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                while running:
                    pyautogui.FAILSAFE = False
                    pyautogui.click(x, y)
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        running = False
                        
                    
                    
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
                                
            elif self.cmb.get() == "Right Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:

                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                        
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                    time.sleep(int(self.inputdelayentry.get()))
                               

            
                    num= int(self.inputdelayentry.get())
                    start_time = datetime.datetime.now()
                    while (datetime.datetime.now() - start_time).total_seconds() < num:
                        
                        if keyboard.is_pressed(self.inputhotkey.get()):
                            exit(0)
                        else:
                            pass
                    
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
                    
            

            def action():
                YourGUI.destroy()


        def getdelay(self):
            tx = self.getinputdelayentry.get()

        def do_hotkey(self):
            hotkey = self.inputhotkey.get()

    if __name__ == '__main__':
        your_gui = YourGUI()
        your_gui.geometry("+300+300")
        your_gui.attributes("-topmost", True)
        your_gui.title('AutoClicker')  # Set title
        try:
            your_gui.iconbitmap('favicon.ico')
        except:
            pass
        your_gui.resizable(False, False)
        your_gui.configure(background="#ebdbff")
        your_gui.mainloop()
    time.sleep(0)


x = threading.Thread(target=MAINWINDOW_NEWSTYLE, daemon=True)
x.start()
def OldStyleGUI():
    class YourGUI(tk.Tk):
        def __init__(self):
            # inherit tkinter's window methods
            tk.Tk.__init__(self)
            # Enter X field and label ⬇
            tk.Label(self, text="ENTER Y:", background="#ebdbff").grid(row=0, column=2)
            self.inputX = tk.Entry(self)
            self.inputX.grid(row=0, column=1)
            # Enter Y field and label ⬇
            tk.Label(self, text="ENTER X:", background="#ebdbff").grid(row=0, column=0)
            self.inputY = tk.Entry(self)
            self.inputY.grid(row=0, column=3)
            
            self.cmb = ttk.Combobox(self, width="10", values=("Left Click","Right Click"))


            class TableDropDown(ttk.Combobox):
                def __init__(self, parent):
                    self.current_table = tk.StringVar() # create variable for table
                    ttk.Combobox.__init__(self, parent)#  init widget
                    self.config(textvariable = self.current_table, state = "readonly", values = ["Customers", "Pets", "Invoices", "Prices"])
                    self.current(0) # index of values for current table
                    self.place(x = 50, y = 50, anchor = "w") # place drop down box

            ttk.Label(self, text="""Choose the left or
right mouse button""", background="#ebdbff", anchor=E).grid(row=1, column=0)
            self.cmb.grid(row=1, column=1, sticky="ew")
            self.cmb.current(0)


            
            # Start Button ⬇
            tk.Button(self, text="start", fg='green', command=self.do_conversion).grid(row=3, column=0, columnspan=2)
            # close button ⬇
            tk.Button(self, text="exit!", fg='red', command=self.EXITME).grid(row=4, column=0, columnspan=2)

            self.inputhotkey = tk.Entry(self)
            self.inputhotkey.grid(row=1, column=3, columnspan=1)
            tk.Button(self, text="   SET   ", fg='#ffbb1b', command=self.do_hotkey).grid(row=3, column=3, columnspan=4)

            def callback():
                webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

            def callback2():
                webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

            tk.Button(self, text="ABOUT", command=callback).grid(row=4, column=3)

            def clicked3():
                your_gui.destroy()
                pyautogui.PAUSE = 0.50
                pyautogui.FAILSAFE = True

                things = []
                root = Tk()
                root.geometry("500x350")

                list_box = Listbox(root, font=(12))
                list_box.config(width=30, height=18)
                list_box.place(x=0, y=0)

                run_btn = Button(root, text="Run List", command=lambda: run_list(), font=(12))
                run_btn.place(x=350, y=15)
                run_btn.config(width=15)

                del_btn = Button(root, text="Delete", command=lambda: delete(list_box), font=(12))
                del_btn.place(x=350, y=90)
                del_btn.config(width=15)

                add_btn = Button(root, text="Add", command=lambda: add(), font=(12))
                add_btn.place(x=350, y=50)
                add_btn.config(width=15)

                x_txt = StringVar()
                y_txt = StringVar()

                x_label = Label(root, text="x", font=(12))
                x_label.place(x=320, y=150)

                x = Entry(root, textvariable=x_txt)
                x.place(x=350, y=150)

                x_txt.set('')
                y_label = Label(root, text="y", font=(12))
                y_label.place(x=320, y=170)

                y = Entry(root, textvariable=y_txt)
                y.place(x=350, y=170)
                y_txt.set('')

                def add():
                    content_x = x_txt.get()
                    content_y = y_txt.get()
                    closed_str = [content_x, content_y]
                    things.append(closed_str)
                    list_box.delete(0, 'end')
                    for i in range(len(things)):
                        list_box.insert(END, things[i])

                def run_list():
                    x_cords = [item[0] for item in things]
                    y_cords = [item[1] for item in things]

                    for i in range(len(things)):
                        screenWidth, screenHeight = pyautogui.size()
                        currentMouseX, currentMouseY = pyautogui.position()
                        pyautogui.moveTo(int(x_cords[i]), int(y_cords[i]))
                        # print("Gonna Click",x_cords[i],y_cords[i])
                        pyautogui.click()

                def delete(listbox):
                    global things
                    # Delete from Listbox
                    selection = list_box.curselection()
                    list_box.delete(selection[0])
                    # Delete from list that provided it
                    value = eval(list_box.get(selection[0]))
                    ind = things.index(value)
                    del (things[ind])

                popup = Menu(root, tearoff=0)
                popup.add_command(label='Run list', command=run_list)
                popup.add_command(label='Exit', command=self.EXITME)

                def do_popup(event):
                    # display the popup menu
                    try:
                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        # make sure to release the grab (Tk 8.0a1 only)
                        popup.grab_release()

                root.bind("<Button-3>", do_popup)

                root.title("AutoClicker - list of coordinates")
                try:
                    root.iconbitmap('favicon.ico')
                
                except:
                    pass
                root.resizable(False, False)
                root.attributes("-topmost", True)
                root.mainloop()
            def Finder():
                try:
                    os.startfile("MousePos.exe")
                except:
                    messagebox.showerror("ERROR", "MousePos.exe is missing")
                    pass

            tk.Button(self, text="List Coordinates", command=clicked3).grid(row=4, column=2,sticky="ew")
            tk.Button(self, text="Find Coordinates", command=Finder).grid(row=3, column=2, sticky="ew")

            def clicked():
                os.startfile("AutoClickerContactPage.exe")

            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('259x94')
                try:
                    window.iconbitmap('favicon.ico')
                except:
                    pass
                window.resizable(False, False)
                window.geometry("+0+0")
                window.attributes("-topmost", True)


                def callBackFunc():
                    your_gui.overrideredirect(True)
                    window.destroy()

                def ExitWindow():
                    window.destroy()

                def Full_screen():
                    your_gui.attributes('-fullscreen', True)
                    your_gui.bind('<Escape>', lambda e: root.destroy())
                    window.destroy()
                def Exit_Full_Screen():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)
                def Show_Title_bar():
                    python = sys.executable
                    os.execl(python, python, * sys.argv)

                ttk.Label(window, text="Settings").grid(column=0, row=1, sticky="ew")
                Button(window, text="               Exit Settings               ", command=ExitWindow).grid(column=0, row= 6)
                Button(window, text="‍‍FullScreen", command=Full_screen).grid(column=0, row=3, sticky="ew")
                Button(window, text="Exit FullScreen", command=Exit_Full_Screen).grid(column=1, row=3, sticky="ew")
                Button(window, text="Hide Title Bar ", command=callBackFunc).grid(column=0, row=5, sticky="ew")
                Button(window, text="Show Title Bar", command=Show_Title_bar).grid(column=1, row=5, sticky="ew")
                Button(window, text="Restart program", command=Show_Title_bar).grid(column=1, row=6, sticky="ew")

                popup = Menu(your_gui, tearoff=0)
                popup.add_command(label="FullScreen", command=Full_screen)
                popup.add_command(label="Exit FullScreen", command=Exit_Full_Screen)
                popup.add_command(label="Hide Title Bar", command=callBackFunc)
                popup.add_command(label="Show Title Bar", command=Show_Title_bar)
                popup.add_command(label="Restart program", command=Show_Title_bar)
                popup.add_command(label="Exit Settings", command=ExitWindow)

                def do_popup(event):

                    try:

                        popup.tk_popup(event.x_root, event.y_root, 0)
                    finally:
                        popup.grab_release()

                window.bind("<Button-3>", do_popup)

                window.mainloop()


            def OpenModernWindow():
                your_gui.destroy()
                MAINWINDOW_NEWSTYLE()

            def clicked2():
                try:
                    os.startfile("AutoClickerMegaSpam.exe")
                except:
                    messagebox.showerror("Error", "AutoClickerMegaSpam.exe is missing")
                    pass

            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='About', command=callback)
            new_item.add_command(label='Github Page', command=callback2)
            new_item.add_command(label='List Coordinates', command=clicked3)
            new_item.add_command(label='Version Number', command=NOTIFICATION)
            new_item.add_command(label='Modern Style', command=OpenModernWindow)
            new_item.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            new_item.add_command(label='Coordinates Finder', command=Finder)
            new_item.add_command(label='Settings', command=settings)
            new_item.add_separator()
            new_item.add_command(label='Start', command=self.do_conversion)
            new_item.add_command(label='Exit', command=self.EXITME)
            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            new_item2.add_command(label='Contact', command=clicked)
            menu.add_cascade(label='Help', menu=new_item2)
            popup = Menu(self, tearoff=0)
            popup.add_command(label="About", command=callback) 
            popup.add_command(label='GitHub Page', command=callback2)
            popup.add_command(label='Auto Clicker Mega Spam', command=clicked2)
            popup.add_command(label='Version Number', command=NOTIFICATION)
            popup.add_command(label='Modern Style', command=OpenModernWindow)
            popup.add_command(label='Settings', command=settings)
            popup.add_command(label='List of coordinates', command=clicked3)
            popup.add_command(label='Find Coordinates', command=Finder)
            popup.add_separator()
            popup.add_command(label='Start', command=self.do_conversion)
            popup.add_command(label='Exit', command=self.EXITME)

            def do_popup(event):
                # display the popup menu
                try:
                    popup.tk_popup(event.x_root, event.y_root, 0)
                finally:
                    # make sure to release the grab (Tk 8.0a1 only)
                    popup.grab_release()

            self.bind("<Button-3>", do_popup)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#ebdbff").grid(row=1, column=2)

        def EXITME(self):
            YourGUI.destroy(self)


        def do_conversion(self):
            if self.cmb.get() == "Left Click":
                y = self.inputY.get()
                x = self.inputX.get()
                    
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:
                    
                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                    # strtoint("crashmE!")
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(x, y)
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break
            elif self.cmb.get() == "Right Click":
                
                y = self.inputY.get()
                x = self.inputX.get()
                running = True
                try:
                    
                    x = int(x)
                    y = int(y)
                except:

                    messagebox.showerror('Invalid point', 'Invalid point')
                    YourGUI.destroy(self)
                    # strtoint("crashmE!")
                        
                while running:
                    pyautogui.FAILSAFE = False # disables the fail-safe
                    pyautogui.click(button='right')
                    pyautogui.click(x, y)
                     
                    
                    if keyboard.is_pressed(self.inputhotkey.get()):
                        break


        def do_hotkey(self):
            hotkey = self.inputhotkey.get()

    if __name__ == '__main__':
        your_gui = YourGUI()
        your_gui.geometry("+300+300")
        your_gui.attributes("-topmost", True)
        your_gui.title('AutoClicker')  # Set title
        try:
            your_gui.iconbitmap('favicon.ico')
        except:
            pass
        your_gui.resizable(False, False)
        your_gui.configure(background="#ebdbff")
        your_gui.mainloop()
    time.sleep(0)


