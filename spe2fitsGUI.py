#!/usr/bin/env python3

"""
batch mode, convert many .SPE to FITS
    select files ( overwrite, output dir )
    select dir ( overwrite, output dir )
watch dir event, auto convert .SPE to FITS
    listen dir ( replace prefix )
display?
image sub
"""

import sys
import os

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
#from tkinter import *
#from tkinter.ttk import *

#sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from spe2fits import SPE

def getFileBasename(nfile):
    print("getFilePath:", nfile)
    if hasattr(nfile, 'read'):
        return os.path.basename(nfile.name)
    return os.path.basename(nfile)

class Application(tk.Frame):
    def __init__(self, master = None):
        super().__init__(master)
        self.parent = master
        self.initUI()
        self.createWidgets()

    def initUI(self):
        self.parent.title("PI/WinViewer .SPE to FITS Converter")
        self.parent.geometry(self.screenAutoSize())
        self.pack(fill = tk.BOTH, expand = 1)
        self.style = ttk.Style()
        self.style.theme_use("default")

    def screenAutoSize(self):
        width = self.parent.winfo_screenwidth()
        height = self.parent.winfo_screenheight()
        self.show_width = int(width/2) if width > 800 else 400
        self.show_height = int(height/2) if height > 600 else 300
        return "{show_width}x{show_height}+{offsetx}+{offsety}".format(
                show_width = self.show_width,
                show_height = self.show_height,
                offsetx = int(width/4) if width > 800 else 100,
                offsety = int(height/4) if height > 600 else 80,
                )


    def createWidgets(self):
        self.chooseFile = tk.Button(self,
                text = "Convert Files...",
                fg="black", bg="white",
                command = self.chooseDialogFiles,
                )
        self.chooseFile.place(x=50, y=50)
        self.chooseFilePath = os.path.abspath(os.path.curdir)
        self.chooseFileOutDir = self.chooseFilePath

        self.chooseDir = tk.Button(self,
                text = "Convert Directory...",
                fg="black", bg="white",
                command = self.chooseDialogDir,
                )
        self.chooseDir.place(x=50, y=100)
        self.chooseDirPath = os.path.abspath(os.path.curdir)
        self.chooseDirOutDir = self.chooseDirPath

    def chooseDialogFiles(self):
        print("chooseDialogFiles")
        filenames = filedialog.askopenfilenames(
                defaultextension = '.SPE',
                filetypes = [('WinViewer Documents', '.SPE'), ('all files', '.*'),],
                parent = self.parent,
                title = "Select .SPE files",
                multiple = True,
                )
        print(filenames)
        if len(filenames) == 0:
            messagebox.showinfo("Select result", "No File Opened")
            return
        self.chooseFilePath = os.path.dirname(
                os.path.realpath(filenames[0])
                )
        print("select:", self.chooseFilePath)
        self.chooseFileOutDir = filedialog.askdirectory(
                initialdir = self.chooseFilePath,
                parent = self.parent,
                title = "Select output Directory",
                mustexist = False, # TODO turn it True
                )
        self.convertFiles(filenames, self.chooseFileOutDir)

    def chooseDialogDir(self):
        print("chooseDialogDir")
        pass

    def convertFiles(self, fileIter, outputDir):
        print("outputDir:", outputDir)
        for onefile in fileIter:
            speHandler = SPE(onefile)
            outPrefix = os.path.splitext(
                    os.path.join(
                        outputDir, getFileBasename(onefile)
                        )
                    )[0]
            print(outPrefix)
            # TODO make it async
            speHandler.spe2fits(
                    outPrefix = outPrefix,
                    )
        messagebox.showinfo("Convert Complete!", "see " + outputDir)

#        toplevel = tk.Toplevel()
#        newFrame = tk.Frame(toplevel, text = route)
#        newFrame.pack()

def main():
    root = tk.Tk()
    app = Application(master = root)
    root.mainloop()

if __name__ == '__main__':
    main()

