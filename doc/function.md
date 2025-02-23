
# DatapackRunner Function Binary Instruction Format

This document describes the binary format used for compiling Minecraft `.mcfunction` files into a portable binary format. The binary format encodes both function instructions and JSON text components for commands (such as `tellraw`) in a compact, length‐prefixed structure.

---

## 1. Overall Instruction Format

Each function is compiled into a contiguous binary block. The instruction block comprises one or more encoded instructions. An instruction is encoded as follows:

- **Argument Count (1 byte)**
  The number of arguments that follow.

- **Instruction Code (1 byte)**
  A value corresponding to a command (see the `Instruction` enum for details).

- **Arguments**
  For each argument, the following structure is used:
  - **Argument Length (1 byte)**: The number of bytes in the argument.
  - **Argument Data (variable)**: The argument text (in UTF‑8) or a compiled binary JSON (for tellraw commands).

### Example

```format
<argCount:1> <instruction:1> <arg1Len:1> <arg1Bytes> <arg2Len:1> <arg2Bytes> ...
```

Each instruction is stored one after another in the function binary data.

---

## 2. JSON Text Format for Tellraw Commands

For `tellraw` commands, the JSON argument is compiled into a binary format. This format supports two primary types of components:

### Component Types

- **Type 0: Pickled Data**
  - Format: `<0><length:1 byte><pickled bytes>`
  - Use: Embeds pickled data instead of JSON for further processing.

- **Type 1: Score Component**
  - Format:
    - `<1>`
    - `<nameLen:1 byte><name bytes>`
    - `<objectiveLen:1 byte><objective bytes>`
    - `<propCount:1 byte>` – Number of formatting properties
    - For each property:
      - If a boolean property (bold, italic, strikethrough, underlined): `<propID:1 byte> <value:1 byte>` (value is always 1)
      - For a color (property ID 5): `<propID:1 byte> <colorLen:1 byte><color string bytes>`
  - Use: Displays dynamic score information.

- **Type 2: Text Component**
  - Format:
    - `<2>`
    - `<textLen:1 byte><text bytes>`
    - `<propCount:1 byte>` – Number of formatting properties
    - For each property: (same as for score components)
  - Use: Displays static text.

- **Type 3: Array of Components**
  - Format:
    - `<3>`
    - `<componentCount:1 byte>`
    - For each sub-component:
      - `<compLen:1 byte><compiled component bytes>`
  - Use: Encodes multiple components in one JSON structure.

### Property Formatting

Formatting properties are stored as follows:

- **Boolean Formatting:**
  Each boolean property (bold, italic, strikethrough, underlined) is assigned an ID (0, 1, 2, 3 respectively). If the property is enabled, the binary format stores:

  ```format
  <propID:1> <1>
  ```

- **Color Property:**
  If a color is specified (and is not "white"), it is stored using property ID 4:

  ```format
  <propID:1> <colorLen:1> <colorBytes>
  ```

### Compilation Overview

- For a single component (either score or text), the compiler reads the relevant keys (`score` or `text`) from the JSON and encodes them along with the formatting properties.

- For an array of components, the compiler first writes a type 3 header, writes the count, and then encodes each component individually (with its length prefixed).

---

## 3. Putting It All Together

When compiling a `.mcfunction` file, each function’s instructions are compiled using the instruction format described above, while tellraw commands compile their JSON text argument into the custom binary JSON format. This design allows the executable to encapsulate multiple functions with a consistent and efficient binary syntax.

By using length-prefixed fields throughout the format, DatapackRunner ensures that:

- The binary structure is self-contained,
- It is straightforward to parse the instruction stream,
- And extensions (such as new instruction types or properties) can be added in future versions.

---

This document can be updated as new features or instruction types are added to the compiler.
