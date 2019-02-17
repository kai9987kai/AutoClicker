import win10toast
import pyautogui
import time
import tkinter as tk
import webbrowser
from tkinter import *
from tkinter import messagebox
import keyboard
from tkinter import ttk
import os


def NOTIFICATION():
    toaster = win10toast.ToastNotifier()
    toaster.show_toast("AutoClicker", "V2.0", duration=5, threaded=True)
    messagebox.showinfo('AutoClicker', 'V2.0')

def tutorial():
    window = Tk()
    window.title("Tutorial")
    window.geometry('750x100')
    tab_control = ttk.Notebook(window)
    tab1 = ttk.Frame(tab_control)
    tab2 = ttk.Frame(tab_control)
    tab_control.add(tab1, text='First Step')
    tab_control.add(tab2, text='Second Step')
    lbl1 = Label(tab1, anchor=W, text='First Get the coordinates download the software\n linked here ➡ http://www.adminsehow.com/wp-content/uploads/2012/03/MousePos.exe or use the python script inside the github project.')
    lbl1.grid(column=0, row=0)
    lbl2 = Label(tab2, text='Input the X and Y coordinates into the Z and Y boxes set a key as the stop key and press start you can use the stop key to stop the clicking')
    lbl2.grid(column=0, row=0)
    tab_control.pack(expand=1, fill='both')
    window.iconbitmap('favicon.ico')
    window.attributes("-topmost", True)
    window.resizable(False, False)
    window.geometry("+300+300")
    window.mainloop()

class Coordinates():
    replayBtn = (100, 350)
