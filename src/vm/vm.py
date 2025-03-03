from string import ascii_lowercase
from enum import IntEnum, auto
from io import BytesIO
import logging
import random
import pickle
import struct
import zlib
import math
import sys
import re

FORMAT_VERSION = 4

level = logging.DEBUG

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    light_green = "\x1b[92m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)6s: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: light_green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

log = logging.getLogger("MCFN")
log.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(level)

ch.setFormatter(CustomFormatter())

log.addHandler(ch)

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

def parse_instructions(bytecode: bytes) -> list:
    """
    Parses a binary instruction block into a list of instructions with their arguments.
    Binary format for each instruction:
      <argCount:1byte><instruction:1byte>
      Then for each argument:
         <argLen:1byte><argBytes>
    Returns:
      A list of tuples: (instruction_name, [arg1, arg2, ...])
    """
    instructions = []
    stream = BytesIO(bytecode)
    while True:
        header = stream.read(2)
        if len(header) < 2:
            break
        arg_count = header[0]
        instr_code = header[1]
        try:
            instr_name = Instruction(instr_code).name
        except ValueError:
            instr_name = f"UNKNOWN({instr_code})"
        args = []
        for _ in range(arg_count):
            len_byte = stream.read(1)
            if not len_byte:
                break
            arg_len = len_byte[0]
            arg_data = stream.read(arg_len)
            try:
                arg_text = arg_data.decode("utf-8")
            except UnicodeDecodeError:
                arg_text = arg_data.hex()
            # If the instruction is tellraw, attempt to parse JSON text format.
            if (
                    instr_name == "tellraw"
                    and arg_text
                    and ord(arg_text[0]) in {0, 1, 2, 3}
                ):
                arg_text = parse_json_text_format(arg_data)
            args.append(arg_text)
        instructions.append((instr_name, args))
    return instructions

def parse_executable(bytecode: bytes) -> tuple:
    """
        Parses the given bytecode and extracts the namespace and functions.

        The format is as follows:
        - 4 bytes: Magic number ("MCFN")
        - 1 byte: Format version
        - 1 byte: Length of the namespace (N)
        - N bytes: Namespace (UTF-8 encoded string)
        - 1 byte: Number of functions (F)
        - For each function:
            - 1 byte: Length of the function name (L)
            - L bytes: Function name (UTF-8 encoded string)
            - 2 bytes: Length of the instruction block (B)
            - B bytes: Instruction block

        Args:
            bytecode (bytes): The bytecode to parse.
        Returns:
            tuple: A tuple containing the namespace (str) and a dictionary of functions.
                The dictionary keys are function names (str) and the values are lists of instructions.
        Raises:
            ValueError: If the bytecode is invalid or incomplete, or if the format version is unsupported.
    """

    functions = {}
    stream = BytesIO(bytecode)

    header = stream.read(4)
    if len(header) != 4 or header != b"MCFN":
        raise ValueError("Invalid magic number in executable")

    version_byte = stream.read(1)
    if len(version_byte) != 1:
        raise ValueError("Missing version byte")

    version = version_byte[0]
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported format version: {version}")

    # Read namespace.
    ns_len_byte = stream.read(1)

    if len(ns_len_byte) != 1:
        raise ValueError("Missing namespace length")

    ns_len = ns_len_byte[0]
    namespace_bytes = stream.read(ns_len)

    if len(namespace_bytes) != ns_len:
        raise ValueError("Incomplete namespace bytes")

    namespace = namespace_bytes.decode('utf-8')

    # Read function count (now 2 bytes)
    func_count_bytes = stream.read(2)
    if len(func_count_bytes) != 2:
        raise ValueError("Missing function count bytes")
    func_count = struct.unpack(">H", func_count_bytes)[0]

    for _ in range(func_count):
        name_len_byte = stream.read(1)


        if len(name_len_byte) != 1:
            raise ValueError("Unexpected end of file while reading function name length")


        name_len = name_len_byte[0]
        func_name_bytes = stream.read(name_len)


        if len(func_name_bytes) != name_len:
            raise ValueError("Unexpected end of file while reading function name")


        func_name = func_name_bytes.decode('utf-8')
        block_len_bytes = stream.read(2)


        if len(block_len_bytes) != 2:
            raise ValueError("Unexpected end of file while reading instruction block length")

        block_len = struct.unpack(">H", block_len_bytes)[0]
        instr_block = stream.read(block_len)

        if len(instr_block) != block_len:
            raise ValueError(f"Incomplete instruction block for {func_name}")

        instructions = parse_instructions(instr_block)
        functions[func_name] = instructions

    return namespace, functions

