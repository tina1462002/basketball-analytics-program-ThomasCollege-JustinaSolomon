import PyInstaller.__main__
import os

# Get the directory of this script
dir_path = os.path.dirname(os.path.realpath(__file__))

PyInstaller.__main__.run([
    'app.py',
    '--onefile',
    '--windowed',
    '--name=BasketballAnalytics',
    '--icon=basketball.ico',  # Optional: add this line if you have an icon file
    '--add-data=data.json;.' if os.name == 'nt' else '--add-data=data.json:.',
    '--clean',
])
