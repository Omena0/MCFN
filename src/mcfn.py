from disassembler import disassemble_executable
import compiler
import sys
import gui
import vm
import os
import logging
from common import setup_logger

os.chdir(os.path.dirname(sys.argv[0]))

# Setup logger for main application
log = setup_logger("MCFN_Main", logging.INFO)

usage = "Usage: mcfn (run | compile | disassemble) [-w <output_path>] <source_path>"

def run_executable(executable):
    """
    Execute a compiled MCFN binary.
    
    Args:
        executable: The binary executable data
        
    Returns:
        None
    
    Raises:
        ValueError: If the executable is invalid or corrupted
        KeyError: If required functions are missing from the executable
    """
    try:
        log.info("Parsing executable...")
        namespace, functions = vm.parse_executable(executable)
        
        if 'main' not in functions:
            log.error("Executable is missing required 'main' function")
            raise KeyError("Missing 'main' function in executable")
            
        log.info(f"Running executable from namespace '{namespace}'")
        log.info(f"Functions available: {', '.join(functions.keys())}")
        
        vm.run(vm.root, functions, namespace)
        log.info("Execution completed successfully")
    except Exception as e:
        log.error(f"Error executing MCFN binary: {e}")
        raise

def compile_executable(source_path):
    try:
        if not os.path.exists(source_path):
            log.error(f"Source path not found: {source_path}")
            sys.exit(1)
            
        functions = compiler.compile_files(source_path)
        return compiler.create_executable(functions, source_path)
    except Exception as e:
        log.error(f"Error compiling executable: {e}")
        sys.exit(1)

def compile_run(source_path):
    try:
        executable = compile_executable(source_path)
        run_executable(executable)
        return executable
    except Exception as e:
        log.error(f"Error during compile and run: {e}")
        sys.exit(1)

def write_executable(executable, output_path):
    try:
        compiler.write_file(output_path, executable)
        log.info(f"Executable successfully written to {output_path}")
    except Exception as e:
        log.error(f"Error writing executable to {output_path}: {e}")
        sys.exit(1)

def read_executable(input_path):
    try:
        if not os.path.exists(input_path):
            log.error(f"Input file not found: {input_path}")
            sys.exit(1)
            
        return vm.read_executable(input_path)
    except Exception as e:
        log.error(f"Error reading executable from {input_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            exit(gui.main()) # Run GUI app

        if len(sys.argv) in range(2, 3):
            log.error("Insufficient arguments provided")
            print(usage)
            exit(1)

        action = sys.argv[1].lower()
        source_path = sys.argv[-1]
        output_path = None
        
        if "-w" in sys.argv:
            try:
                w_index = sys.argv.index("-w")
                if w_index + 1 >= len(sys.argv) or sys.argv[w_index + 1].startswith('-'):
                    log.error("Missing output path after -w flag")
                    print(usage)
                    exit(1)
                output_path = sys.argv[w_index + 1]
            except ValueError:
                log.error("Invalid command line arguments")
                print(usage)
                exit(1)

        # Validate source_path exists
        if not source_path or source_path.startswith('-'):
            log.error("Missing source path")
            print(usage)
            exit(1)
            
        # Validate action
        valid_actions = ["run", "compile", "disassemble"]
        if action not in valid_actions:
            log.error(f"Invalid action: {action}. Must be one of {valid_actions}")
            print(usage)
            exit(1)

        log.info(f"Executing action: {action} on {source_path}")
        
        # Execute the requested action
        if action == "run":
            if os.path.isdir(source_path):
                log.info(f"Compiling and running directory: {source_path}")
                executable = compile_run(source_path)
            else:
                log.info(f"Running executable file: {source_path}")
                executable = read_executable(source_path)
                run_executable(executable)

        elif action == "compile":
            log.info(f"Compiling source: {source_path}")
            executable = compile_executable(source_path)
            log.info("Compilation successful")

        elif action == "disassemble":
            log.info(f"Disassembling: {source_path}")
            executable = read_executable(source_path)
            executable = disassemble_executable(executable)
            print(executable)
            if output_path:
                try:
                    with open(output_path, 'w') as f:
                        f.write(executable)
                    log.info(f"Disassembly written to {output_path}")
                except Exception as e:
                    log.error(f"Error writing disassembly to {output_path}: {e}")
                    exit(1)

        # Write executable if output path is specified
        if output_path and action != "disassemble":
            write_executable(executable, output_path)
            
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        exit(1)


