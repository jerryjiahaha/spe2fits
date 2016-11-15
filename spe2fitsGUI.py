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
import re
from functools import partial
from pathlib import Path # New in version 3.4

# ref: https://github.com/gorakhargosh/watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ref: http://effbot.org/tkinterbook/
import tkinter as tk
from tkinter import filedialog, messagebox, Checkbutton
from tkinter import ttk
#from tkinter import *
#from tkinter.ttk import *

#sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from spe2fits import SPE

class customerDirHandler(FileSystemEventHandler):
    SPE_FILE_PATTERN = re.compile(".*\.spe", re.IGNORECASE)
    def __init__(self, hook = None):
        self._hook = hook

    def set_hook(self, hook):
        self._hook = hook

    def on_created(self, event):
        super().on_created(event)
        print("on created", event)
        if event.is_directory:
            return
        newfile = os.path.abspath(event.src_path)
        print("newfile", newfile)
        if not customerDirHandler.SPE_FILE_PATTERN.match(newfile):
            return
        try:
            print("process hook")
            self._hook(newfile)
        except Exception as e:
            print(e)

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

        # settings of file overwrite
        self.overWriteFileFlag = tk.BooleanVar(self)
        self.overwriteFile = tk.Checkbutton(self,
                text = "overwrite exist",
                variable = self.overWriteFileFlag,
                onvalue = True, offvalue = False,
                )
        self.overwriteFile.place(x=50, y=150)

        # button for select files to convert
        self.chooseFile = tk.Button(self,
                text = "Convert Files...",
                fg="black", bg="white",
                command = self.chooseDialogFiles,
                )
        self.chooseFile.place(x=50, y=50)
        self.chooseFilePath = os.path.abspath(os.path.curdir)
        self.chooseFileOutDir = self.chooseFilePath

        # button for select directory to convert
        self.chooseDir = tk.Button(self,
                text = "Convert Directory...",
                fg="black", bg="white",
                command = self.chooseDialogDir,
                )
        self.chooseDir.place(x=50, y=100)
        self.chooseDirPath = os.path.abspath(os.path.curdir)
        self.chooseDirOutDir = self.chooseDirPath

        # select dir to listen
        ## source direcory
        self.listenDirPath = tk.StringVar(
                master = self, value = os.path.abspath(os.path.curdir),
                name = "listenDirPath",
                )
        ## destination directory
        self.listenDirOutputPath = tk.StringVar(
                master = self, value = os.path.abspath(os.path.curdir),
                name = "listenDirOutputPath",
                )
        self.listenDir = tk.Button(self,
                text = "Monitor directory...",
                fg="black", bg="white",
                command = self.addListenDir,
                )
        self.listenDir.place(x=50, y=250)
        self.listenDirOutput = tk.Button(self,
                text = "Binded directory...",
                fg="black", bg="white",
                command = self.bindListenDir,
                )
        self.listenDirOutput.place(x=50, y=300)
        self.listenDirEnableFlag = tk.BooleanVar(self)
        self.listenDirEnable = tk.Checkbutton(self,
                text = "Enable monitor",
                variable = self.listenDirEnableFlag,
                command = self.checkListenTask,
                onvalue = True, offvalue = False,
                )
        self.listenDirEnable.place(x=50, y=350)
        self.listenDirPathShow = tk.Label(self,
                fg="black", bg="white", width = 80,
                textvariable = self.listenDirPath,
                )
        self.listenDirPathShow.place(x=60+self.listenDir.winfo_reqwidth(),
                y=250)
        self.listenDirOutputPathShow = tk.Label(self,
                fg="black", bg="white", width = 80,
                textvariable = self.listenDirOutputPath,
                )
        self.listenDirOutputPathShow.place(x=60+self.listenDir.winfo_reqwidth(),
                y=300)

    def checkListenTask(self):
        self.listener.unschedule_all()
        print("checkListenTask")
        if self.listenDirEnableFlag.get():
            print("enable")
            listen_dir = os.path.abspath(self.listenDirPath.get())
            try:
                self.listener.schedule(self._listen_handler,
                        listen_dir, recursive = True)
            except Exception as e:
                messagebox.showinfo("listen dir {dirname} failed"
                        .format(dirname = listen_dir),
                        "{reason}".format(
                            reason = traceback.format_exception(*sys.exc_info())
                            )
                        )
        else:
            print("disable")

    def addListenDir(self):
        print("addListenDir")
        listenDirPath = filedialog.askdirectory(
                parent = self,
                title = "Auto convert (listen) .spe under this directory",
                initialdir = self.listenDirPath.get(),
                )
        if not self.checkDir(listenDirPath, autocreate = False, poperror = False):
            return
        print("listen:", listenDirPath)
        if os.path.abspath(listenDirPath) != self.listenDirPath.get():
            self.listenDirPath.set(os.path.abspath(listenDirPath))
            self.checkListenTask()

    def bindListenDir(self):
        print("bindListenDir")
        newOutDir = filedialog.askdirectory(
                parent = self,
                title = "Auto convert .spe into this directory",
                initialdir = self.listenDirPath.get(),
                )
        if not self.checkDir(newOutDir, autocreate = False, poperror = False):
            return
        print("bind to:", newOutDir)
        self.listenDirOutputPath.set(os.path.abspath(newOutDir))

    @property
    def listener(self):
        """ observer of files, for listening file created event
        """
        if not hasattr(self, "_listener"):
            self._listener = Observer()
            self._listen_handler = customerDirHandler(self.on_created)
            self._listener.start()
        return self._listener

    def on_created(self, onefile):
        if not self.listenDirEnableFlag.get():
            return
        try:
            print("convert:", onefile)
            outputDir = self.listenDirOutputPath.get()
            oldPrefix = self.listenDirPath.get()
            outPrefix = getOutputPrefix( onefile,
                    outputDir, oldPrefix)
            print("output prefix:", outPrefix)
            self.checkDir(os.path.dirname(outPrefix))
            speHandler = SPE(onefile)
            speHandler.spe2fits(
                    outPrefix = outPrefix,
                    clobber = self.overWriteFileFlag.get(),
                    )
        except Exception as e:
            messagebox.showinfo("Convert " + onefile + " Failed" + str(e),
                    traceback.format_exception(*sys.exc_info()))
        else:
            # TODO show status on widgets
            print("created")

    def chooseDialogFiles(self):
        print("chooseDialogFiles")
        filenames = filedialog.askopenfilenames(
                defaultextension = '.SPE',
                filetypes = [('WinViewer Documents', '.SPE'), ('all files', '.*'),],
                parent = self,
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
                parent = self,
                title = "Select output Directory",
                mustexist = False,
                )
        print("out:", self.chooseFileOutDir)
        if not self.checkDir(self.chooseFileOutDir):
            return
        self.convertFiles(filenames, self.chooseFileOutDir)

    def chooseDialogDir(self):
        print("chooseDialogDir")
        self.chooseDirPath = filedialog.askdirectory(
                initialdir = self.chooseDirPath,
                parent = self,
                title = "Select Directory contains .SPE files",
                )
        print("select:", self.chooseDirPath)
        if len(self.chooseDirPath) == 0:
            return
        self.chooseDirOutDir = filedialog.askdirectory(
                initialdir = self.chooseDirPath,
                parent = self,
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

    def checkDir(self, dirname, autocreate = True, poperror = True):
        if dirname is None or len(dirname) == 0:
            return False
        try:
            if not os.path.exists(dirname) and autocreate:
                os.makedirs(dirname)
        except Exception as e:
            if poperror:
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
                print("output prefix:", outPrefix)
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
    def cleanup(self):
        print("cleanup")
        self.listener.stop()
        self.listener.join()
        self.parent.destroy()


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


def on_closing(app):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        app.cleanup()

def main():
    root = tk.Tk()
    workaroundForGUI()
    app = Application(master = root)
    root.protocol("WM_DELETE_WINDOW", partial(on_closing, app))
    root.mainloop()

if __name__ == '__main__':
    main()

