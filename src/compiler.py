from io import BytesIO
import logging
import pickle
import struct
import zlib
import json
import sys
import os
from common import Instruction, MAGIC, FORMAT_VERSION, setup_logger, STYLES

level = logging.DEBUG
log = setup_logger("MCFN", level)

# Logger is now set up by the setup_logger function from common.py

### Preprocessor ###
def get_indent(line:str) -> int:
    """
    Calculate the indentation level of a line by counting leading spaces.
    
    Args:
        line: The input line to analyze
        
    Returns:
        The number of leading spaces in the line
    """
    return len(line) - len(line.lstrip(' '))

definitions = {}
def process_line(line:str, name:str) -> list:
    """
    Process a line of source code, handling preprocessor directives.
    
    Args:
        line: The input line to process
        name: Name of the source file being processed
        
    Returns:
        A list of one or more processed lines
    """
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
        result = f'${result.strip()[1:]}'
    return result

def preprocess(source:str, name:str) -> str:
    """
    Preprocess source code to handle indentation, line continuations, and directives.
    
    This function:
    1. Processes each line for preprocessor directives
    2. Joins lines that end with backslash line continuations
    3. Handles indentation to create hierarchical code structure
    
    Args:
        source: The source code to preprocess
        name: Name of the source file
        
    Returns:
        The preprocessed source code as a single string
    """
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
    
    # Use the joined_lines as base but then build a new final_lines list
    final_lines = []

    # Store the most recent line for each indent level
    indented_lines = [""] * 20
    all_lines = source.splitlines()  # using original source lines for indentation
    for i, original_line in enumerate(all_lines):
        if not original_line.strip() or original_line.strip().startswith('#'):
            continue

        line = original_line.replace('###','´´´').replace('##','´´').split('# ')[0].replace('´','#').rstrip('\\')
        indent = len(line) - len(line.lstrip(' '))
        level = indent // 4
        indented_lines[level] = line
        # Clear deeper levels
        for j in range(level+1, len(indented_lines)):
            indented_lines[j] = ""
        
        # Lookahead for the next non-skipped line
        next_level = None
        for j in range(i+1, len(all_lines)):
            next_line = all_lines[j]
            if not next_line.strip() or next_line.strip().startswith('#'):
                continue
            next_line = next_line.split('#')[0].rstrip('\\')
            next_indent = len(next_line) - len(next_line.lstrip(' '))
            next_level = next_indent // 4
            break
        
        # Only output if no following line increases the indent
        if next_level is None or next_level <= level:
            out_line = " ".join(indented_lines[k].strip() for k in range(level+1) if indented_lines[k].strip())
            final_lines.append(out_line)
      # Return the final preprocessed source (using only final_lines)
    return '\n'.join(final_lines)

### Compiler ###
# Using Instruction enum from common.py

def compile_component(comp: dict) -> bytes:  # sourcery skip: low-code-quality
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
        raise ValueError(f"Invalid JSON data: {e}\nData: {json_text}") from e

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
            raise ValueError("Pickled data too long.") from e
        return struct.pack("B", 0) + struct.pack("B", len(pickled)) + pickled

