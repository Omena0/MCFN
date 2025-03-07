from disasemble import disassemble_executable # type:ignore
import compiler
import sys
import gui
import vm
import os

os.chdir(os.path.dirname(sys.argv[0]))

usage = "Usage: mcfn (run | compile | disasemble) [-w <output_path>] <source_path>"

def run_executable(executable):
    namespace, functions = vm.parse_executable(executable)
    vm.run(vm.root, functions, namespace)

def compile_executable(source_path):
    functions = compiler.compile_files(source_path)
    executable = compiler.create_executable(functions,source_path)
    return executable

def compile_run(source_path):
    executable = compile_executable(source_path)
    run_executable(executable)
    return executable

def write_executable(executable, output_path):
    compiler.write_file(output_path, executable)

def read_executable(input_path):
    return vm.read_executable(input_path)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        exit(gui.main()) # Run GUI app

    if len(sys.argv) in range(2, 3):
        exit(usage)

    action = sys.argv[1]
    source_path = sys.argv[-1]
    output_path = None
    if "-w" in sys.argv:
        output_path = sys.argv[sys.argv.index("-w") + 1]

    if action == "run":
        if os.path.isdir(source_path):
            executable = compile_run(source_path)
        else:
            executable = read_executable(source_path)
            run_executable(executable)

    elif action == "compile":
        executable = compile_executable(source_path)

    elif action == "disasemble":
        executable = read_executable(source_path)
        executable = disassemble_executable(executable)
        print(executable)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(executable)

    else:
        exit(usage)

    if output_path:
        write_executable(executable, output_path)


