# -*- coding: utf8 -*-


from tkinter   import *
from tkinter   import filedialog
from tkinter   import messagebox
from tkinter   import ttk
from threading import *
from time      import sleep
from datetime  import datetime, timedelta
from os        import path
from psutil    import disk_usage


# HDD constants
HDD_SECTOR_SIZE    = 512
# MXF record keys
FILE_HEADER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x02, 0x04, 0x00]
FILE_FOOTER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x04, 0x04, 0x00]
FRAME_HEADER_START = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x04, 0x01, 0x01, 0x00]
FRAME_DATA_START   = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x06, 0x0E, 0x06, 0x0D, 0x03, 0x19, 0x01, 0x45, 0x00]
FRAME_FOOTER_START = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x16, 0x04, 0x03, 0x00]
# MXF record sizes
FILE_HEADER_SIZE   = 11264
FILE_FOOTER_SIZE   = 10800
FRAME_HEADER_SIZE  = 512
FRAME_DATA_SIZE    = 7452672
FRAME_FOOTER_SIZE  = 36352
FRAME_SIZE         = FRAME_HEADER_SIZE + FRAME_DATA_SIZE + FRAME_FOOTER_SIZE
# Offsets of duration in file header
DURATION_OFFSETS   = [0x0BC8, 0x0C27, 0x0CEF, 0x0D6F, 0x15F2, 0x0E37, 0x0EB7, 0x0F7F, 0x0FFF, 0x10C7, 0x1147, 0x120F,
                      0x128F, 0x1357, 0x13D7, 0x1593, 0x16BA, 0x173A, 0x1802, 0x1882, 0x194A, 0x19CA, 0x1A92, 0x1B12,
                      0x1BDA, 0x1C5A, 0x1D22, 0x1DA2]
# Offsets of timestamps in file header, file footer
TIMESTAMPS_OFFSETS = [0x0C1B, 0x15E6]


# load file header, file footer
fh = open("header.mxf", "rb")
fh.seek(0)
file_header = fh.read(FILE_HEADER_SIZE)
fh.close()
fh = open("footer.mxf", "rb")
fh.seek(0)
file_footer = fh.read(FILE_FOOTER_SIZE)
fh.close()


# key compare
def key_cmp(key, pattern):
    for i in range(16):
        if key[i] != pattern[i]:
            return False
    return True
# convert from bcd
def from_bcd(x):
    return 10 * (x >> 4) + (x & 0x0F)
# read block from target disk
def get_block(fs, offset, size=HDD_SECTOR_SIZE):
    adr = offset & 0xFFFFFFFFFFFFFE00
    ost = offset - adr
    try:
        fs.seek(adr)
    except:
        raise Exception("seek() error with offset = 0x%016X" % offset)
    return fs.read(size)[ost:]
# get int value from block
def get_value(buffer, offset, size):
    value = 0
    for i in range(size):
        value <<= 8
        value |= buffer[offset+i]
    return value
# find mxf records in block
def scan_record(fs, offset):
    block = get_block(fs, offset)
    if key_cmp(block, FRAME_HEADER_START):
        n = get_value(block, 0x0016, 5)
        h = from_bcd(block[0x040])
        m = from_bcd(block[0x03F])
        s = from_bcd(block[0x03E])
        f = from_bcd(block[0x03D])
        offset += FRAME_HEADER_SIZE
        block = get_block(fs, offset)
        if key_cmp(block, FRAME_DATA_START):
            offset += FRAME_DATA_SIZE
            block = get_block(fs, offset)
            if key_cmp(block, FRAME_FOOTER_START):
                return "FRAME_FULL", [n, h, m, s, f]
            else:
                return "FRAME_DATA", [n, h, m, s, f]
        else:
            return "FRAME_HEADER", [n, h, m, s, f]
    elif key_cmp(block, FILE_HEADER_START):
        block = get_block(fs, offset, 4096)
        dur   = get_value(block, 0x0BC8, 4)
        ts    = get_value(block, 0x0C1B, 4)
        pos   = get_value(block, 0x002C, 8)
        return "FILE_HEADER", [dur, ts, pos]
    elif key_cmp(block, FILE_FOOTER_START):
        block = get_block(fs, offset, 4096)
        dur   = get_value(block, 0x0BC8, 4)
        ts    = get_value(block, 0x0C1B, 4)
        pos   = get_value(block, 0x002C, 8)
        return "FILE_FOOTER", [dur, ts, pos]
    return "NONE", []
# convert to timestamp
def to_timestamp(h, m, s, f):
    return f + 25 * (s + 60 * (m + 60 * h))
# convert from timestamp
def from_timestamp(ts):
    f = ts % 25
    ts //= 25
    s = ts % 60
    ts //= 60
    m = ts % 60
    h = ts // 60
    return [h, m, s, f]
