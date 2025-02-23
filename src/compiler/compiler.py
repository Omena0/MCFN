from enum import IntEnum
from io import BytesIO
import pickle
import struct
import zlib
import json
import sys
import os

MAGIC = b'MCFN'
FORMAT_VERSION = 3

logging = False

# Logging init
if logging:
    logpath = os.path.join(os.getenv('userprofile'),"desktop",'processor.log')

    with open(logpath, 'w') as f:
        f.write('')

def log(line:str):
    if not logging: return
    with open(logpath, 'a') as f:
        f.write(line + '\n')

### Preprocessor ###
def get_indent(line:str):
    return len(line) - len(line.lstrip(' '))

definitions = {}
def process_line(line:str, name):
    for name, value in definitions.items():
        line = line.replace(f'?{name}', value)

    if line.strip().startswith(('@','#@')):
        indent = get_indent(line)
        operation, args = line.strip().split(':',1)[0].strip().split(' ',1)
        args = [i.strip() for i in args.split(',')]
        operation = operation.lstrip('#')
        command = '    '*indent + line.split(':',1)[1].strip()

        if operation == '@repeat':
            r = range(int(args[0]))
            if len(args) > 1:
                r = range(int(args[0]),int(args[1]))
                if len(args) > 2:
                    r = range(int(args[0]),int(args[1]),int(args[2]))
            return [command.replace('<i>',str(i)) for i in r]

        elif operation == '@define':
            name = args[0]
            value = command
            definitions[name] = value
            return []

    return [line]

def flatten(indented_lines, level):
    # Build a single output line from all lines in the chain
    chain = [indented_lines[i].strip() for i in range(level+1) if indented_lines[i].strip()]
    result = " ".join(chain)
    if result.lstrip().startswith('$'):
        result = '$' + result.strip()[1:]
    return result

def preprocess(source:str, name:str):
    # Commands pass
    new_lines = []
    for line in source.splitlines():
        new_lines.extend(process_line(line, name))

    # Join lines ending with backslash
    joined_lines = []
    buffer = ""
    for line in new_lines:
        if line.endswith("\\"):
            buffer += line[:-1].strip()
        else:
            buffer += line
            joined_lines.append(buffer)
            buffer = ""

    new_lines = joined_lines

    # Multiline pass
    log(f'# {name}')

    # Store the most recent line for each indent level
    indented_lines = [""] * 20
    # Process with index to allow lookahead.
    for i, original_line in enumerate(source.splitlines()):
        if not original_line.strip() or original_line.strip().startswith('#'):
            continue

        log(f'# {original_line}')
        line = original_line.replace('###','´´´').replace('##','´´').split('# ')[0].replace('´','#').rstrip('\\')  # Strip trailing backslash
        indent = get_indent(line)
        level = indent // 4  # or use another factor if your indentation is different

        # Place this line at the current indent level
        indented_lines[level] = line
        # Clear deeper levels
        for j in range(level+1, len(indented_lines)):
            indented_lines[j] = ""

        # Lookahead for the next non-skipped line
        next_level = None
        for j in range(i+1, len(source.splitlines())):
            next_line = source.splitlines()[j]
            if not next_line or next_line.startswith('#'):
                continue
            next_line = next_line.split('#')[0].rstrip('\\')
            next_indent = get_indent(next_line)
            next_level = next_indent // 4
            break

        # Only output if no following line increases the indent,
        # meaning the current line is not just a prefix.
        if next_level is None or next_level <= level:
            out_line = flatten(indented_lines, level)
            log(out_line)
            new_lines.append(out_line)

    return '\n'.join(new_lines)