def parse_json_text_format(data: bytes) -> dict | list[dict]:
    # sourcery skip: low-code-quality
    """
    Parses the binary JSON text format used for tellraw commands into a structure
    that follows the standard Minecraft JSON text component format.

    Binary formats handled:
      Type 0: Pickled data
         <0><length:1 byte><pickled bytes>
      Type 1: Score component
         <1><nameLen:1><name bytes><objectiveLen:1><objective bytes>
         <propCount:1>
         For each property:
           If property is color (ID 4):
              <propID:1><colorLen:1><color bytes>
           Otherwise (boolean properties, IDs 0-3):
              <propID:1><1>
      Type 2: Text component
         <2><textLen:1><text bytes>
         <propCount:1>
         For each property, same as Type 1.
      Type 3: Array of components
         <3><componentCount:1>
         For each component:
              <compLen:1><compiled component bytes>

    Returns:
      - For Type 0, returns the unpickled object (if a dict or list) or an error object.
      - For Type 1, returns an object with a "score" key along with extra formatting.
      - For Type 2, returns an object with a "text" key and formatting.
      - For Type 3, returns a list of components, each as a dict (or other parsed object),
        matching the way Minecraft represents a JSON text component array.
    """
    from io import BytesIO
    stream = BytesIO(data)
    try:
        type_byte = stream.read(1)[0]
    except IndexError:
        return None

    if type_byte == 0:
        # Pickled data.
        length = stream.read(1)[0]
        pickled_bytes = stream.read(length)
        try:
            obj = pickle.loads(pickled_bytes)
            return obj  # Expected to be a dict or list.
        except Exception:
            return {"error": pickled_bytes.hex()}

    elif type_byte == 1:
        # Score component.
        name_len = stream.read(1)[0]
        name = stream.read(name_len).decode("utf-8")
        obj_len = stream.read(1)[0]
        objective = stream.read(obj_len).decode("utf-8")
        prop_count = stream.read(1)[0]
        props = {}
        for _ in range(prop_count):
            pid = stream.read(1)[0]
            if pid == 4:
                color_len = stream.read(1)[0]
                color = stream.read(color_len).decode("utf-8")
                props["color"] = color
            else:
                value = stream.read(1)[0]
                mapping = {0: "bold", 1: "italic", 2: "strikethrough", 3: "underlined"}
                prop_name = mapping.get(pid, f"prop{pid}")
                props[prop_name] = (value == 1)
        # Standard Minecraft score component JSON.
        result = {
            "score": {
                "name": name,
                "objective": objective
            }
        }
        result.update(props)
        return result

    elif type_byte == 2:
        # Text component.
        text_len = stream.read(1)[0]
        text = stream.read(text_len).decode("utf-8")
        prop_count = stream.read(1)[0]
        props = {}
        for _ in range(prop_count):
            pid = stream.read(1)[0]
            if pid == 4:
                color_len = stream.read(1)[0]
                color = stream.read(color_len).decode("utf-8")
                props["color"] = color
            else:
                value = stream.read(1)[0]
                mapping = {0: "bold", 1: "italic", 2: "strikethrough", 3: "underlined"}
                prop_name = mapping.get(pid, f"prop{pid}")
                props[prop_name] = (value == 1)
        # Standard Minecraft text component.
        result = {"text": text}
        result.update(props)
        return result

    elif type_byte == 3:
        # Array of components.
        count = stream.read(1)[0]
        components = []
        for _ in range(count):
            comp_len = stream.read(1)[0]
            comp_data = stream.read(comp_len)
            component = parse_json_text_format(comp_data)
            components.append(component)
        return components  # Return a list of components.

    else:
        return {"error": data.hex()}

def parse_range(value_str: str) -> tuple[None | int, None | int]:
    """
    Parses a range specification string of the format "[<start>]..[<end>]".
    If either bound is omitted, None is returned for that bound.

    Args:
        value_str (str): The range string, e.g. "[4]..[8]" or "..[8]".

    Returns:
        tuple: A tuple (start, end) where start and end are integers or None.
    """
    range_parts = value_str.split('..')
    if len(range_parts) != 2:
        raise ValueError(f"Invalid range specification: {value_str}")

    def strip_brackets(s: str) -> str:
        s = s.strip()
        if s.startswith('[') and s.endswith(']'):
            return s[1:-1].strip()
        return s

    start_str = strip_brackets(range_parts[0])
    end_str   = strip_brackets(range_parts[1])
    start_value = int(start_str) if start_str != '' else None
    end_value   = int(end_str) if end_str != '' else None
    return start_value, end_value