# insert value to buffer
def set_value(fs, base, offsets, value, length):
    buffer = [0 for i in range(length)]
    for i in range(length-1, -1, -1):
        buffer[i] = value & 0xFF
        value >>= 8
    for offset in offsets:
        fs.seek(base+offset)
        fs.write(bytes(buffer))
# write file header, file footer and set metadata to destination file
def complete_file(fs, f_count, f_timestamp, f_fname):
    pos = FILE_HEADER_SIZE + f_count * FRAME_SIZE
    # file header
    fs.seek(0)
    fs.write(file_header)
    set_value(fs, 0, DURATION_OFFSETS,   f_count,     4)
    set_value(fs, 0, [0x002C],           pos,         8)
    set_value(fs, 0, TIMESTAMPS_OFFSETS, f_timestamp, 4)
    # file footer
    fs.seek(pos)
    fs.write(file_footer)
    set_value(fs, pos, DURATION_OFFSETS,         f_count,     4)
    set_value(fs, pos, [0x001C, 0x002C, 0x2A23], pos,         8)
    set_value(fs, pos, TIMESTAMPS_OFFSETS,       f_timestamp, 4)
    fs.close()
# Timedelta to string
def td_str(td):
    s = td % 60
    td //= 60
    m = td % 60
    h = td // 60
    return "%02i:%02i:%02i" % (h, m, s)

