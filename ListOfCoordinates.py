from tkinter import *
import pyautogui

pyautogui.PAUSE = 0.50
pyautogui.FAILSAFE = True

things = []
root = Tk()
root.geometry("500x350")

list_box = Listbox(root ,font = (12))
list_box.config(width=30,height=18)
list_box.place(x=0,y=0)

run_btn = Button(root, text = "Run List", command = lambda: run_list() ,font = (12))
run_btn.place(x=350,y=15)
run_btn.config(width=15)

del_btn = Button(root, text = "Delete", command = lambda: delete(list_box),font = (12))
del_btn.place(x=350,y=90)
del_btn.config(width=15)

add_btn = Button(root, text = "Add", command = lambda: add(),font = (12))
add_btn.place(x=350,y=50)
add_btn.config(width=15)

x_txt = StringVar()
y_txt = StringVar()

x_label = Label(root, text="x",font = (12))
x_label.place(x=320,y=150)

x = Entry(root ,textvariable=x_txt)
x.place(x=350,y=150)

x_txt.set('')
y_label = Label(root, text="y",font = (12))
y_label.place(x=320,y=170)

y = Entry(root ,textvariable=y_txt)
y.place(x=350,y=170)
y_txt.set('')

def add():
    content_x=x_txt.get()
    content_y=y_txt.get()
    closed_str=[content_x,content_y]
    things.append(closed_str)
    list_box.delete(0,'end')
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
    del(things[ind])

root.mainloop()
