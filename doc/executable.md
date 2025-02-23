# DatapackRunner Binary Executable Format

This document describes the binary format used by DatapackRunner for compiling vanilla Minecraft `.mcfunction` files into a single executable binary that supports multiple functions.

## Overall Structure

The executable binary is comprised of:

- A fixed header (magic bytes, version and namespace).
- A function table that lists all the functions included.
  - For each function, a header with its name (i.e. its file path) and its compiled instruction block (using the old binary format for function instructions).

### File Header

The file begins with a header in the following structure:
  • **Magic Number (4 bytes):** A constant signature (`MCFN`) identifying the file as a MCFunction executable.
  • **Version (1 byte):** The format version number (now `3`).
  • **Namespace (variable):**
      - **Namespace Length (1 byte):** Length of the namespace string.
      - **Namespace (UTF‑8):** The namespace (typically the compiled folder).
  • **Function Count (2 byte):** The number of functions contained in the binary.

**Example:**

```data structure
MCFN 0x02
```

### Function Table

After the header, the file contains a function table:
  • **Function Count (1 byte):** The number of functions contained in the binary.

Then, for each function, the following structure is used:

  • **Function Name Length (1 byte):** The length (in bytes) of the function's name (this is the path of the original `.mcfunction` file).

  • **Function Name (variable):** The UTF-8 encoded function name (i.e. file path).

  • **Instruction Block Length (2 bytes):** The length (in bytes) of the compiled instruction block for that function. (A 2-byte unsigned integer allows instruction blocks up to 65,535 bytes.)

  • **Instruction Block (variable):** The compiled instructions for that function. This block uses the old binary format, where each instruction is encoded as:
    - `<argCount: 1 byte>`
    - `<instruction code: 1 byte>`
    - For each argument:
      - `<arg length: 1 byte>`
      - `<arg bytes (UTF-8 or compiled JSON for tellraw commands)>`

## File layout table

```table
+------------+------------------+
| Header     | Function Entries |
+------------+------------------+
| Magic      | Per function:    |
| Format ver |   <len: 1 byte>  |
| Namespace  |   <func name>    |
| Func count |   <len: 2 bytes> |
|            |   <instructions> |
+------------+------------------+
```

## Summary

- **Header:**
  4 bytes magic (`MCFN`) + 1 byte version number.

- **Function Count:**
  1 byte indicating the number of functions.

- **Per-function Entry:**
  1 byte name length, variable-length function name (UTF-8), 2 bytes instruction block length, and the instruction block (compiled using the old format).

This format allows the compiler to support multiple functions, where the function’s name (the mcfunction file path) is stored as part of the binary.