def parse_nbt_filter(nbt_str: str) -> dict:
    """
    Very naive SNBT parser for use in target selectors.
    Expects an SNBT fragment enclosed in {}.
    For lists, it splits by commas outside brackets.
    This parser supports simple numbers (with an optional trailing 'd' for double)
    and strings (without quotes) and lists.
    Note: This implementation is limited and serves only as an example.
    """
    if not (nbt_str.startswith('{') and nbt_str.endswith('}')):
        raise ValueError("NBT filter must be enclosed in { }")
    content = nbt_str[1:-1].strip()
    result = {}
    if not content:
        return result
    # Split on commas not inside square brackets.
    parts = re.split(r',(?![^\[]*\])', content)
    for part in parts:
        if ':' not in part:
            raise ValueError(f"Invalid NBT fragment part: {part}")
        k, v = part.split(':', 1)
        key = k.strip()
        value = v.strip()
        # If value is a list.
        if value.startswith('[') and value.endswith(']'):
            list_content = value[1:-1].strip()
            if list_content == "":
                result[key] = []
            else:
                # Split on commas
                items = [x.strip() for x in list_content.split(',')]
                parsed_list = []
                for item in items:
                    # Try to convert numbers.
                    try:
                        if item.endswith('d'):
                            parsed_list.append(float(item[:-1]))
                        else:
                            parsed_list.append(int(item))
                    except:
                        parsed_list.append(item)
                result[key] = parsed_list
        else:
            # Try numeric conversion.
            try:
                if value.endswith('d'):
                    result[key] = float(value[:-1])
                else:
                    result[key] = int(value)
            except:
                result[key] = value
    return result

def read_executable(filepath: str) -> bytes:
    with open(filepath, 'rb') as f:
        return zlib.decompress(f.read())

def distance_3d(a, b):
    return sum((x-y)**2 for x,y in zip(a,b))**0.5

def print_formatted_text(text, color, bold, italic, underline):
    """
    Prints the given text with the specified formatting.
    """
    # ANSI escape codes for text formatting
    color_codes = {
        'black': '30', 'red': '31', 'green': '32', 'yellow': '33',
        'blue': '34', 'magenta': '35', 'cyan': '36', 'white': '37'
    }
    reset_code = '\033[0m'
    bold_code = '\033[1m' if bold else ''
    italic_code = '\033[3m' if italic else ''
    underline_code = '\033[4m' if underline else ''
    color_code = f'\033[{color_codes.get(color, "37")}m'

    formatted_text = f"{color_code}{bold_code}{italic_code}{underline_code}{text}{reset_code}"
    print(formatted_text,end='')

def print_json_text(text:dict | list[dict], recursed=False):
    if isinstance(text, list):
        for item in text:
            print_json_text(item, recursed=True)
        print()
        return

    if not isinstance(text, dict):
        print(text)
        return

    if 'text' not in text:
        if 'score' not in text:
            raise ValueError(f'Invalid JSON text format: {text}')

        # Score component
        score = text['score']
        name = score['name']
        objective = score['objective']

        if objective not in scoreboards:
            scoreboards[objective] = {name:0}

        if name not in scoreboards[objective]:
            scoreboards[objective][name] = 0

        text['text'] = scoreboards[objective][name]

    color     = text.get('color', 'white')
    bold      = text.get('bold', False)
    italic    = text.get('italic', False)
    underline = text.get('underlined', False)

    print_formatted_text(text['text'], color, bold, italic, underline)

    if not recursed:
        print()


# Vars

branches = []
branchId = 0

blocks = {}
entities = []
scoreboards = {}

