import shutil
import os

try: os.chdir('src')
except: pass

build_command = """
py -m nuitka --standalone --onefile
 --product-name="MCFN Launcher" --product-version=1.0.0
 --file-description="The MCFN language launcher"
 --enable-plugin=tk-inter
 --nofollow-import-to=nuitka
 --copyright="Copyright © 2025 Omena0. All rights reserved."
 --output-dir="build"
 --deployment --python-flag="-OO" --python-flag="-S"
 --output-filename="mcfn.exe"
 build/mcfn.py
""".strip().replace('\n', '')

def build():
    # Move over source files
    shutil.copy('compiler/compiler.py', 'build/compiler.py')
    shutil.copy('disasembler/disasemble.py', 'build/disasemble.py')
    shutil.copy('vm/vm.py', 'build/vm.py')
    shutil.copy('launcher/mcfn.py', 'build/mcfn.py')
    shutil.copy('gui/gui.py', 'build/gui.py')

    # Run compilation
    os.system(build_command)

    shutil.move('build/mcfn.exe', '../dist/mcfn.exe')

if __name__ == "__main__":
    build()