def get_arg_letter(i: int) -> str:
    """
    Returns a letter (or two letters) based on the 0-indexed argument position.
    Example: 0 -> "a", 1 -> "b", …, 25 -> "z", 26 -> "aa", 27 -> "ab", etc.
    """
    base = 26
    if i < base:
        return chr(ord('a') + i)
    else:
        # Compute two-letter key. (For positions > 25, this can be extended as needed.)
        first = (i // base) - 1
        second = i % base
        return chr(ord('a') + first) + chr(ord('a') + second)

def compile_instr(cmd: str, args: list) -> bytes:
    """
    Compiles a single instruction with its arguments into binary format.
    """
    local = bytearray()
    try:
        instr_code = Instruction[cmd]
    except KeyError:
        return b''  # Drop instruction

    if len(args) > 255:
        log.error(f'Ignoring invalid command: {cmd} {args}')
        log.error("Too many arguments in instruction.")
        return b''

    local += struct.pack("B", len(args))
    local += struct.pack("B", instr_code.value)

    for arg in args:
        # If the argument is already a bytes object, use it directly.
        if isinstance(arg, bytes):
            arg_bytes = arg
        else:
            # For tellraw commands, compile the JSON argument to binary.
            if instr_code == Instruction.tellraw and arg.lstrip().startswith(('{', '[')):
                try:
                    arg_bytes = compile_minecraft_json(arg)
                except:
                    return b''  # Drop instruction
            else:
                arg_bytes = arg.encode('utf-8')

        if len(arg_bytes) > 255:
            log.error(f'Ignoring invalid command: {cmd} {args}')
            log.error(f"Argument too long. [{len(arg_bytes)}/255]")
            return b''

        local += struct.pack("B", len(arg_bytes))
        local += arg_bytes

    return bytes(local)

def compile_source(func_name, source):  # sourcery skip: low-code-quality
    """
    Compiles the Minecraft .mcfunction source into a binary executable.
    Each instruction is stored as:
      <argCount:1byte><instruction:1byte><arg1Len:1byte><arg1Bytes>...
    """
    compiled = bytearray()
    lines = source.splitlines()
    # Process each line.
    if func_name:
        log.info(f'Compiling: {func_name}')

    for line in lines:
        # Remove any trailing newline and spaces.
        line = line.strip()
        if not line:
            continue

        log.debug(f'Compiling: {line}')

        # NEW: if the line is a vanilla macro line (starts with "$"), remove the dollar.
        if line.lstrip().startswith('$'):
            line = line.removeprefix('$')
            for macro in line.split('$(')[1:]:
                macro = macro.split(')',1)[0]
                func_name = func_name.replace(f'{namespace}/','').removesuffix('.mcfunction')
                if func_name not in args_map:
                    log.error(f'Function {func_name} not found.')

                final = args_map[func_name].get(macro)
                if final is None:
                    log.error(f'Variable {macro} was not supplied in the function call to {func_name}')

                line = line.replace(f'$({macro})', f'$({final})')

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
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing selector after 'as'")
                        continue

                    selector = tokens[i]
                    exec_instructions += compile_instr("execute_as", [selector])
                    i += 1

                elif token == "at":
                    i += 1
                    if i >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing selector after 'at'")
                        continue

                    selector = tokens[i]
                    exec_instructions += compile_instr("execute_at", [selector])
                    i += 1

                elif token == "positioned":
                    # Expect three arguments: <x> <y> <z>
                    if i + 3 >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing coordinates after 'positioned'")
                        continue

                    x = tokens[i+1]
                    y = tokens[i+2]
                    z = tokens[i+3]
                    exec_instructions += compile_instr("positioned", [x, y, z])
                    i += 4

                elif token == "if":
                    i += 1
                    if i >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing condition type after 'if'")
                        continue

                    condition = tokens[i].lower()
                    i += 1
                    if condition == "block":
                        # Syntax: if block <x> <y> <z> <block>
                        if i + 3 >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Incomplete 'if block' condition")
                            continue

                        bx = tokens[i]; by = tokens[i+1]; bz = tokens[i+2]
                        block_id = tokens[i+3]
                        exec_instructions += compile_instr("if_block", [bx, by, bz, block_id])
                        i += 4

                    elif condition == "entity":
                        # Syntax: if entity <selector>
                        if i >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Missing selector after 'if entity'")
                            continue

                        selector_if = tokens[i]
                        exec_instructions += compile_instr("if_entity", [selector_if])
                        i += 1

                    elif condition == "score":
                        # Supports two syntaxes:
                        # A) Using "matches": if score <selector> <objective> matches <range>
                        # B) Using a relational operator: if score <selector> <objective> <op> <comp_selector> <comp_objective>
                        if i + 3 >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Incomplete 'if score' condition")
                            continue

                        score_selector = tokens[i]
                        objective = tokens[i+1]
                        operator = tokens[i+2].lower()
                        valid_ops = {"matches", ">", "<", ">=", "<=", "==", "!="}
                        if operator not in valid_ops:
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error(f"Expected comparison operator in 'if score' condition, got {tokens[i+2]}")
                            continue

                        if operator == "matches":
                            range_spec = tokens[i+3]
                            exec_instructions += compile_instr("if_score", [score_selector, objective, "matches", range_spec])
                            i += 4
                        else:
                            if i + 4 >= len(tokens):
                                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                                log.error("Incomplete 'if score' condition for operator")
                                continue

                            comp_selector = tokens[i+3]
                            comp_objective = tokens[i+4]
                            exec_instructions += compile_instr("if_score", [score_selector, objective, operator, comp_selector, comp_objective])
                            i += 5
                    else:
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error(f"Unsupported if-condition type: {condition}")
                        continue

                elif token == "unless":
                    i += 1
                    if i >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing condition type after 'unless'")
                        continue
                    condition = tokens[i].lower()
                    i += 1
                    if condition == "block":
                        # Syntax: unless block <x> <y> <z> <block>
                        if i + 3 >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Incomplete 'unless block' condition")
                            continue

                        bx = tokens[i]; by = tokens[i+1]; bz = tokens[i+2]
                        block_id = tokens[i+3]
                        exec_instructions += compile_instr("unless_block", [bx, by, bz, block_id])
                        i += 4
                    elif condition == "entity":
                        # Syntax: unless entity <selector>
                        if i >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Missing selector after 'unless entity'")
                            continue

                        selector_unless = tokens[i]
                        exec_instructions += compile_instr("unless_entity", [selector_unless])
                        i += 1
                    elif condition == "score":
                        # Supports two syntaxes for unless score as well.
                        if i + 3 >= len(tokens):
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error("Incomplete 'unless score' condition")
                            continue

                        score_selector = tokens[i]
                        objective = tokens[i+1]
                        operator = tokens[i+2].lower()
                        valid_ops = {"matches", ">", "<", ">=", "<=", "==", "!="}
                        if operator not in valid_ops:
                            log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                            log.error(f"Expected comparison operator in 'unless score' condition, got {tokens[i+2]}")
                            continue

                        if operator == "matches":
                            range_spec = tokens[i+3]
                            exec_instructions += compile_instr("unless_score", [score_selector, objective, "matches", range_spec])
                            i += 4
                        else:
                            if i + 4 >= len(tokens):
                                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                                log.error("Incomplete 'unless score' condition for operator")
                                continue

                            comp_selector = tokens[i+3]
                            comp_objective = tokens[i+4]
                            exec_instructions += compile_instr("unless_score", [score_selector, objective, operator, comp_selector, comp_objective])
                            i += 5
                    else:
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error(f"Unsupported unless-condition type: {condition}")
                        continue

                elif token == "store":
                    i += 1
                    if i >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing store type after 'store'")
                        continue

                    store_type = tokens[i].lower()
                    if store_type not in ("result", "success"):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Store type must be 'result' or 'success'")
                        continue

                    i += 1
                    if i >= len(tokens) or tokens[i].lower() != "score":
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Expected 'score' after execute store <result|success>")
                        continue

                    i += 1
                    if i + 1 >= len(tokens):
                        log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                        log.error("Missing target or objective for execute store score")
                        continue

                    targets = tokens[i]
                    objective = tokens[i+1]
                    exec_instructions += compile_instr("execute_store", [store_type, targets, objective])
                    i += 2

                else:
                    log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                    log.error(f"Unexpected token in execute clause: {tokens[i]}")
                    continue

            # Expect the "run" keyword
            if i >= len(tokens) or tokens[i].lower() != "run":
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error("Missing 'run' keyword in execute command")
                continue

            i += 1  # Skip the "run" token
            # The remainder forms the subcommand.
            subcommand = ' '.join(tokens[i:])
            # Compile the subcommand recursively.
            subcmd_bytes = compile_source(None, subcommand)
            # Append the accumulator instructions, the subcommand and then "kill_branch".
            compiled += exec_instructions + subcmd_bytes + compile_instr("kill_branch", [])
            continue

        # --- Scoreboard Commands ---
        elif tokens[0].lower() == "scoreboard":
            if tokens[1].lower() == "objectives":
                if len(tokens) >= 3 and tokens[2].lower() == "list":
                    cmd = "list_objectives"
                    args = []  # no additional arguments

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
                    log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                    log.error(f"Unsupported scoreboard players command: {line}")
                    continue
            else:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error(f"Unsupported scoreboard command: {line}")
                continue

        # --- Output ---
        elif tokens[0].lower() == "tellraw":
            parts = line.split(None, 2)
            if len(parts) < 3:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error("tellraw command requires a target and a JSON argument.")
                continue
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
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error(f"Invalid data command syntax: {line}")
                continue

        # --- Return Commands ---
        elif tokens[0].lower() == "return":
            if len(tokens) < 2:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error("return command requires at least one argument")
                continue
            if tokens[1].lower() == "fail":
                if len(tokens) != 3:
                    log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                    log.error("Usage: /return fail <fail status>")
                    continue
                cmd = "return_fail"
                args = [tokens[2]]
                compiled += compile_instr(cmd, args)

            elif tokens[1].lower() == "run":
                if len(tokens) < 3:
                    log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                    log.error("Expecting subcommand at `/return run ...`")
                    continue
                if func_name == 'main':
                    log.warning("/return run in main class. Did you really intend this?", SyntaxWarning)

                # For "return run", compile the subcommand recursively,
                # then output a return_run instruction (with no arguments),
                # followed by the compiled subcommand and a kill_branch instruction.
                subcommand = ' '.join(tokens[2:])
                compiled_subcmd = compile_source(None, subcommand)
                compiled += compile_instr("return_run", [])
                compiled += compiled_subcmd + compile_instr("kill_branch", [])
                continue  # Skip further processing of this line.

            else:
                cmd = "return_"
                args = tokens[1:]
                compiled += compile_instr(cmd, args)

        # --- Tag Commands ---
        elif tokens[0].lower() == "tag":
            if len(tokens) < 3:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error(f"Invalid tag command syntax: {line}")
                continue
            if tokens[1].lower() == "add":
                cmd = "tag_add"
                args = tokens[2:]
            elif tokens[1].lower() == "remove":
                cmd = "tag_remove"
                args = tokens[2:]
            else:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error(f"Invalid tag command syntax: {line}")
                continue

        # --- Function Command ---
        elif tokens[0].lower() == "function":
            if len(tokens) < 2:
                log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                log.error(f'Function command requires at least 2 arguments.')
                continue

            cmd = "run_func"
            rest = ' '.join(tokens[1:])

            mapping = {}  # mapping from original names to positional letters
            if '{' in rest:
                idx = rest.index('{')
                func_name = rest[:idx].strip().removesuffix('.mcfunction')
                json_str = rest[idx:].strip()
                try:
                    func_args = json.loads(json_str)
                    # Use the order in the function call JSON to create the mapping.
                    for i, (orig, value) in enumerate(func_args.items()):
                        mapping[orig] = get_arg_letter(i)
                    # Build the argument list in the call order (ignoring the keys).
                    arg_list = [str(func_args[orig]) for orig in func_args.keys()]
                except Exception as e:
                    log.error(f'Ignoring invalid command in {func_name}: "{line}"')
                    log.error(f"Invalid JSON for function arguments: {json_str} [{e}]")
                    continue
                args = [func_name] + arg_list
            else:
                args = [rest]
            args_map[func_name] = mapping
            to_compile.append(func_name)

        # --- Default ---
        else:
            # Use the command as specified.
            cmd = tokens[0].lower()
            args = tokens[1:]

        compiled += compile_instr(cmd, args)

    return bytes(compiled)

def compile_file(filename:str, func_name:str) -> bytes:
    source = read_file(filename)
    source = preprocess(source, filename)
    return compile_source(func_name, source)

args_map = {}
compiled = []
to_compile = ['main']
def compile_files(path:str) -> dict:
    """
    Compile all .mcfunction files that need to be compiled.
    
    This function processes files in the to_compile list, which starts with 'main'
    and gets expanded as function calls are discovered during compilation.
    
    Args:
        path: Base directory path containing .mcfunction files
        
    Returns:
        A dictionary mapping function names to their compiled bytecode
        
    Raises:
        FileNotFoundError: If a required .mcfunction file is not found
        ValueError: If compilation errors occur
    """
    functions = {}
    while to_compile:
        func = to_compile.pop(0)

        if func in compiled:
            log.debug(f"Already compiled {func}")
            continue

        filename = os.path.join(path, f'{func}.mcfunction')
        filename = filename.replace('\\','/')
        
        if not os.path.exists(filename):
            log.error(f"Function file not found: {filename}")
            raise FileNotFoundError(f"Required function file not found: {filename}")

        functions[func] = compile_file(filename, func)
        compiled.append(func)

    return functions

def read_file(infile: str) -> str:
    """
    Read text content from a file.
    
    Args:
        infile: Path to the file to read
        
    Returns:
        The file content as a string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file can't be read
    """
    try:
        with open(infile, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fall back to system default encoding if UTF-8 fails
        with open(infile, 'r') as f:
            return f.read()

def write_file(outfile: str, data: bytes) -> None:
    """
    Compress and write binary data to a file.
    
    Args:
        outfile: Path to the output file
        data: Binary data to write
        
    Raises:
        PermissionError: If the file can't be written
    """
    data = zlib.compress(data, level=9)
    with open(outfile, 'wb') as f:
        f.write(data)

def write_value(exe: BytesIO, data: bytes, bytes_len: int) -> None:
    """
    Write a length-prefixed value to a binary stream.
    
    Args:
        exe: Binary stream to write to
        data: Actual data bytes to write
        bytes_len: Number of bytes to use for the length prefix
    """
    exe.write(len(data).to_bytes(bytes_len, 'big'))
    exe.write(data)

def create_executable(functions: dict[str, bytes], namespace: str) -> bytes:
    """
    Create a MCFN executable binary from compiled functions.
    
    The executable format is:
    - MAGIC header (4 bytes)
    - FORMAT_VERSION (1 byte)
    - Namespace length (1 byte) + namespace bytes
    - Function count (2 bytes)
    - For each function:
      - Function name length (1 byte) + name bytes
      - Function data length (2 bytes) + function data
    
    Args:
        functions: Dictionary mapping function names to their compiled bytecode
        namespace: Namespace string for the executable
        
    Returns:
        Complete executable as bytes
        
    Raises:
        ValueError: If namespace is too long
    """
    exe = BytesIO()

    # Header
    exe.write(MAGIC)  # 4 bytes magic
    exe.write(FORMAT_VERSION.to_bytes(1, 'big'))  # 1 byte version

    # Namespace
    ns_bytes = namespace.encode('utf-8')
    if len(ns_bytes) > 255:
        error_msg = f"Namespace too long: {len(ns_bytes)} bytes (max 255)"
        log.error(error_msg)
        raise ValueError(error_msg)

    exe.write(len(ns_bytes).to_bytes(1, 'big'))
    exe.write(ns_bytes)

    # Write function count as 2 bytes.
    exe.write(len(functions).to_bytes(2, 'big'))
    for name, data in functions.items():
        name = name.encode('utf-8')
        write_value(exe, name, 1)
        write_value(exe, data, 2)
    return exe.getvalue()

def print_functions(functions):  # sourcery skip: use-join
    for name,data in functions.items():
        data = data.hex(' ')
        block = ''
        for i in range(0, len(data), 170):
            block += f'  {data[i:i + 170].strip()}' + '\n'
        print(f"Compiled {name}:\n{block}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: main.py <namespace> <output file>")
        sys.exit(1)

    namespace = sys.argv[1]
    binary_name = sys.argv[2]

    # Compile
    functions:dict[str,bytes] = compile_files(namespace)

    # Create binary
    binary_executable = create_executable(functions, namespace)

    # Write binary
    write_file(binary_name, binary_executable)

    # Done
    log.info(f"DONE: Compiled {namespace} to {binary_name} in namespace {namespace}")