class Branch:
    def __init__(self,
            executor='SERVER',
            position=(0,0,0),
            facing=(0,0),
            program_counter=-1,  # Incremented before instruction is run
            caller=None
        ):
        global branchId

        self.executor = executor
        self.position = position
        self.facing = facing
        self.program = []
        self.program_counter = program_counter
        self.id = branchId
        branchId += 1

        # NEW: store pending execute_store info and result from the previous instruction.
        self.pending_store = None   # Will be set as (store_type, target, objective)
        self.last_value    = 0
        self.caller:Branch = caller # Branch which cloned this branch

        # List of variable values. Use varname_to_int() to get the index based on the variable letter(s)
        self.vars = []

        if self.id == 10000:
            log.warning("There are 10 000 branches, you probably should fix that..")
        branches.append(self)

    def execute_one(self):
        self.program_counter += 1

        if self.program_counter >= len(self.program):
            self.kill()
            return True

        inst, args = self.program[self.program_counter]

        log.debug(f'{"  "*self.id}{inst} {str(args).strip("[]")}')

        result = execute_instruction(self, inst, args)

        if isinstance(result, tuple):
            # Capture the returned value for later use in execute_store.
            self.last_value = result[1]
            return result[0]
        else:
            return result

    def skip_over(self):
        """Skip over the next kill_branch instruction."""
        while self.program_counter < len(self.program):
            inst, args = self.program[self.program_counter]
            if inst == 'kill_branch':
                break

            self.program_counter += 1

    def new(self, executor='SERVER', position=(0,0,0), facing=(0,0), program_counter=-1):
        """Create a new branch."""

        return Branch(executor, position, facing, program_counter, self)

    def clone(self, executor=None, position=None, facing=None, program_counter=None):
        """Clone this branch and return it with the selected attributes modified."""
        if executor is None:
            executor = self.executor

        if position is None:
            position = self.position

        if facing is None:
            facing = self.facing

        if program_counter is None:
            program_counter = self.program_counter

        return self.new(executor, position, facing, program_counter, self)

    def kill(self):
        # Process any pending store before killing the branch.
        if self.pending_store is not None:
            store_type, target, objective = self.pending_store
            value = int(self.last_value) if store_type == "result" else (1 if self.last_value else 0)
            if objective not in scoreboards:
                scoreboards[objective] = {}
            scoreboards[objective][target] = value
            self.pending_store = None
        branches.remove(self)
        self.program_counter = None
        self.executor = None

    def __str__(self):
        return f"Branch(\n  executor={self.executor},\n  position={self.position},\n  facing={self.facing},\n  program_counter={self.program_counter}\n)"

root = Branch()