### Compiler ###
class Instruction(IntEnum):
    # Executor instructions (from "as <entity>" and "at <entity>")
    execute_as = 1
    execute_at = 2
    positioned = 3

    # Conditionals (commands: if block/entity/score, unless block/entity/score)
    if_block = 4
    if_entity = 5
    if_score = 6
    unless_block = 7
    unless_entity = 8
    unless_score = 9

    # Scoreboards
    add = 10
    remove = 11
    list_scores = 12
    list_objectives = 13
    set_score = 14
    get = 15
    operation = 16
    reset = 17

    # Output
    say = 18
    tellraw = 19

    # Blocks
    setblock = 12
    fill = 21
    clone = 22

    # Data
    get_block = 23
    get_entity = 24
    merge_block = 25
    merge_entity = 26

    # Random
    random = 27

    # Entities
    summon = 28
    kill = 29

    # Tag
    tag_add = 30
    tag_remove = 31

    # Return
    return_ = 32
    return_fail = 33
    return_run = 34

    # Kill branch
    kill_branch = 35

    # Function execution: creates a new branch to run a function immediately.
    run_func = 36

def compile_component(comp: dict) -> bytes:
    """
    Compiles a single Minecraft JSON component into a binary format.

    For a component with a "score" key (score component), the binary format is:
      <type:1byte=1>
      <nameLen:1byte><name bytes>
      <objectiveLen:1byte><objective bytes>
      <propCount:1byte> [Formatting properties, if any]

    For a component with a "text" key (text component), the binary format is:
      <type:1byte=2>
      <textLen:1byte><text bytes>
      <propCount:1byte> [Formatting properties]

    Formatting properties:
      For boolean properties (bold (0), italic (1), strikethrough (2), underlined (3)):
         <propID:1byte> <1>
      For color (if not "white", propID 5):
         <propID:1byte> <colorLen:1byte> <color bytes>

    Default values are: bold false, italic false, strikethrough false, underlined false, color "white".
    """
    result = bytearray()
    if "score" in comp:
        # Score component header
        result += struct.pack("B", 1)
        score = comp["score"]
        name = score.get("name", "")
        objective = score.get("objective", "")
        name_bytes = name.encode("utf-8")
        if len(name_bytes) > 255:
            raise ValueError("Name too long.")
        result += struct.pack("B", len(name_bytes))
        result += name_bytes
        obj_bytes = objective.encode("utf-8")
        if len(obj_bytes) > 255:
            raise ValueError("Objective too long.")
        result += struct.pack("B", len(obj_bytes))
        result += obj_bytes
        # Include formatting properties from the main component (if provided)
        props = {}
        if comp.get("bold", False) is True:
            props[0] = 1
        if comp.get("italic", False) is True:
            props[1] = 1
        if comp.get("strikethrough", False) is True:
            props[2] = 1
        if comp.get("underlined", False) is True:
            props[3] = 1
        if "color" in comp and comp["color"] != "white":
            props[4] = comp["color"]
        result += struct.pack("B", len(props))
        for pid, value in props.items():
            result += struct.pack("B", pid)
            if pid == 4:
                color_bytes = value.encode("utf-8")
                if len(color_bytes) > 255:
                    raise ValueError("Color too long.")
                result += struct.pack("B", len(color_bytes))
                result += color_bytes
            else:
                result += struct.pack("B", value)
    elif "text" in comp:
        # Text component header
        result += struct.pack("B", 2)
        text = comp.get("text", "")
        text_bytes = text.encode("utf-8")
        if len(text_bytes) > 255:
            raise ValueError("Text too long.")
        result += struct.pack("B", len(text_bytes))
        result += text_bytes
        # Only store non-default properties.
        props = {}
        if comp.get("bold", False) is True:
            props[0] = 1
        if comp.get("italic", False) is True:
            props[1] = 1
        if comp.get("strikethrough", False) is True:
            props[2] = 1
        if comp.get("underlined", False) is True:
            props[3] = 1
        if "color" in comp and comp["color"] != "white":
            props[4] = comp["color"]
        result += struct.pack("B", len(props))
        for pid, value in props.items():
            result += struct.pack("B", pid)
            if pid == 4:
                color_bytes = value.encode("utf-8")
                if len(color_bytes) > 255:
                    raise ValueError("Color too long.")
                result += struct.pack("B", len(color_bytes))
                result += color_bytes
            else:
                result += struct.pack("B", value)
    else:
        raise ValueError("Component must have either a 'score' or 'text' key.")
    return bytes(result)

