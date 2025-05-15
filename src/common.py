from enum import IntEnum, auto
import logging
import os
import re

os.system('')

MAGIC = b'MCFN'
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


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up and return a configured logger with colored output.
    
    Args:
        name: The name for the logger
        log_level: The logging level (default: INFO)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create console handler with specified log level
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(CustomFormatter())
    
    # Add handler to logger
    logger.addHandler(ch)
    
    return logger

# STYLES for JSON components
STYLES = ["bold", "italic", "strikethrough", "underlined"]

def parse_target_selector(selector: str) -> dict:
    """
    Parse a target selector string into its components.
    This function is for testing purposes and doesn't require a Branch object.
    
    Args:
        selector (str): The selector string to parse (e.g., "@e[type=zombie,distance=5..10]")
        
    Returns:
        dict: A dictionary with "selector" and "args" keys
        
    Example:
        >>> parse_target_selector("@e[type=zombie,distance=5..10,limit=5]")
        {'selector': '@e', 'args': {'type': 'zombie', 'distance': (5, 10), 'limit': 5}}
    """
    result = {"selector": "", "args": {}}
    
    if not selector.startswith('@'):
        return {"selector": selector, "args": {}}
    
    # Extract the base selector (@a, @e, @p, @s, etc.)
    base_selector = selector.split('[', 1)[0]
    result["selector"] = base_selector
    
    # If there are no arguments, return early
    if '[' not in selector:
        return result
    
    # Parse arguments
    args_str = selector.split('[', 1)[1].rstrip(']')
    arg_pairs = [pair.strip() for pair in args_str.split(',')]
    
    for pair in arg_pairs:
        if '=' not in pair:
            continue
        
        key, value = pair.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Parse special cases
        if key == 'distance':
            if '..' in value:
                parts = value.split('..')
                min_val = float(parts[0]) if parts[0] else None
                max_val = float(parts[1]) if parts[1] else None
                result["args"][key] = (min_val, max_val)
            else:
                exact_val = float(value)
                result["args"][key] = (exact_val, exact_val)
        elif key == 'limit':
            result["args"][key] = int(value)
        elif key == 'scores':
            # Handle score object format
            scores = {}
            if value.startswith('{') and value.endswith('}'):
                value = value[1:-1]
            score_pairs = value.split(',')
            for score_pair in score_pairs:
                s_key, s_val = score_pair.split('=')
                if '..' in s_val:
                    parts = s_val.split('..')
                    min_score = int(parts[0]) if parts[0] else None
                    max_score = int(parts[1]) if parts[1] else None
                    scores[s_key] = (min_score, max_score)
                else:
                    scores[s_key] = int(s_val)
            result["args"][key] = scores
        else:
            # For most keys, just store the value directly
            result["args"][key] = value
    
    return result
