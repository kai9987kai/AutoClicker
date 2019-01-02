import pyautogui
import time
import tkinter as tk
import webbrowser
from tkinter import *
from tkinter import messagebox
import keyboard
from win32api import *
from win32gui import *
import win32con
import sys, os
import struct

def NOTIFICATION():
    class WindowsBalloonTip:
        def __init__(self, title, msg):
            message_map = {
                win32con.WM_DESTROY: self.OnDestroy,
            }
            # Register the Window class.
            wc = WNDCLASS()
            hinst = wc.hInstance = GetModuleHandle(None)
            wc.lpszClassName = "PythonTaskbar"
            wc.lpfnWndProc = message_map  # could also specify a wndproc.
            classAtom = RegisterClass(wc)
            # Create the Window.
            style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
            self.hwnd = CreateWindow(classAtom, "Taskbar", style, \
                                     0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                                     0, 0, hinst, None)
            UpdateWindow(self.hwnd)
            iconPathName = os.path.abspath(os.path.join(sys.path[0], "favicon.ico"))
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            try:
                hicon = LoadImage(hinst, iconPathName, \
                                  win32con.IMAGE_ICON, 0, 0, icon_flags)
            except:
                hicon = LoadIcon(0, win32con.IDI_APPLICATION)
            flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
            nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, hicon, "tooltip")
            Shell_NotifyIcon(NIM_ADD, nid)
            Shell_NotifyIcon(NIM_MODIFY, \
                             (self.hwnd, 0, NIF_INFO, win32con.WM_USER + 20, \
                              hicon, "Balloon  tooltip", msg, 200, title))
            # self.show_balloon(title, msg)
            time.sleep(10)
            DestroyWindow(self.hwnd)

        def OnDestroy(self, hwnd, msg, wparam, lparam):
            nid = (self.hwnd, 0)
            Shell_NotifyIcon(NIM_DELETE, nid)


    def balloon_tip(title, msg):
        w = WindowsBalloonTip(title, msg)

    if __name__ == '__main__':
        balloon_tip("AutoClicker", "V1.0")

class Coordinates():
    replayBtn = (100, 350)

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

        def callback3():
            webbrowser.open_new(r"https://autoclicker.webstarts.com/index.html?r=20181122215206")

        tk.Button(self, text="ABOUT", command=callback).grid(row=4, column=1, columnspan=2)

        def clicked():
            messagebox.showinfo('CONTACT', 'Email: kai9987kai@gmail.com')

        # Menu Bar!! ⬇
        menu = Menu(self)
        new_item = Menu(menu)
        new_item.add_command(label='ABOUT', command=callback)
        new_item.add_command(label='GITHUB PAGE', command=callback2)
        new_item.add_command(label='CONTACT', command=clicked)
        new_item.add_command(label='VERSION NUMBER', command=NOTIFICATION)
        new_item.add_separator()
        new_item.add_command(label='START', command=self.do_conversion)
        new_item.add_command(label='EXIT', command=self.EXITME)
        menu.add_cascade(label='Menu', menu=new_item)
        new_item2 = Menu(menu)
        new_item2.add_command(label='Tutorial', command=callback3)
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
    your_gui.title('AutoClicker')  # Set title
    your_gui.iconbitmap('favicon.ico')  # Set icon
    your_gui.resizable(False, False)
    your_gui.configure(background="#ebdbff")
    your_gui.mainloop()
time.sleep(0)