def compile_minecraft_json(json_text: str) -> bytes:
    """
    Parses data for a tellraw command and compiles it to a binary format.

    Supported formats:
      - A single component (a dict containing a "score" or "text" key) is compiled via compile_component.
      - An array of components is compiled as:
          <type:1byte=3>
          <componentCount:1byte>
          For each component:
              <compLen:1byte><compiled component bytes>

    The provided json_text must be valid JSON representing an object or an array.

    As a fallback for any parsing errors, the function falls back to
    pickling the original string, returning:
        <type:1 byte=0><length:1 byte><pickled bytes>
    """

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        # Always propagate JSON decoding errors.
        raise ValueError(f"Invalid JSON data: {e}\nData: {json_text}")

    try:
        compiled = bytearray()

        if isinstance(data, list):
            compiled += struct.pack("B", 3)
            count = len(data)
            compiled += struct.pack("B", count)
            for comp in data:
                if not isinstance(comp, dict):
                    raise ValueError("Each component in array must be a dict.")
                comp_bytes = compile_component(comp)
                if len(comp_bytes) > 255:
                    raise ValueError("Component too long.")
                compiled += struct.pack("B", len(comp_bytes))
                compiled += comp_bytes

        elif isinstance(data, dict):
            if "score" in data or "text" in data:
                comp_bytes = compile_component(data)
                compiled += comp_bytes
            else:
                raise ValueError("Invalid component format for tellraw.")
        else:
            raise ValueError("Invalid JSON format for tellraw.")

        return bytes(compiled)

    except Exception as e:
        # Fallback: if any non-JSON decoding error occurs during processing,
        # use the original string pickled.
        pickled = pickle.dumps(json_text)
        if len(pickled) > 255:
            raise ValueError("Pickled data too long.")
        return struct.pack("B", 0) + struct.pack("B", len(pickled)) + pickled

def compile_instr(cmd: str, args: list) -> bytes:
    """
    Compiles a single instruction with its arguments into binary format.
    """
    local = bytearray()
    try:
        instr_code = Instruction[cmd]

    except KeyError:
        return b'' # Drop instruction

    if len(args) > 255:
        raise ValueError("Too many arguments in instruction.")

    local += struct.pack("B", len(args))
    local += struct.pack("B", instr_code.value)

    for arg in args:
        # For tellraw commands, compile the JSON argument to binary.
        if instr_code == Instruction.tellraw and arg.lstrip().startswith(('{', '[')):
            try:
                arg_bytes = compile_minecraft_json(arg)

            except:
                return b'' # Drop instruction

        else:
            arg_bytes = arg.encode('utf-8')

        if len(arg_bytes) > 255:
            raise ValueError("Argument too long.")

        local += struct.pack("B", len(arg_bytes))
        local += arg_bytes

    return bytes(local)