def MAINWINDOW_NEWSTYLE():
    class YourGUI(tk.Tk):
        def __init__(self):
            # inherit tkinter's window methods
            tk.Tk.__init__(self)
            # Enter X field and label ⬇
            ttk.Label(self, text="ENTER Y:", background="#ebdbff", anchor=E).grid(row=0, column=2)
            self.inputX = ttk.Entry(self)
            self.inputX.grid(row=0, column=1)
            # Enter Y field and label ⬇
            tk.Label(self, text="ENTER X:", background="#ebdbff").grid(row=0, column=0)
            self.inputY = ttk.Entry(self)
            self.inputY.grid(row=0, column=3)
            # Start Button ⬇
            ttk.Button(self, text="start", command=self.do_conversion).grid(row=3, column=0, columnspan=2)
            # close button ⬇
            ttk.Button(self, text="exit!", command=self.EXITME).grid(row=4, column=0, columnspan=2)
            self.inputhotkey = ttk.Entry(self)
            self.inputhotkey.grid(row=1, column=3, columnspan=1)
            ttk.Button(self, text="   SET   ", command=self.do_hotkey).grid(row=3, column=3, columnspan=4)

            def callback():
                webbrowser.open_new(r"https://kai9987kai.github.io/AutoClicker.html")

            def callback2():
                webbrowser.open_new(r"https://github.com/kai9987kai/AutoClicker")

            ttk.Button(self, text="ABOUT", command=callback).grid(row=4, column=3)

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
                root.title("AutoClicker - list of coordinates")
                root.iconbitmap('favicon.ico')
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

                root.mainloop()

            def clicked():
                os.startfile("AutoClickerContactPage.exe")
            def clicked2():
                os.startfile("AutoClickerMegaSpam.exe")

            ttk.Button(self, text="List Coordinates", command=clicked3).grid(row=4, column=2)

            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('260x50')
                window.iconbitmap('favicon.ico')
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

                ttk.Label(window, text="Settings").grid(column=0, row=0)
                ttk.Button(window, text="Close", command=ExitWindow).grid(column=3, row=1)

                chkValue = tk.BooleanVar()
                chkValue.set(False)

                chkExample = tk.Checkbutton(window, text='Hide Title Bar',
                                            var=chkValue, command=callBackFunc)
                chkExample.grid(column=0, row=1)
                chkValue2 = tk.BooleanVar()
                chkValue2.set(False)

                chkExample2 = tk.Checkbutton(window, text='FullScreen',
                                            var=chkValue2, command=Full_screen)
                chkExample2.grid(column=2, row=1)
                window.mainloop()
            def OpenOldWindow():
                your_gui.destroy()
                OldStyleGUI()


            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='ABOUT', command=callback)
            new_item.add_command(label='GITHUB PAGE', command=callback2)
            new_item.add_command(label='AUTO CLICKER MEGA SPAM', command=clicked2)
            new_item.add_command(label='VERSION NUMBER', command=NOTIFICATION)
            new_item.add_command(label='OLD STYLE GUI', command=OpenOldWindow)
            new_item.add_command(label='SETTINGS', command=settings)
            new_item.add_command(label='LIST OF COORDINATES', command=clicked3)
            new_item.add_separator()
            new_item.add_command(label='START', command=self.do_conversion)
            new_item.add_command(label='EXIT', command=self.EXITME)

            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            menu.add_cascade(label='Help', menu=new_item2)
            new_item2.add_command(label='Contact', command=clicked)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#ebdbff").grid(row=1, column=2)

        def EXITME(self):
            exit(0)  # crashed prog so it closes
            # strtoint("crashmE!")

        def do_conversion(self):
            y = self.inputY.get()
            x = self.inputX.get()

            def action():
                YourGUI.destroy()

            image = Image.open("favicon.png")
            menu = (item('Help', action), item('Close', action))
            icon = pystray.Icon("name", image, "test", menu)
            icon.run()

            running = True
            try:
                x = int(x)
                y = int(y)
            except:
                messagebox.showerror('Invalid point', 'Invalid point')
                exit(0)
                # strtoint("crashmE!")
            while running:
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
        your_gui.iconbitmap('favicon.ico')  # Set icon
        your_gui.resizable(False, False)
        your_gui.configure(background="#ebdbff")
        your_gui.mainloop()
    time.sleep(0)

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
                root.title("AutoClicker - list of coordinates")
                root.iconbitmap('favicon.ico')
                root.resizable(False, False)
                root.attributes("-topmost", True)
                root.mainloop()

            tk.Button(self, text="List of Coordinates", command=clicked3).grid(row=4, column=2)
            def clicked():
                os.startfile("AutoClickerContactPage.exe")



            def settings():
                window = Tk()
                window.title("Settings")
                window.geometry('260x50')
                window.iconbitmap('favicon.ico')
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

                ttk.Label(window, text="Settings").grid(column=0, row=0)
                ttk.Button(window, text="Close", command=ExitWindow).grid(column=3, row=1)

                chkValue = tk.BooleanVar()
                chkValue.set(False)

                chkExample = tk.Checkbutton(window, text='Hide Title Bar',
                                            var=chkValue, command=callBackFunc)
                chkExample.grid(column=0, row=1)
                chkValue2 = tk.BooleanVar()
                chkValue2.set(False)

                chkExample2 = tk.Checkbutton(window, text='FullScreen',
                                            var=chkValue2, command=Full_screen)
                chkExample2.grid(column=2, row=1)
                window.mainloop()
            def OpenModernWindow():
                your_gui.destroy()
                MAINWINDOW_NEWSTYLE()



            # Menu Bar!! ⬇
            menu = Menu(self)
            new_item = Menu(menu)
            new_item.add_command(label='ABOUT', command=callback)
            new_item.add_command(label='GITHUB PAGE', command=callback2)
            new_item.add_command(label='LIST OF COORDINATES', command=clicked3)
            new_item.add_command(label='VERSION NUMBER', command=NOTIFICATION)
            new_item.add_command(label='MODERN STYLE', command=OpenModernWindow)
            new_item.add_command(label='SETTINGS', command=settings)
            new_item.add_separator()
            new_item.add_command(label='START', command=self.do_conversion)
            new_item.add_command(label='EXIT', command=self.EXITME)
            menu.add_cascade(label='Menu', menu=new_item)
            new_item2 = Menu(menu)
            new_item2.add_command(label='Tutorial', command=tutorial)
            new_item2.add_command(label='Contact', command=clicked)
            menu.add_cascade(label='Help', menu=new_item2)
            self.config(menu=menu)
            tk.Label(self, text="Keyboard key to stop clicking:", background="#ebdbff").grid(row=1, column=2)



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
                messagebox.showerror('Invalid point', 'Invalid point')
                exit(0)
                # strtoint("crashmE!")
            while running:
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
        your_gui.iconbitmap('favicon.ico')  # Set icon
        your_gui.resizable(False, False)
        your_gui.configure(background="#ebdbff")
        your_gui.mainloop()
    time.sleep(0)
MAINWINDOW_NEWSTYLE()
