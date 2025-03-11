# MCFN

Compile Minecraft functions to custom bytecode executables. 

You can later execute it in a VM.

I have not tested for perfect vanilla compatibility, but the command syntax is identical. 

## Features:
- Basic commands support
- Scoreboards
- Entities
- Blocks
- I/O (no input (yet) so i guess its just O) 
- Fully async executor by design
  - Executes multiple branches asynchronously
  - For more information you can attempt to decipher the source code
- Simple and space efficient executable format
- Vanilla tellraw json text format compilation real time evaluation
- Vanilla target selector compilation and real time evaluation 
- Working disassembler 
- Visual debugger (WIP, contains more bugs than atoms in the observable universe) 
- 1.21 macros support
- Colorful error/warning/info logging
- Function argument minimization (may be unstable)
- Custom preprocessor with multi-line syntax and macro commands
  - You can easily add more preprocessor commands
  - End a line with `\` and indent the next line to append the first line before all following indented lines
  - @define \<const\> \<value can have spaces\>
  - @repeat <range: e.g. 5..30, 0.., ..6> <command can have spaces>
    - `<i>` is replaced with the index
- Command line launcher tool (.exe WIP) 