def eval_target_selector(branch: Branch, selector: str) -> str:
    """Find all entities that match a selector and return their ids"""
    global entities

    # If the selector doesn't start with '@', return
    if not selector.startswith('@'):
        return [selector]

    # Only @e is permitted.
    if selector.split('[', 1)[0] not in {'@e', '@s'}:
        raise ValueError(f'Only @e or @s selector is permitted: {selector}')

    if selector.startswith('@s'):
        included = [branch.executor]
    elif selector.startswith('@e'):
        included = entities
    else:
        raise ValueError(f'Invalid selector: {selector}')

    if not '[' in selector:
        return included

    # Parse selector arguments.
    args = {
        k.strip(): v.strip()
        for (k, v) in [
            i.split('=',1)
            for i in selector.rstrip(']').split('[', 1)[1].split(',')
        ]
    }

    # Filter by entity type.
    if 'type' in args:
        included = [e for e in included if e['type'] == args['type']]

    # Limit option.
    if 'limit' in args:
        included = included[:int(args['limit'])]

    # Distance filter.
    if 'distance' in args:
        d_spec = args['distance']
        if '..' in d_spec:
            parts = d_spec.split('..')
            lower = float(parts[0]) if parts[0] != '' else None
            upper = float(parts[1]) if parts[1] != '' else None
        else:
            val = float(d_spec)
            lower = val
            upper = val

        def in_range(d):
            if lower is not None and d < lower - 1e-6:
                return False
            if upper is not None and d > upper + 1e-6:
                return False
            return True

        included = [e for e in included if in_range(distance_3d(e['position'], branch.position))]

    # Scores filter.
    if 'scores' in args:
        scores_str = args['scores'].strip()
        # Remove surrounding curly braces if present.
        if scores_str.startswith('{') and scores_str.endswith('}'):
            scores_str = scores_str[1:-1].strip()
        # Process one or more score specifications, separated by commas.
        for score_spec in scores_str.split(','):
            parts = score_spec.split('=', 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid score specification: {score_spec}")
            objective = parts[0].strip()
            value_str = parts[1].strip()
            # If the value contains "..", process as a range.
            if '..' in value_str:
                start_value, end_value = parse_range(value_str)

                new_included = []
                for e in included:
                    s_val = scoreboards[e['id']].get(objective, 0)
                    if start_value is not None and s_val < start_value:
                        continue
                    if end_value is not None and s_val > end_value:
                        continue
                    new_included.append(e)
                included = new_included
            else:
                # Process as a single integer value.
                try:
                    eq_value = int(value_str)
                except ValueError:
                    raise ValueError(f"Invalid score value for objective '{objective}': {value_str}")
                included = [e for e in included if scoreboards[e['id']].get(objective, 0) == eq_value]

    # Tag filter.
    if 'tag' in args:
        tag_value = args['tag']
        if tag_value.startswith('!'):
            tag_value = tag_value[1:]
            included = [e for e in included if tag_value not in e.get('tags', [])]
        else:
            included = [e for e in included if tag_value in e.get('tags', [])]

    # Name filter.
    if 'name' in args:
        name_value = args['name']
        if name_value.startswith('!'):
            name_value = name_value[1:]
            included = [e for e in included if e.get('CustomName', '') != name_value]
        else:
            included = [e for e in included if e.get('CustomName', '') == name_value]

    # NBT filter.
    if 'nbt' in args:
        nbt_str = args['nbt']
        negative = False
        if nbt_str.startswith('!'):
            negative = True
            nbt_str = nbt_str[1:]
        try:
            filter_nbt = parse_nbt_filter(nbt_str)
        except Exception as e:
            raise ValueError(f"Invalid NBT filter: {e}")
        def entity_matches_nbt(entity):
            # Assume that the target entity's full NBT is stored in its 'nbt' key.
            if 'nbt' not in entity:
                return False
            return match_nbt(filter_nbt, entity['nbt'])
        if negative:
            included = [e for e in included if not entity_matches_nbt(e)]
        else:
            included = [e for e in included if entity_matches_nbt(e)]

    # x, dx, y, dy, z, dz filters.
    if any(k in args for k in ('x', 'y', 'z', 'dx', 'dy', 'dz')):
        coord_filters = {}
        for coord in ('x', 'y', 'z'):
            if coord in args:
                base = float(args[coord])
                d_key = {'x': 'dx', 'y': 'dy', 'z': 'dz'}[coord]
                if d_key in args:
                    d_val = float(args[d_key])
                else:
                    d_val = 0  # default: region covers one block
                if d_val >= 0:
                    region_min = base
                    region_max = base + d_val + 1
                else:
                    region_min = base + d_val
                    region_max = base + 1
                coord_filters[coord] = (region_min, region_max)

        # If any coordinate filter is active, filter the entities by checking their position.
        if coord_filters:
            def in_region(entity):
                pos = entity.get('position', (0, 0, 0))
                for axis, (min_val, max_val) in coord_filters.items():
                    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
                    if not (min_val <= pos[idx] < max_val):
                        return False
                return True
            included = [e for e in included if in_region(e)]

    # Sort options.
    if 'sort' in args:
        if args['sort'] == 'nearest':
            included = sorted(included, key=lambda e: distance_3d(e['position'], branch.position))
        elif args['sort'] == 'furthest':
            included = sorted(included, key=lambda e: distance_3d(e['position'], branch.position), reverse=True)
        elif args['sort'] == 'random':
            random.shuffle(included)
        # 'arbitrary' does nothing.


    # Return IDs (assuming each entity has an 'id' key).
    return included

def eval_position(branch:Branch, x: str, y: str, z: str) -> tuple:
    """
    Evaluates a position from three coordinate strings.

    Supports:
      - Absolute: e.g. "5"
      - Relative: e.g. "~" or "~2" adds 0 or 2 to the current global position.
      - Camera-relative: e.g. "^" or "^3"
         When any coordinate begins with "^", all three are assumed to be caret coordinates.
         Caret coordinates are applied relative to the current camera direction (facing).

    Globals:
      position: (x,y,z) tuple representing the current world position.
      facing: (yaw,pitch) in degrees representing the current camera orientation.
    """
    base_x, base_y, base_z = branch.position  # current world position
    # If any coordinate starts with "^", process all three as camera-relative.
    if x.startswith("^") or y.startswith("^") or z.startswith("^"):
        # Extract caret offsets; if a component is not provided as caret, assume 0.
        dx = float(x[1:]) if x.startswith("^") and x != "^" else 0.0
        dy = float(y[1:]) if y.startswith("^") and y != "^" else 0.0
        dz = float(z[1:]) if z.startswith("^") and z != "^" else 0.0

        # Compute the forward, right, and up vectors based on the camera's yaw and pitch.
        yaw_deg, pitch_deg = branch.facing
        yaw = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)

        # Forward vector (pointing in the direction the camera is looking).
        f_x = -math.sin(yaw) * math.cos(pitch)
        f_y = math.sin(pitch)
        f_z = math.cos(yaw) * math.cos(pitch)
        # Right vector (points to the right of the camera).
        r_x = math.cos(yaw)
        r_y = 0
        r_z = math.sin(yaw)
        # Up vector is computed as the cross product of forward and right.
        up_x = f_y * r_z - f_z * r_y  # = f_y * r_z
        up_y = f_z * r_x - f_x * r_z
        up_z = f_x * r_y - f_y * r_x  # = -f_y * r_x

        # New position = current position + (right * dx + up * dy + forward * dz)
        new_x = base_x + (dx * r_x + dy * up_x + dz * f_x)
        new_y = base_y + (dx * r_y + dy * up_y + dz * f_y)
        new_z = base_z + (dx * r_z + dy * up_z + dz * f_z)
        return (new_x, new_y, new_z)

    else:
        # For tilde and absolute values, process each coordinate independently.
        def parse_coord(comp_str: str, base: float) -> float:
            # If relative coordinate using tilde, add the offset to base.
            if comp_str.startswith("~"):
                if comp_str == "~":
                    return base
                return base + float(comp_str[1:])
            # Otherwise, it's absolute.
            return float(comp_str)

        new_x = parse_coord(x, base_x)
        new_y = parse_coord(y, base_y)
        new_z = parse_coord(z, base_z)
        return (new_x, new_y, new_z)