class MxfHddScaner:
    def __init__(self):
        # Main Form
        self.main_form = Tk()
        self.main_form.title("MXF HDD Scaner")
        #self.main_form.resizable(width=False, height=True)
        self.main_form.wm_geometry("450x500")
        self.main_form.minsize(450, 500)
        self.main_form.bind("<Destroy>", self.main_form_close)
        # Target disk select
        self.dl_label = Label(self.main_form, text="Target disk:")
        self.dl_label.place(x=5, y=5, width=70, height=15)
        self.disk_list = Listbox(self.main_form)
        self.disk_list.place(x=5, y=20, width=70, height=100)
        self.disk_list.bind("<<ListboxSelect>>", self.disk_list_select)
        # Destination path select
        self.dp_label = Label(self.main_form, text="Destination path:")
        self.dp_label.place(x=80, y=5, width=300, height=15)
        self.dst_path = Entry(self.main_form)
        self.dst_path.place(x=80, y=20, width=300)
        self.dst_select = Button(self.main_form, text="Select", command=self.dst_select_click)
        self.dst_select.place(x=385, y=20, width=60, height=self.dst_path["width"])
        # Offset select
        self.os_label = Label(self.main_form, text="Offset:")
        self.os_label.place(x=80, y=45, width=300, height=15)
        self.start_offset = Entry(self.main_form)
        self.start_offset.place(x=80, y=60, width=300)
        self.start_scan = Button(self.main_form, text="Start", command=self.start_scan_click)
        self.start_scan.place(x=385, y=60, width=60, height=self.start_offset["width"])
        # Dummy mode
        self.dummy_mode = IntVar()
        self.d_mode = Checkbutton(self.main_form, text="Log only", variable=self.dummy_mode)
        self.d_mode.place(x=80, y=83, width=65, height=15)
        # Time progress
        self.et_label = Label(self.main_form, text="Elapsed: 00:00:00")
        self.et_label.place(x=180, y=83, width=90, height=15)
        self.rt_label = Label(self.main_form, text="Remainig: 00:00:00")
        self.rt_label.place(x=290, y=83, width=100, height=15)
        # Scan progress
        self.scan_progress = ttk.Progressbar(self.main_form, orient="horizontal",value=0)
        self.scan_progress.place(x=80, y=100, width=365, height=20)
        # Scan log
        self.sl_panel = Frame(self.main_form)
        self.sl_panel.pack(side=BOTTOM, fill=BOTH, expand=1, padx=[5, 5], pady=[125, 5])
        self.scan_log = Text(self.sl_panel, width=54, height=32, font=("consolas",10), wrap=NONE, state="disabled")
        self.scan_log.pack(side=LEFT, fill=BOTH, expand=1)
        self.scan_log_scroll = Scrollbar(self.sl_panel, command=self.scan_log.yview, orient=VERTICAL)
        self.scan_log_scroll.pack(anchor=SE, fill=Y, expand=1)
        self.scan_log["yscrollcommand"] = self.scan_log_scroll.set 
        self.scan_log_menu = Menu(self.scan_log, tearoff=False)
        self.scan_log_menu.add_command(label="Copy", command=self.scan_log_menu_copy)
        self.scan_log_menu.add_command(label="Save", command=self.scan_log_menu_save)
        self.scan_log_menu.add_command(label="Clear", command=self.scan_log_menu_clear)
        self.scan_log.bind("<Button-3>", self.scan_log_menu_handler)
        self.scan_log.tag_configure("def", background="#FFFFFF", foreground="#000000")
        self.scan_log.tag_configure("ok",  background="#FFFFFF", foreground="#008000")
        self.scan_log.tag_configure("com", background="#FFFFFF", foreground="#0000FF")
        self.scan_log.tag_configure("wrn", background="#FFFFFF", foreground="#FF8027")
        self.scan_log.tag_configure("bad", background="#FFFFFF", foreground="#FF0000")
        self.scan_log.tag_configure("fhf", background="#FFFFFF", foreground="#FF00FF")

    # Disk select handler
    def disk_list_select(self, event):
        sel = event.widget.curselection()
        if len(sel):
            index = sel[0]
            self.target_disk = "\\\\.\\" + self.disks[index]
            self.tg_disk_size = disk_usage(self.disks[index]+"\\").total

    # Destination path select button click handler
    def dst_select_click(self):
        pd = filedialog.askdirectory()
        if pd:
            self.dst_path.delete(0, END)
            self.dst_path.insert(0, pd.replace("/", "\\"))

    # Scan start button click
    def start_scan_click(self):
        if self.scan_state == "RUN":
            self.scan_log_append("scan stop.\n")
            self.start_scan["state"] = "disabled"
            self.scan_state = "IDLE"
        else:
            if self.target_disk != None:
                dst = self.dst_path.get()
                if path.isdir(dst):
                    if dst[0] != self.target_disk[4]:
                        self.destination = dst
                        # Get start offset
                        o = self.start_offset.get()
                        try:
                            self.offset = int(o)
                        except:
                            self.offset = 0
                        self.start_offset.delete(0, END)
                        self.start_offset.insert(END, str(self.offset))
                        # Reset scan progress
                        self.scan_progress["value"] = 0
                        # Clear scan log
                        self.scan_log_append("scan disk %s start by offset 0x%016X\n" % (self.target_disk[4:], self.offset))
                        # Disable UI
                        self.disk_list["state"]  = "disabled"
                        self.dst_path["state"]   = "disabled"
                        self.dst_select["state"] = "disabled"
                        # Change button function
                        self.start_scan["text"]  = "Stop"
                        # Enable scan task
                        self.scan_state = "RUN"
                    else:
                        messagebox.showerror(title="error", message="Target disk and Destination path located on one disk!")
                else:
                    messagebox.showerror(title="error", message="Destination path not selected!")
            else:
                messagebox.showerror(title="error", message="Target disk not selected!")
    
    # Scan log context Menu
    def scan_log_menu_handler(self, event):
        self.scan_log_menu.post(event.x_root, event.y_root)

    # Scan log copy
    def scan_log_menu_copy(self):
        self.scan_log.event_generate("<<Copy>>")

    # Scan log save to file
    def scan_log_menu_save(self):
        lf = filedialog.asksaveasfile(mode='w', defaultextension=".log")
        if lf:
            fd = open(lf.name, "wt")
            fd.write(self.scan_log.get("1.0", END))
            fd.close()

    # Scan log clear
    def scan_log_menu_clear(self):
        self.scan_log["state"] = "normal"
        self.scan_log.delete('1.0', END)
        self.scan_log["state"] = "disabled"
    
    # Scan log append
    def scan_log_append(self, text, atr="def"):
        self.scan_log["state"] = "normal"
        self.scan_log.insert(END, text, atr)
        self.scan_log["state"] = "disabled"
        self.scan_log.see(END)
    
    # Main form closing handler
    def main_form_close(self, event):
        if event.widget == self.main_form and self.scan_thread is not None:
            self.scan_state = "COMPLETED"
            while self.scan_state != "EXIT":
                pass
            self.scan_thread = None

    # Scan
    def scan_sub_task(self):
        m_dummy     = self.dummy_mode.get()
        ds          = self.tg_disk_size - self.offset
        step        = ds / 1000.0
        pos         = 0
        s_time      = datetime.now()
        #
        f_offset    = self.offset
        l_offset    = None
        f_count     = 0
        f_prev_no   = None
        f_timestamp = None
        f_fname     = None
        f_disk      = open(self.target_disk, "rb")
        f_dst_fd    = None
        while self.scan_state == "RUN":
            r_type, r_md = scan_record(f_disk, f_offset)
            if r_type == "FRAME_FULL":
                n, h, m, s, f = r_md
                # Complete file, if this frame is last in series
                if (f_prev_no != None) and ((n-1) != f_prev_no):
                    if m_dummy == 0:
                        complete_file(f_dst_fd, f_count, f_timestamp, f_fname)
                    self.scan_log_append("%i frames saved to file <%s>\n\r\n" % (f_count, f_fname), "com")
                    f_count   = 0
                    f_prev_no = None
                    f_fname   = None
                    l_offset  = None
                # Init first frame in current series
                if f_count == 0:
                    f_timestamp = to_timestamp(h, m, s, f)
                    f_fname     = "%s\\%016X.mxf" % (self.destination, f_offset)
                    if m_dummy == 0:
                        f_dst_fd    = open(f_fname, "wb")
                    l_offset    = f_offset
                # Copy frame to destinaton file
                if m_dummy == 0:
                    f_disk.seek(f_offset)
                    buffer = f_disk.read(FRAME_SIZE)
                    f_dst_fd.seek(FILE_HEADER_SIZE+f_count*FRAME_SIZE)
                    f_dst_fd.write(buffer)
                # Print frame info
                self.scan_log_append("%016X: FRAME_FULL no=%i %02i:%02i:%02i.%02i\n" % (f_offset, n, h, m, s, f*4), "ok")
                # to next frame
                f_count  += 1
                f_prev_no = n
                f_offset += FRAME_SIZE
            else:
                if r_type == "FRAME_DATA" or r_type == "FRAME_HEADER":
                    n, h, m, s, f = r_md
                    self.scan_log_append("%016X: %s no=%i %02i:%02i:%02i.%02i\n" % (f_offset, r_type, n, h, m, s, f*4), "wrn")
                elif r_type == "FILE_HEADER" or r_type == "FILE_FOOTER":
                    d, t, p = r_md
                    h, m, s, f = from_timestamp(t)
                    self.scan_log_append("%016X: %s frames=%i timecode=%02i:%02i:%02i.%02i FP=0x%016X\n" % (f_offset, r_type, d, h, m, s, f*4, p), "fhf")
                if f_count != 0:
                    if m_dummy == 0:
                        complete_file(f_dst_fd, f_count, f_timestamp, f_fname)
                    self.scan_log_append("%i frames saved to file <%s>\n\r\n" % (f_count, f_fname), "com")
                    f_count   = 0
                    f_prev_no = None
                    f_fname   = None
                    l_offset  = None
                f_offset += 256
            # Progress update
            ps = (f_offset - self.offset) // step 
            if ps > pos:
                # Progress
                pos = ps
                per = (f_offset - self.offset) / ds
                self.scan_progress["value"] = per * 100.0
                # Time
                e_time = (datetime.now() - s_time).total_seconds()
                r_time = e_time * (1.0 / per - 1.0)
                self.et_label["text"] = "Elapsed: %s" % td_str(e_time)
                self.rt_label["text"] = "Remainig: %s" % td_str(r_time)
            # Check end of disk
            if f_offset >= self.tg_disk_size:
                self.scan_progress["value"] = 100
                self.scan_log_append("scan end.\n")
                self.scan_state = "IDLE"
                l_offset = 0
        f_disk.close()
        self.offset = l_offset if l_offset != None else f_offset
        self.start_offset.delete(0, END)
        self.start_offset.insert(0, str(self.offset))
    
    # Scan task
    def scan_task(self):
        while self.scan_state != "COMPLETED":
            while self.scan_state == "IDLE":
                sleep(0.1)
            # SCAN
            if self.scan_state == "RUN":
                self.scan_sub_task()
                # Save last offset
                fd = open("prev_offset.txt", "wt")
                fd.write(str(self.offset))
                fd.close()
                # Stop -> enable UI
                self.disk_list["state"]  = "normal"
                self.dst_path["state"]   = "normal"
                self.dst_select["state"] = "normal"
                self.start_scan["state"] = "normal"
                self.start_scan["text"]  = "Start"
        self.scan_state = "EXIT"
    
    # Run App
    def run(self):
        # Init fields
        self.target_disk  = None
        self.tg_disk_size = 0
        self.destination  = None
        self.offset       = 0
        self.scan_state   = "IDLE"
        # Make disk list
        self.disks = ["%s:" % i for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if path.exists("%s:" % i)]
        for disk in self.disks:
            self.disk_list.insert(END, disk)
        # Prev offset load
        if path.isfile("prev_offset.txt"):
            fd = open("prev_offset.txt", "rt")
            po = fd.read()
            fd.close()
            self.start_offset.delete(0, END)
            self.start_offset.insert(0, po)         
        # Scan thread
        self.scan_thread = Thread(target=self.scan_task, args=(), daemon=True)
        self.scan_thread.start()
        # Run main form dispatch message cycle
        self.main_form.mainloop()


MxfHddScaner().run()#1213385728
