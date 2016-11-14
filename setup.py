from cx_Freeze import setup, Executable
from spe2fits import VERSION, AUTHOR

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = [], excludes = [],
        include_files = "WINHEAD.TXT",

        )

base = 'Console'

executables = [
    Executable('spe2fits.py', base=base,
        icon = 'bitbug_favicon.ico',
        )
]

setup(name='spe2fits',
      version = VERSION,
      author = AUTHOR,
      maintainer = AUTHOR,
      license = 'Apache-2.0',
      description = 'convert .SPE file to FITS',
      options = dict(build_exe = buildOptions),
      executables = executables)