def match_nbt(filter_nbt, target_nbt) -> bool:
    """
    Recursively checks that every key/value in filter_nbt exists in target_nbt.
    For lists (other than byte/long/int arrays), the order and number of elements is ignored:
      every element in filter_nbt must appear somewhere in target_nbt.
    For dictionaries, the match is recursive.
    All comparisons are type-sensitive.
    """
    for key, f_val in filter_nbt.items():
        if key not in target_nbt:
            return False
        t_val = target_nbt[key]
        if isinstance(f_val, dict) and isinstance(t_val, dict):
            if not match_nbt(f_val, t_val):
                return False
        elif isinstance(f_val, list) and isinstance(t_val, list):
            # For byte/long/int arrays, we assume that all elements are ints.
            if all(isinstance(x, int) for x in f_val):
                if f_val != t_val:
                    return False
            else:
                # For normal lists, every element from f_val must be in t_val (order and count ignored).
                if len(f_val) == 0 and len(t_val) != 0:
                    return False
                for item in f_val:
                    if item not in t_val:
                        return False
        else:
            if f_val != t_val:
                return False
    return True

def varname_to_int(varname: str) -> int:
    """
    Converts a variable name in the format $<varname> to an integer.
    The conversion is done by summing the ASCII values of each character in <varname>.
    """
    try: return sum((ascii_lowercase.index(char)+1)*(len(ascii_lowercase)**i) for i,char in enumerate(varname.lower())) - 1
    except Exception as e:
        raise ValueError(f'Invalid varname: {varname}') from e

