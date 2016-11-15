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
import traceback
from pathlib import Path # New in version 3.4

import tkinter as tk
from tkinter import filedialog, messagebox, Checkbutton
from tkinter import ttk
#from tkinter import *
#from tkinter.ttk import *

#sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from spe2fits import SPE

def yieldFilesUnderDirectory(dirname, match = None):
    """ yield all file names under the directory 'dirname' recursively
    return absolute path
    """
    print("test directory:", dirname)
    dirnamePath = Path(dirname)
    matched = dirnamePath.rglob(match)
    for match in matched:
        yield str(match.absolute())

def getOutputPrefix(oldname, outputDir, oldPrefix):
    """ get output path prefix
    oldname: filename to be converted
    outputDir: output directory name
    oldPrefix: file's path will need to cut the prefix first
    e.g.: path/b.ext -> output/b ( prefix is path )
    e.g.: path/to/c.ext -> output/to/c ( prefix is path )
    """
    # XXX is os.path.abspath necessary ?
    if oldPrefix is not None:
        relpath = os.path.relpath( os.path.abspath(oldname),
                os.path.abspath(oldPrefix) )
    else:
        relpath = os.path.basename(oldname)
    relpath = os.path.splitext(relpath)[0]
    print("relpath:", relpath)
    return os.path.join( os.path.abspath(outputDir), relpath )

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
        self.overWriteFileFlag = tk.BooleanVar(self)
        self.overwriteFile = tk.Checkbutton(self.parent,
                text = "overwrite exist",
                variable = self.overWriteFileFlag,
                onvalue = True, offvalue = False,
                )
        self.overwriteFile.place(x=50, y=150)
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
            return
        self.chooseFilePath = os.path.dirname(
                os.path.realpath(filenames[0])
                )
        print("select:", self.chooseFilePath)
        self.chooseFileOutDir = filedialog.askdirectory(
                initialdir = self.chooseFilePath,
                parent = self.parent,
                title = "Select output Directory",
                mustexist = False,
                )
        if not self.checkDir(self.chooseFileOutDir):
            return
        self.convertFiles(filenames, self.chooseFileOutDir)

    def chooseDialogDir(self):
        print("chooseDialogDir")
        self.chooseDirPath = filedialog.askdirectory(
                initialdir = self.chooseDirPath,
                parent = self.parent,
                title = "Select Directory contains .SPE files",
                )
        print("select:", self.chooseDirPath)
        if len(self.chooseDirPath) == 0:
            return
        self.chooseDirOutDir = filedialog.askdirectory(
                initialdir = self.chooseDirPath,
                parent = self.parent,
                title = "Select output Directory",
                mustexist = False,
                )
        # TODO check wirte permission first
        if not self.checkDir(self.chooseDirOutDir):
            return
        filenames = yieldFilesUnderDirectory(self.chooseDirPath,
                match = "*.SPE")
        if filenames is None:
            messagebox.showinfo("Convert result", "No .SPE files under this directory")
            return
        self.convertFiles(filenames, self.chooseDirOutDir,
                oldPrefix = self.chooseDirPath)

    def checkDir(self, dirname):
        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        except Exception as e:
            messagebox.showinfo("Check Directory Failed: " + str(e),
                    traceback.format_exception(*sys.exc_info()))
            return False
        return True

    def convertFiles(self, fileIter, outputDir, oldPrefix = None):
        """ convert files
        fileIter: iterable file lists
        outputDir: destination output dir
        oldPrefix: original path cut oldPrefix then concat outputDir
        """
        print("outputDir:", outputDir)
        filecount = 0
        fileallcount = 0
        for onefile in fileIter:
            fileallcount += 1
            try:
                print("convert: ", onefile)
                speHandler = SPE(onefile)
                outPrefix = getOutputPrefix( onefile,
                        outputDir, oldPrefix )
                print(outPrefix)
                self.checkDir(os.path.dirname(outPrefix))
                # TODO check file existence first
                # TODO make it async
                # TODO handle file existence more friendly
                speHandler.spe2fits(
                        outPrefix = outPrefix,
                        clobber = self.overWriteFileFlag.get(),
                        output_verify = "warn", # XXX "warn" will alse throw exception?
                        )
            except OSError:
                pass
            except Exception as e:
                messagebox.showinfo("Convert " + onefile + " Failed: " + str(e),
                        traceback.format_exception(*sys.exc_info()))
            else:
                filecount += 1
        messagebox.showinfo("Convert Complete!", \
                "{filecount}(/{allcount}) files convert into {outputDir}".format(
                    filecount = filecount, outputDir = outputDir,
                    allcount = fileallcount)
                )

def workaroundForGUI():
    """ redirect I/O when in GUI
    ref:  http://stackoverflow.com/questions/2883205/how-can-i-freeze-a-dual-mode-gui-and-console-application-using-cx-freeze
    ref:  https://mail.gnome.org/archives/commits-list/2012-November/msg04489.html
    ref:  http://stackoverflow.com/questions/23505835/cx-freeze-ignores-custom-variables-module
    """
    try:
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        class GuiLogger:
            logfile = os.path.realpath(os.path.realpath(sys.argv[0]))
            logfile = os.path.splitext(logfile)[0] + '.log'
            logObj = open(logfile, "w")
            def __init__(self):
                self.logObj = GuiLogger.logObj
            def write(self, data):
                self.logObj.write(data)
            def flush(self):
                self.logObj.flush()
            def close(self):
                self.flush()
            def read(self, data):
                pass
        sys.stdout = sys.stderr = sys.stdin = sys.__stdout__ = sys.__stdin__ = sys.__stderr__ = GuiLogger()


def main():
    root = tk.Tk()
    workaroundForGUI()
    app = Application(master = root)
    root.mainloop()

if __name__ == '__main__':
    main()