def compile_source(source):
    """
    Compiles the Minecraft .mcfunction source into a binary executable.
    Each instruction is stored as:
      <argCount:1byte><instruction:1byte><arg1Len:1byte><arg1Bytes>...
    """
    compiled = bytearray()
    lines = source.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        tokens = line.split()

        # --- Execute Command Support ---
        if tokens[0].lower() == "execute":
            i = 1
            exec_instructions = bytearray()

            # Process optional clauses until we see "run".
            while i < len(tokens) and tokens[i].lower() != "run":
                token = tokens[i].lower()
                if token == "as":
                    i += 1
                    if i >= len(tokens):
                        raise ValueError("Missing selector after 'as'")
                    selector = tokens[i]
                    exec_instructions += compile_instr("execute_as", [selector])
                    i += 1
                elif token == "at":
                    i += 1
                    if i >= len(tokens):
                        raise ValueError("Missing selector after 'at'")
                    selector = tokens[i]
                    exec_instructions += compile_instr("execute_at", [selector])
                    i += 1
                elif token == "positioned":
                    # Expect three arguments: <x> <y> <z>
                    if i + 3 >= len(tokens):
                        raise ValueError("Missing coordinates after 'positioned'")
                    x = tokens[i+1]
                    y = tokens[i+2]
                    z = tokens[i+3]
                    exec_instructions += compile_instr("positioned", [x, y, z])
                    i += 4
                elif token == "if":
                    i += 1
                    if i >= len(tokens):
                        raise ValueError("Missing condition type after 'if'")
                    condition = tokens[i].lower()
                    i += 1
                    if condition == "block":
                        # Syntax: if block <x> <y> <z> <block>
                        if i + 3 >= len(tokens):
                            raise ValueError("Incomplete 'if block' condition")
                        bx = tokens[i]; by = tokens[i+1]; bz = tokens[i+2]
                        block_id = tokens[i+3]
                        exec_instructions += compile_instr("if_block", [bx, by, bz, block_id])
                        i += 4
                    elif condition == "entity":
                        # Syntax: if entity <selector>
                        if i >= len(tokens):
                            raise ValueError("Missing selector after 'if entity'")
                        selector_if = tokens[i]
                        exec_instructions += compile_instr("if_entity", [selector_if])
                        i += 1
                    elif condition == "score":
                        # Supports two syntaxes:
                        # A) Using "matches": if score <selector> <objective> matches <range>
                        # B) Using a relational operator: if score <selector> <objective> <op> <comp_selector> <comp_objective>
                        if i + 3 >= len(tokens):
                            raise ValueError("Incomplete 'if score' condition")
                        score_selector = tokens[i]
                        objective = tokens[i+1]
                        operator = tokens[i+2].lower()
                        valid_ops = {"matches", ">", "<", ">=", "<=", "==", "!="}
                        if operator not in valid_ops:
                            raise ValueError(f"Expected comparison operator in 'if score' condition, got {tokens[i+2]}")
                        if operator == "matches":
                            range_spec = tokens[i+3]
                            exec_instructions += compile_instr("if_score", [score_selector, objective, "matches", range_spec])
                            i += 4
                        else:
                            if i + 4 >= len(tokens):
                                raise ValueError("Incomplete 'if score' condition for operator")
                            comp_selector = tokens[i+3]
                            comp_objective = tokens[i+4]
                            exec_instructions += compile_instr("if_score", [score_selector, objective, operator, comp_selector, comp_objective])
                            i += 5
                    else:
                        raise ValueError(f"Unsupported if-condition type: {condition}")

                elif token == "unless":
                    i += 1
                    if i >= len(tokens):
                        raise ValueError("Missing condition type after 'unless'")
                    condition = tokens[i].lower()
                    i += 1
                    if condition == "block":
                        # Syntax: unless block <x> <y> <z> <block>
                        if i + 3 >= len(tokens):
                            raise ValueError("Incomplete 'unless block' condition")
                        bx = tokens[i]; by = tokens[i+1]; bz = tokens[i+2]
                        block_id = tokens[i+3]
                        exec_instructions += compile_instr("unless_block", [bx, by, bz, block_id])
                        i += 4
                    elif condition == "entity":
                        # Syntax: unless entity <selector>
                        if i >= len(tokens):
                            raise ValueError("Missing selector after 'unless entity'")
                        selector_unless = tokens[i]
                        exec_instructions += compile_instr("unless_entity", [selector_unless])
                        i += 1
                    elif condition == "score":
                        # Supports two syntaxes for unless score as well.
                        if i + 3 >= len(tokens):
                            raise ValueError("Incomplete 'unless score' condition")
                        score_selector = tokens[i]
                        objective = tokens[i+1]
                        operator = tokens[i+2].lower()
                        valid_ops = {"matches", ">", "<", ">=", "<=", "==", "!="}
                        if operator not in valid_ops:
                            raise ValueError(f"Expected comparison operator in 'unless score' condition, got {tokens[i+2]}")
                        if operator == "matches":
                            range_spec = tokens[i+3]
                            exec_instructions += compile_instr("unless_score", [score_selector, objective, "matches", range_spec])
                            i += 4
                        else:
                            if i + 4 >= len(tokens):
                                raise ValueError("Incomplete 'unless score' condition for operator")
                            comp_selector = tokens[i+3]
                            comp_objective = tokens[i+4]
                            exec_instructions += compile_instr("unless_score", [score_selector, objective, operator, comp_selector, comp_objective])
                            i += 5
                    else:
                        raise ValueError(f"Unsupported unless-condition type: {condition}")
                else:
                    raise ValueError(f"Unexpected token in execute clause: {tokens[i]}")

            # Expect the "run" keyword
            if i >= len(tokens) or tokens[i].lower() != "run":
                raise ValueError("Missing 'run' keyword in execute command")

            i += 1  # Skip the "run" token
            # The remainder forms the subcommand.
            subcommand = ' '.join(tokens[i:])
            # Compile the subcommand recursively.
            subcmd_bytes = compile_source(subcommand)
            # Append the accumulator instructions, the subcommand and then "kill_branch".
            compiled += exec_instructions + subcmd_bytes + compile_instr("kill_branch", [])
            continue

        # --- Scoreboard Commands ---
        elif tokens[0].lower() == "scoreboard":
            if tokens[1].lower() == "objectives":
                if len(tokens) >= 3 and tokens[2].lower() == "list":
                    cmd = "list_objectives"
                    args = []  # no additional arguments
                else:
                    # Ignore other objectives commands as scoreboards are auto‑created.
                    continue
            elif tokens[1].lower() == "players":
                subcmd = tokens[2].lower()
                if subcmd == "set":
                    cmd = "set_score"
                    args = tokens[3:]
                elif subcmd == "add":
                    cmd = "add"
                    args = tokens[3:]
                elif subcmd == "remove":
                    cmd = "remove"
                    args = tokens[3:]
                elif subcmd == "list":
                    cmd = "list_scores"
                    args = tokens[3:]
                elif subcmd == "get":
                    cmd = "get"
                    args = tokens[3:]
                elif subcmd == "operation":
                    cmd = "operation"
                    args = tokens[3:]
                elif subcmd == "reset":
                    cmd = "reset"
                    args = tokens[3:]
                else:
                    raise ValueError(f"Unsupported scoreboard players command: {line}")
            else:
                raise ValueError(f"Unsupported scoreboard command: {line}")

        # --- Output ---
        elif tokens[0].lower() == "tellraw":
            parts = line.split(None, 2)
            if len(parts) < 3:
                raise ValueError("tellraw command requires a target and a JSON argument.")
            cmd = "tellraw"
            args = [parts[2].strip()]  # only the JSON text is compiled

        # --- Data Commands ---
        elif tokens[0].lower() == "data":
            subcmd = tokens[1].lower()
            typ = tokens[2].lower()
            if subcmd == "get" and typ in ("block", "entity"):
                cmd = f"get_{typ}"
                args = tokens[3:]
            elif subcmd == "merge" and typ in ("block", "entity"):
                cmd = f"merge_{typ}"
                args = tokens[3:]
            else:
                raise ValueError(f"Invalid data command syntax: {line}")

        # --- Return Commands ---
        elif tokens[0].lower() == "return":
            if len(tokens) < 2:
                raise ValueError("return command requires at least one argument")
            if tokens[1].lower() == "fail":
                if len(tokens) != 3:
                    raise ValueError("Usage: /return fail <fail status>")
                cmd = "return_fail"
                args = [tokens[2]]
            elif tokens[1].lower() == "run":
                if len(tokens) < 3:
                    raise ValueError("Usage: /return run <command>")
                cmd = "return_run"
                args = [' '.join(tokens[2:])]
            else:
                cmd = "return_"
                args = tokens[1:]

        # --- Tag Commands ---
        elif tokens[0].lower() == "tag":
            if len(tokens) < 3:
                raise ValueError(f"Invalid tag command syntax: {line}")
            if tokens[1].lower() == "add":
                cmd = "tag_add"
                args = tokens[2:]
            elif tokens[1].lower() == "remove":
                cmd = "tag_remove"
                args = tokens[2:]
            else:
                raise ValueError(f"Invalid tag command syntax: {line}")

        # --- Function Command ---
        elif tokens[0].lower() == "function":
            if len(tokens) < 2:
                raise ValueError("function command requires a function name")
            cmd = "run_func"
            args = [' '.join(tokens[1:])]

        # --- Default ---
        else:
            # Use the command as specified.
            cmd = tokens[0].lower()
            args = tokens[1:]

        compiled += compile_instr(cmd, args)

    return bytes(compiled)

