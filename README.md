# MCFN

MCFN is a system that compiles Minecraft functions to custom bytecode executables that can be executed in a virtual machine.

The command syntax is identical to vanilla Minecraft's, but this implementation provides additional features and optimizations.

## Features

- **Command Support**
  - Basic commands
  - Scoreboards
  - Entities
  - Blocks
  - I/O capabilities

- **Advanced Execution Model**
  - Fully async executor by design
  - Executes multiple branches asynchronously
  - Efficient branch handling

- **Optimized Format**
  - Simple and space-efficient executable format
  - Vanilla tellraw JSON text format compilation with real-time evaluation
  - Vanilla target selector compilation with real-time evaluation

- **Developer Tools**
  - Working disassembler to inspect compiled code
  - Visual debugger (GUI interface)
  - Colorful error/warning/info logging

- **Modern Features**
  - 1.21 macros support
  - Function argument minimization
  - Custom preprocessor with multi-line syntax and macro commands

## Preprocessor Features

- Line continuation: End a line with `\` and indent the next line to append
- Preprocessor commands:
  - `@define <const> <value>` - Define constants
  - `@repeat <range> <command>` - Repeat commands with range like `5..30`, `0..`, `..6`
    - `<i>` is replaced with the current index

## Project Structure

```
MCFN/
│
├── src/                   # Source code
│   ├── common.py          # Common utilities and shared definitions
│   ├── compiler.py        # Main compiler implementation
│   ├── disassembler.py    # Binary disassembler
│   ├── gui.py             # GUI debugger interface
│   ├── mcfn.py            # Command line interface
│   ├── vm.py              # Virtual machine implementation
│   └── test_mcfn.py       # Unit tests
│
├── doc/                   # Documentation
│   ├── example.md         # Example usage
│   ├── function.md        # Function binary format description
│   ├── executable.md      # Executable format documentation
│   └── instructions.md    # Instruction set documentation
│
├── build.py               # Build script for creating executable
└── requirements.txt       # Project dependencies
```

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/MCFN.git
cd MCFN
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

**Running MCFN:**
```bash
python src/mcfn.py run path/to/functions
```

**Compiling Functions:**
```bash
python src/mcfn.py compile path/to/functions -w output.bin
```

**Disassembling an Executable:**
```bash
python src/mcfn.py disassemble input.bin -w disasm.txt
```

**Using the GUI Debugger:**
```bash
python src/mcfn.py
```

## Running Tests

```bash
python src/test_mcfn.py
```

## License

Open source - see repository for license details.

