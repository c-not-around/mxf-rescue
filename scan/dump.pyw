# -*- coding: utf8 -*-


from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from os      import path


class HddDump:
    def __init__(self):
        # Main Form
        self.main_form = Tk()
        self.main_form.title("HDD Dump")
        self.main_form.resizable(width=False, height=False)
        self.main_form.wm_geometry("450x130")
        self.main_form.minsize(450, 130)
        # Target disk select
        self.dl_label = Label(self.main_form, text="Target disk:")
        self.dl_label.place(x=5, y=5, width=70, height=15)
        self.disk_list = Listbox(self.main_form)
        self.disk_list.place(x=5, y=20, width=70, height=100)
        # Destination path select
        self.dp_label = Label(self.main_form, text="Destination path:")
        self.dp_label.place(x=80, y=5, width=300, height=15)
        self.dst_path = Entry(self.main_form)
        self.dst_path.place(x=80, y=20, width=300)
        self.dst_select = Button(self.main_form, text="Select", command=self.dst_select_click)
        self.dst_select.place(x=385, y=20, width=60, height=self.dst_path["width"])
        # Offsets
        self.os_label = Label(self.main_form, text="Offsets:")
        self.os_label.place(x=80, y=45, width=300, height=15)
        self.offset_list = Text(self.main_form, width=54, height=3, font=("consolas",10), wrap=NONE)
        self.offset_list.place(x=80, y=60, width=300, height=55)
        self.make_dump = Button(self.main_form, text="Dump", command=self.make_dump_click)
        self.make_dump.place(x=385, y=60, width=60, height=self.dst_path["width"])
    
    # Destination path select button click handler
    def dst_select_click(self):
        pd = filedialog.askdirectory()
        if pd:
            self.dst_path.delete(0, END)
            self.dst_path.insert(0, pd.replace("/", "\\"))
    
    # Scan start button click
    def make_dump_click(self):
        disk = self.disk_list.curselection()
        path = self.dst_path.get()
        text = self.offset_list.get()
        regs = [[int(o, 0), int(s, 0)] for o, s in [p.split(",") for p in text.split(";")]]
        dump = open("\\\\.\\"+disk, "rb")
        for o, s in regs:
            adr = o & 0xFFFFFFFFFFFFFE00
            ost = o - adr
            dump.seek(adr)
            block = dump.read(s)[ost:]
            f = open("%s\\%016X.dump" % (path, o), "wb")
            f.write(block)
            f.close()
        dump.close()
        messagebox.showinfo(title="Done", message="Done!")
    
    # Run App
    def run(self):
        # Make disk list
        self.disks = ["%s:" % i for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if path.exists("%s:" % i)]
        for disk in self.disks:
            self.disk_list.insert(END, disk)
        # Run main form dispatch message cycle
        self.main_form.mainloop()


HddDump().run()