def compile_file(filename:str) -> bytes:
    source = read_file(filename)
    source = preprocess(source, filename)
    return compile_source(source)

def compile_files(path:str) -> dict:
    """Compile all leaf files in a directory"""
    functions = {}

    # If path is a folder
    if os.path.isdir(path):
        # Loop all files
        for file in os.listdir(path):
            # Convert to path and replace backslashes
            file = os.path.join(path,file).replace('\\','/')

            # Recurse if dir
            if os.path.isdir(file):
                functions.update(compile_files(file))

            else:
                # Ignore if not .mcfunction
                if not file.endswith('.mcfunction'):
                    continue

                # Actually compile it
                functions[file.removesuffix('.mcfunction')] = compile_file(file)

    else:
        functions[path] = compile_file(path)

    return functions

def read_file(infile):
    with open(infile, 'r') as f:
        return f.read()

def write_file(outfile, data:bytes):
    data = zlib.compress(data, level=9)
    with open(outfile, 'wb') as f:
        f.write(data)

def create_executable(functions: dict[str, bytes], namespace: str):
    exe = BytesIO()

    # Header
    exe.write(MAGIC)  # 4 bytes magic
    exe.write(FORMAT_VERSION.to_bytes(1, 'big'))  # 1 byte version

    # Namespace
    ns_bytes = namespace.encode('utf-8')
    if len(ns_bytes) > 255:
        raise ValueError("Namespace too long.")
    exe.write(len(ns_bytes).to_bytes(1, 'big'))
    exe.write(ns_bytes)

    # Write function count as 2 bytes.
    exe.write(len(functions).to_bytes(2, 'big'))
    for name, data in functions.items():
        name_bytes = name.encode('utf-8')
        exe.write(len(name_bytes).to_bytes(1, 'big'))
        exe.write(name_bytes)
        exe.write(len(data).to_bytes(2, 'big'))
        exe.write(data)
    return exe.getvalue()

def print_functions(functions):
    for name,data in functions.items():
        data = data.hex(' ')
        block = ''
        for i in range(0, len(data), 170):
            block += '  ' + data[i:i+170].strip() + '\n'
        print(f"Compiled {name}:\n{block}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: main.py <namespace> <output file>")
        sys.exit(1)

    namespace = sys.argv[1]
    binary_name = sys.argv[2]

    # Compile
    functions:dict[str,bytes] = compile_files(namespace)

    # Print all the functions (wont remove)
    print_functions(functions)

    # Create binary
    binary_executable = create_executable(functions, namespace)

    # Write binary
    write_file(binary_name, binary_executable)

    # Done
    print(f"Compiled {namespace} to {binary_name} in namespace {namespace}")