def execute_instruction(branch:Branch, inst, args):
    for i,arg in enumerate(args):
        if str(arg).startswith('$'):
            var = arg.removeprefix('$(').removesuffix(')')
            var = varname_to_int(var)
            if len(branch.vars) <= var:
                raise RuntimeError(f'Variable index out of range: {var}, {branch.vars}')
            args[i] = branch.vars[var]

    match inst:
        case "execute_as":
            executors = eval_target_selector(branch, args[0])
            for executor in executors:
                branch.clone(executor=executor)
            branch.skip_over()

        case "execute_at":
            entity = eval_target_selector(branch, args[0])[0]
            position = (0,0,0) if entity == 'SERVER' else entity['Pos']
            branch.clone(position=position)
            branch.skip_over()

        case "execute_store":
            # Args: store_type, target, objective.
            store_type, target, objective = args
            # Instead of modifying the scoreboard immediately,
            # record the store request on this branch.
            branch.pending_store = (store_type, target, objective)

        case "kill_branch":
            if branch.pending_store is not None:
                store_type, target, objective = branch.pending_store
                # Use the value of the last executed instruction.
                value = int(branch.last_value) if store_type == "result" else bool(branch.last_value)
                if objective not in scoreboards:
                    scoreboards[objective] = {}
                scoreboards[objective][target] = value
                branch.pending_store = None

            if branch.id == 0:
                return False

            branch.kill()
            return True  # Yield

        case "get":
            target = eval_target_selector(branch, args[0])[0]
            objective = args[1]
            if objective not in scoreboards:
                scoreboards[objective] = {}
            if target not in scoreboards[objective]:
                scoreboards[objective][target] = 0
            return None, scoreboards[objective][target]

        case "positioned":
            branch.position = eval_position(branch, *args[:3])

        case "if_block":
            position = eval_position(branch, *args[:3])
            if not blocks.get(position):
                branch.kill()

        case "if_entity":
            entities = eval_target_selector(args[0])
            if not entities:
                branch.kill()

        case "if_score":
            # If the instruction was compiled in range mode (matches)
            if len(args) == 4 and args[2].lower() == "matches":
                target = eval_target_selector(branch, args[0])[0]
                objective = args[1]
                range_spec = args[3]
                start, end = parse_range(range_spec)
                if start is None:
                    start = 0
                if end is None:
                    end = 1000000
                if objective not in scoreboards:
                    scoreboards[objective] = {}
                if target not in scoreboards[objective]:
                    scoreboards[objective][target] = 0
                value = scoreboards[objective][target]
                if not (start <= value < end):
                    branch.skip_over()
            # Relational mode: compare two scores.
            elif len(args) == 5:
                target = eval_target_selector(branch, args[0])[0]
                objective = args[1]
                operator = args[2]
                comp_target = eval_target_selector(branch, args[3])[0]
                comp_objective = args[4]
                # Ensure default score values.
                if objective not in scoreboards:
                    scoreboards[objective] = {}
                if target not in scoreboards[objective]:
                    scoreboards[objective][target] = 0
                if comp_objective not in scoreboards:
                    scoreboards[comp_objective] = {}
                if comp_target not in scoreboards[comp_objective]:
                    scoreboards[comp_objective][comp_target] = 0
                value = scoreboards[objective][target]
                comp_value = scoreboards[comp_objective][comp_target]
                cond = False
                if operator == ">":
                    cond = value > comp_value
                elif operator == "<":
                    cond = value < comp_value
                elif operator == ">=":
                    cond = value >= comp_value
                elif operator == "<=":
                    cond = value <= comp_value
                elif operator in {"==", "="}:
                    cond = value == comp_value
                elif operator in {"!=", "<>"}:
                    cond = value != comp_value
                else:
                    raise ValueError(
                        f"Unknown relational operator: {operator}"
                    )
                if not cond:
                    branch.skip_over()
            else:
                raise ValueError("Invalid argument count for if_score")

        case "unless_block":
            position = eval_position(branch, *args[:3])
            if blocks.get(position):
                branch.kill()

        case "unless_entity":
            entities = eval_target_selector(args[0])
            if entities:
                branch.kill()

        case "unless_score":
            # If the instruction was compiled in range mode (matches)
            if len(args) == 4 and args[2].lower() == "matches":
                target = eval_target_selector(branch, args[0])[0]
                objective = args[1]
                range_spec = args[3]
                start, end = parse_range(range_spec)
                if start is None:
                    start = 0
                if end is None:
                    end = 1000000
                if objective not in scoreboards:
                    scoreboards[objective] = {}
                if target not in scoreboards[objective]:
                    scoreboards[objective][target] = 0
                value = scoreboards[objective][target]
                if start <= value < end:
                    branch.skip_over()

            # Relational mode: compare two scores.
            elif len(args) == 5:
                target = eval_target_selector(branch, args[0])[0]
                objective = args[1]
                operator = args[2]
                comp_target = eval_target_selector(branch, args[3])[0]
                comp_objective = args[4]
                # Ensure default score values.
                if objective not in scoreboards:
                    scoreboards[objective] = {}
                if target not in scoreboards[objective]:
                    scoreboards[objective][target] = 0
                if comp_objective not in scoreboards:
                    scoreboards[comp_objective] = {}
                if comp_target not in scoreboards[comp_objective]:
                    scoreboards[comp_objective][comp_target] = 0
                value = scoreboards[objective][target]
                comp_value = scoreboards[comp_objective][comp_target]
                cond = False
                if operator == ">":
                    cond = value > comp_value
                elif operator == "<":
                    cond = value < comp_value
                elif operator == ">=":
                    cond = value >= comp_value
                elif operator == "<=":
                    cond = value <= comp_value
                elif operator in {"==", "="}:
                    cond = value == comp_value
                elif operator in {"!=", "<>"}:
                    cond = value != comp_value
                else:
                    raise ValueError(
                        f"Unknown relational operator: {operator}"
                    )
                if cond:
                    branch.skip_over()
            else:
                raise ValueError("Invalid argument count for unless_score")

        case "say":
            executor = branch.executor
            if executor != 'SERVER':
                executor = executor['type']

            print(f'[{executor}]', " ".join(args))

        case "tellraw":
            print_json_text(args[0])

        case "add":
            target = eval_target_selector(branch, args[0])[0]
            objective = args[1]

            if objective not in scoreboards:
                scoreboards[objective] = {}

            if target not in scoreboards[objective]:
                scoreboards[objective][target] = 0

            scoreboards[objective][target] += int(args[2])

        case "remove":
            target = eval_target_selector(branch, args[0])[0]
            objective = args[1]
            scoreboards[objective][target] -= int(args[2])

        case "list_scores":
            target = eval_target_selector(branch, args[0])[0]
            if target == '*':
                # Count every entry in every scoreboard
                count = sum(len(scores) for scores in scoreboards.values())
            else:
                count = sum(1 for scores in scoreboards.values() if target in scores)
            return None, count

        case "list_objectives":
            return None, len(scoreboards)

        case "set_score":
            target = eval_target_selector(branch, args[0])[0]
            objective = args[1]
            if objective not in scoreboards:
                scoreboards[objective] = {}
            scoreboards[objective][target] = int(args[2])

        case "operation":
            target = eval_target_selector(branch, args[0])[0]
            target_obj = args[1]
            operation = args[2]
            source = eval_target_selector(branch, args[3])[0]
            source_obj = args[4]

            if target_obj not in scoreboards:
                scoreboards[target_obj] = {}

            if target not in scoreboards[target_obj]:
                scoreboards[target_obj][target] = 0

            if source_obj not in scoreboards:
                scoreboards[source_obj] = {}

            if source not in scoreboards[source_obj]:
                scoreboards[source_obj][source] = 0

            if operation == "=":
                scoreboards[target_obj][target] = scoreboards[source_obj][
                    source
                ]
            elif operation == "+=":
                scoreboards[target_obj][target] += scoreboards[source_obj][
                    source
                ]
            elif operation == "-=":
                scoreboards[target_obj][target] -= scoreboards[source_obj][
                    source
                ]
            elif operation == "*=":
                scoreboards[target_obj][target] *= scoreboards[source_obj][
                    source
                ]
            elif operation == "/=":
                scoreboards[target_obj][target] //= scoreboards[source_obj][
                    source
                ]
            elif operation == "%=":
                scoreboards[target_obj][target] %= scoreboards[source_obj][
                    source
                ]
            elif operation == "<":
                scoreboards[target_obj][target] = min(
                    scoreboards[target_obj][target],
                    scoreboards[source_obj][source],
                )
            elif operation == ">":
                scoreboards[target_obj][target] = max(
                    scoreboards[target_obj][target],
                    scoreboards[source_obj][source],
                )
            elif operation == "><":
                (
                    scoreboards[target_obj][target],
                    scoreboards[source_obj][source],
                ) = (
                    scoreboards[source_obj][source],
                    scoreboards[target_obj][target_obj],
                )
            else:
                raise ValueError(f"Unknown operation: {operation}")

        case "run_func":
            func_name = args[0]
            func_args = args[1:]
            full_func_name = f"{namespace}/{func_name}"
            if full_func_name not in functions:
                raise RuntimeError(f"Function {full_func_name} not found. Functions: {', '.join(functions.keys())}")

            # Create a new Branch and assign its program.
            new_branch = branch.new()
            new_branch.program = functions[full_func_name]
            new_branch.vars = func_args

            return True, new_branch.last_value  # Yield

        case "return_run":
            if branch.id == 0:
                log.warning(f'Return run in root branch.')
                return

            if not branch.caller:
                log.error(f'No caller to return to. {func_name}:{branch.program_counter}')
                return

            # Execute the next instruction immediately
            result = branch.execute_one()

            # Capture output
            if isinstance(result, tuple):
                branch.last_value = result[1]

            # Return to caller
            branch.caller.last_value = branch.last_value
            # Terminate the current branch
            branch.kill()
            return True, branch.last_value

        case _:
            log.info(f'NotImplemented: {inst} {args}')

def run(branch:Branch, functions:dict, namespace:str):
    # global namespace, functions
    globals()['namespace'] = namespace
    globals()['functions'] = functions

    main = functions[f'{namespace}/main']
    root.program = main

    while branches:
        for branch in branches:
            while branch in branches:
                do_yield = branch.execute_one()

                if do_yield:
                    break


if __name__ == "__main__":
    executable = read_executable(sys.argv[1])
    namespace, functions = parse_executable(executable)
    run(root, functions, namespace)

    log.debug(scoreboards)
