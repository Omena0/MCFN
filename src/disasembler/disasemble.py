from enum import IntEnum, auto
from io import BytesIO
import struct
import zlib
import sys

FORMAT_VERSION = 4

class Instruction(IntEnum):
    # Executor instructions (from "as <entity>" and "at <entity>")
    execute_as = auto()
    execute_at = auto()
    execute_store = auto()
    positioned = auto()

    # Conditionals (commands: if block/entity/score, unless block/entity/score)
    if_block = auto()
    if_entity = auto()
    if_score = auto()
    unless_block = auto()
    unless_entity = auto()
    unless_score = auto()

    # Scoreboards
    add = auto()
    remove = auto()
    list_scores = auto()
    list_objectives = auto()
    set_score = auto()
    get = auto()
    operation = auto()
    reset = auto()

    # Output
    say = auto()
    tellraw = auto()

    # Blocks
    setblock = auto()
    fill = auto()
    clone = auto()

    # Data
    get_block = auto()
    get_entity = auto()
    merge_block = auto()
    merge_entity = auto()

    # Random
    random = auto()

    # Entities
    summon = auto()
    kill = auto()

    # Tag
    tag_add = auto()
    tag_remove = auto()

    # Return
    return_ = auto()
    return_fail = auto()
    return_run = auto()

    # Kill branch
    kill_branch = auto()

    # Function execution: creates a new branch to run a function immediately.
    run_func = auto()


STYLES = ["bold", "italic", "strikethrough", "underlined"]

def disassemble_json(data: bytes) -> str:
    stream = BytesIO(data)
    try:
        t = stream.read(1)[0]
    except IndexError:
        return "<empty>"

    if t == 0:
        length = stream.read(1)[0]
        return f"RAW_JSON({stream.read(length).decode('utf-8')})"

    elif t in (1, 2):
        if t == 1:
            name = stream.read(stream.read(1)[0]).decode('utf-8')
            obj = stream.read(stream.read(1)[0]).decode('utf-8')
        else:
            text = stream.read(stream.read(1)[0]).decode('utf-8')

        prop_count = stream.read(1)[0]
        props = []

        for _ in range(prop_count):
            pid = stream.read(1)[0]
            if pid == 4:
                props.append(f"color={stream.read(stream.read(1)[0]).decode('utf-8')}")
            else:
                val = stream.read(1)[0]
                if pid > len(STYLES):
                    props.append(f"prop{pid}={val}")
                else:
                    props.append(STYLES[pid])

        props_str = " ".join(props)
        if t == 1:
            return f"SCORE(name={name}, objective={obj}{", " if props_str else ""}{props_str})" if props_str else f"SCORE(name={name}, objective={obj})"
        else:
            return f'TEXT("{text}"{" " if props_str else ""}{props_str})'

    elif t == 3:
        count = stream.read(1)[0]
        comps = [disassemble_json(stream.read(stream.read(1)[0])) for _ in range(count)]
        return "[" + ", ".join(comps) + "]"

    return f"UnknownType(0x{data.hex()})"

def disassemble(bytecode: bytes) -> str:
    stream = BytesIO(bytecode)
    lines = []

    while True:
        header = stream.read(2)
        if len(header) < 2:
            if header:
                lines.append("; Incomplete instruction at end")
            break

        arg_count, instr_val = header
        try:
            instr = Instruction(instr_val).name
        except ValueError:
            instr = f"UNKNOWN({instr_val})"

        args = []
        for _ in range(arg_count):
            bl = stream.read(1)
            if not bl:
                args.append("; Missing argument bytes")
                break
            arg_len = bl[0]
            arg_bytes = stream.read(arg_len)
            if instr == "tellraw" and arg_bytes and arg_bytes[0] in (0, 1, 2, 3):
                args.append(disassemble_json(arg_bytes))
            else:
                try:
                    args.append(arg_bytes.decode('utf-8'))
                except UnicodeDecodeError:
                    args.append(arg_bytes.hex())
        lines.append(instr + " " + " ".join(args))

    return "\n".join(lines)

def disassemble_executable(data: bytes) -> str:
    stream = BytesIO(data)
    output = ['####### Executable Disassembly #######\n']

    header = stream.read(4)
    if len(header) < 4:
        return "File too short for header."
    magic = header.decode('utf-8', errors='replace')

    version_byte = stream.read(1)
    if not version_byte:
        return "Missing version."
    version = version_byte[0]

    if magic != "MCFN":
        return f"Invalid magic bytes: {magic}"
    if version != FORMAT_VERSION:
        return f"Unsupported version: v{version}. Only v{FORMAT_VERSION} is supported."

    output.append(f'### Executable Header ###')
    output.append(f"Magic: {magic}")
    output.append(f"Version: {version}")

    # Read the namespace length and namespace bytes.
    ns_len_byte = stream.read(1)
    if len(ns_len_byte) != 1:
        return "Missing namespace length."
    ns_len = ns_len_byte[0]
    namespace_bytes = stream.read(ns_len)
    if len(namespace_bytes) != ns_len:
        return "Incomplete namespace bytes."
    namespace = namespace_bytes.decode('utf-8')
    output.append(f"Namespace: {namespace}")

    # Read function count (2 bytes)
    func_count_bytes = stream.read(2)
    if len(func_count_bytes) != 2:
        return "Missing function count bytes."
    func_count = struct.unpack(">H", func_count_bytes)[0]
    output.append(f"Function Count: {func_count}")
    output.append('\n### Functions ###')

    for _ in range(func_count):
        nlb = stream.read(1)
        if not nlb:
            output.append(";; Unexpected end while reading function entries.")
            break

        name_len = nlb[0]
        func_name_bytes = stream.read(name_len)
        if len(func_name_bytes) != name_len:
            output.append(";; Incomplete function name data.")
            break
        func_name = func_name_bytes.decode('utf-8')
        block_len_bytes = stream.read(2)
        if len(block_len_bytes) != 2:
            output.append(f';; Incomplete header for "{func_name}" with length {name_len}')
            break

        block_len = struct.unpack(">H", block_len_bytes)[0]
        instr_block = stream.read(block_len)
        if len(instr_block) != block_len:
            output.append(f";; Incomplete block for {func_name} (expected {block_len} bytes, got {len(instr_block)})")
            break

        output.append(f"## Function: {func_name} ##")
        output.append(f"  Length: {block_len} bytes")
        output.append("  Disassembly:")
        output.append("    " + "\n    ".join(disassemble(instr_block).splitlines()))
        
    return "\n".join(output)

def main():
    if len(sys.argv) < 2:
        print("Usage: parser.py <executable file>")
        sys.exit(1)

    with open(sys.argv[1], 'rb') as f:
        bytecode = zlib.decompress(f.read())

    print(disassemble_executable(bytecode))


if __name__ == '__main__':
    main()