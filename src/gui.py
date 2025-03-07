from disassembler import disassemble_executable
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog
from threading import Thread
import customtkinter as tki
import tkinter as tk
import zlib
import sys
import os
import vm

VERSION = "0.0.1"

branch = vm.root

class CustomRoot(tki.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        tki.CTk.__init__(self)
        self.TkdndVersion = TkinterDnD._require(self)

def main():
    global root
    root = CustomRoot()
    root.title(f"MCFN Gui v{VERSION}")
    root.geometry("800x600")

    # Toolbar
    toolbar_frame = tki.CTkFrame(root, height=35, fg_color="#333333")
    toolbar_frame.pack(side="top", fill="x")

    # File menu button
    file_btn = tki.CTkButton(
        toolbar_frame,
        text="File",
        width=50,
        height=30,
        fg_color="#333333",
        hover_color="#555555",
        corner_radius=0,
        command=lambda: show_file_menu(root, file_btn)
    )
    file_btn.pack(side="left", padx=5)

    # Help menu button
    help_btn = tki.CTkButton(
        toolbar_frame,
        text="Help",
        width=50,
        height=30,
        fg_color="#333333",
        hover_color="#555555",
        corner_radius=0,
        command=lambda: show_help_menu(root, help_btn)
    )
    help_btn.pack(side="left", padx=5)

    # Create main content area for initial state
    content_frame = tki.CTkFrame(root)
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    root.content_frame = content_frame  # Store reference for later access

    tki.CTkLabel(
        content_frame,
        text="Drag and drop an MCFN executable here to debug it.",
        font=(None, 28)
    ).place(relx=0.5, rely=0.4, anchor='center')

    # Add status bar
    status_bar = tki.CTkFrame(root, height=25)
    status_bar.pack(side="bottom", fill="x")
    status_label = tki.CTkLabel(status_bar, text="Ready")
    status_label.pack(side="left", padx=5)
    root.status_label = status_label  # Store for updating later

    def drop(event):
        file_path = event.data.strip('{}')  # Remove curly braces that might be added
        print('File dropped:', file_path)

        try:
            with open(file_path, 'rb') as f:
                bytecode = zlib.decompress(f.read())

            disassembly = disassemble_executable(bytecode)[1]

            # Store the current disassembly for later use (e.g., saving)
            root.current_disassembly = disassembly
            root.current_filename = os.path.basename(file_path)

            show_disassembly(root, disassembly, os.path.basename(file_path))

        except Exception as e:
            raise e
            print(f"Error: {e}")
            show_error(root, f"Error: {e}")

    # Register for file drops
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', drop)

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        set_file(root, file_path)

    root.mainloop()

def open_file(root):
    """Open file dialog and load a file"""
    file_path = filedialog.askopenfilename(
        title="Open MCFN Executable",
        filetypes=[("MCFN Executables", "*.bin"), ("All Files", "*.*")]
    )

    if not file_path:
        return

    set_file(root, file_path)

def set_file(root, file_path):
    try:
        update_status(root, f"Opening {os.path.basename(file_path)}...")
        with open(file_path, 'rb') as f:
            bytecode = zlib.decompress(f.read())

        disassembly = disassemble_executable(bytecode)[1]

        # Store the current disassembly for later use
        root.current_disassembly = disassembly
        root.current_filename = os.path.basename(file_path)

        show_disassembly(root, disassembly, os.path.basename(file_path))
        update_status(root, f"Opened {os.path.basename(file_path)}")

    except Exception as e:
        raise e
        print(f"Error: {e}")
        show_error(root, f"Error: {e}")
        update_status(root, "Error opening file")

def save_disassembly(root):
    """Save the disassembly as a text file"""
    if not hasattr(root, 'current_disassembly'):
        show_error(root, "No disassembly to save")
        return

    file_path = filedialog.asksaveasfilename(
        title="Save Disassembly",
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )

    if not file_path:
        return

    try:
        update_status(root, "Saving disassembly...")
        with open(file_path, 'w') as f:
            for func, lines in root.current_disassembly.items():
                f.write(f"{func}:\n")
                for line in lines:
                    f.write(f"    {line}\n")
                f.write("\n")

        print(f"Saved disassembly to {file_path}")
        update_status(root, f"Saved to {os.path.basename(file_path)}")
    except Exception as e:
        show_error(root, f"Error saving file: {e}")
        update_status(root, "Error saving file")

def show_help():
    """Display help information"""
    help_window = tki.CTkToplevel()
    help_window.title("About MCFN GUI")
    help_window.geometry("500x400")
    help_window.resizable(False, False)

    help_text = f"""
        MCFN GUI v{VERSION}

        This application allows you to view and debug MCFN executables.

        Usage:
        - Drag and drop an MCFN executable (.bin file) onto the window
        - Use the menu options to open, save, or export the disassembly

        Menu options:
        - File > Open: Open an MCFN executable file
        - File > Save As: Save the disassembly as a text file
        - Help > About: Show this information window

        For more information, visit the GitHub repository:
        https://github.com/Omena0/MCFN
    """

    text_widget = tki.CTkTextbox(help_window, width=480, height=350)
    text_widget.pack(padx=10, pady=(10,0))
    text_widget.insert("1.0", help_text)
    text_widget.configure(state="disabled")

    close_btn = tki.CTkButton(
        help_window,
        width=100,
        height=35,
        text="Close",
        command=help_window.destroy
    )
    close_btn.pack(pady=5)

### Most of the shit is here ###
def show_disassembly(root, disassembly, filename):
    """Display the disassembly in the main window with debugging features"""
    global executable, namespace, functions

    # Initialize vm
    executable = vm.read_executable(filename)
    namespace, functions = vm.parse_executable(executable)

    # global namespace, functions
    vm.namespace = namespace
    vm.functions = functions

    main = functions[f'main']
    vm.root.program = main

    vm.debugHook = debug_hook

    # Clear the content frame
    if hasattr(root, 'content_frame'):
        for widget in root.content_frame.winfo_children():
            widget.destroy()
    else:
        # Create new content frame if it doesn't exist
        content_frame = tki.CTkFrame(root)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        root.content_frame = content_frame

    # Add a title
    tki.CTkLabel(
        root.content_frame,
        text=f"Disassembly of {filename}",
        font=(None, 20)
    ).pack(anchor='w',pady=(5, 10))

    # Create a horizontal split with debug controls on left, assembly on right
    main_frame = tki.CTkFrame(root.content_frame)
    main_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Left panel - Debug controls and state
    debug_panel = tki.CTkFrame(main_frame, width=200)
    debug_panel.pack(side="left", fill="y")

    # State display section
    state_frame = tki.CTkFrame(debug_panel)
    state_frame.pack(fill="x", padx=10, pady=(0,10))

    tki.CTkLabel(
        state_frame,
        text="Execution State",
        font=(None, 16)
    ).pack(anchor="w")

    # Program counter
    pc_frame = tki.CTkFrame(state_frame)
    pc_frame.pack(fill="x", pady=2)
    tki.CTkLabel(pc_frame, text="PC:").pack(side="left", padx=5)
    pc_var = tk.StringVar(value="0")
    pc_label = tki.CTkLabel(pc_frame, textvariable=pc_var, width=100)
    pc_label.pack(side="left", padx=10, fill="x", expand=True)

    # Branch count
    branch_frame = tki.CTkFrame(state_frame)
    branch_frame.pack(fill="x", pady=2)
    tki.CTkLabel(branch_frame, text="Branches:").pack(side="left", padx=5)
    branch_var = tk.StringVar(value="0")
    branch_label = tki.CTkLabel(branch_frame, textvariable=branch_var, width=100)
    branch_label.pack(side="left", padx=10, fill="x", expand=True)

    # Status
    status_frame = tki.CTkFrame(state_frame)
    status_frame.pack(fill="x", pady=2)
    tki.CTkLabel(status_frame, text="Status:").pack(side="left", padx=5)
    status_var = tk.StringVar(value="Ready")
    status_label = tki.CTkLabel(status_frame, textvariable=status_var, width=100)
    status_label.pack(side="left", padx=10, fill="x", expand=True)

    # Debug controls section
    controls_frame = tki.CTkFrame(debug_panel)
    controls_frame.pack(fill="x", padx=10, pady=(0, 5))

    tki.CTkLabel(
        controls_frame,
        text="Debug Controls",
        font=(None, 16)
    ).grid(row=0, column=0, pady=(0, 5))

    # Run button
    run_btn = tki.CTkButton(
        controls_frame,
        text="▶ Run",
        height=25,
        command=lambda: start_execution(root),
    )
    run_btn.grid(row=1, column=0)

    # Pause button
    pause_btn = tki.CTkButton(
        controls_frame,
        text="⏸ Pause",
        height=25,
        command=lambda: pause_execution(root)
    )
    pause_btn.grid(row=1, column=1)

    # Step button
    step_btn = tki.CTkButton(
        controls_frame,
        text="⏩ Step",
        height=25,
        command=lambda: step_execution(root)
    )
    step_btn.grid(row=2, column=0)

    # Step over button
    step_over_btn = tki.CTkButton(
        controls_frame,
        text="↪ Step Over",
        height=25,
        command=lambda: step_over_execution(root)
    )
    step_over_btn.grid(row=2, column=1)

    # Reset button
    reset_btn = tki.CTkButton(
        controls_frame,
        text="⟳ Reset",
        height=25,
        command=lambda: reset_execution(root)
    )
    reset_btn.grid(row=3, column=0, columnspan=2, sticky="ew")

    # Breakpoints section
    breakpoints_frame = tki.CTkFrame(debug_panel)
    breakpoints_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tki.CTkLabel(breakpoints_frame, text="Breakpoints", font=(None, 16)).pack(anchor="w", pady=(0, 5))

    # Breakpoints list
    breakpoints_list = tki.CTkTextbox(breakpoints_frame, height=100)
    breakpoints_list.pack(fill="both", expand=True, pady=5)
    breakpoints_list.insert("1.0", "Click on line numbers to add breakpoints")
    breakpoints_list.configure(state="disabled")

    # Clear breakpoints button
    clear_bp_btn = tki.CTkButton(
        breakpoints_frame,
        text="Clear All Breakpoints",
        height=30,
        command=lambda: clear_breakpoints(root)
    )
    clear_bp_btn.pack(fill="x", pady=2)

    # Right panel - Assembly view
    assembly_frame = tki.CTkFrame(main_frame)
    assembly_frame.pack(side="right", fill="both", expand=True)

    # Create a frame for the line numbers and assembly text
    code_container = tki.CTkFrame(assembly_frame)
    code_container.pack(fill="both", expand=True, padx=5, pady=5)

    # Create text widgets
    line_numbers = tki.CTkTextbox(code_container, width=50, fg_color=("#EBEBEB", "#333333"))
    line_numbers.pack(side="left", fill="y")

    code_frame = tki.CTkFrame(code_container)
    code_frame.pack(side="right", fill="both", expand=True)

    assembly_text = tki.CTkTextbox(code_frame)
    assembly_text.pack(side="top", fill="both", expand=True)

    # Access the underlying tkinter Text widgets
    tk_assembly_text = assembly_text._textbox
    tk_line_numbers = line_numbers._textbox

    # Insert the disassembly text
    line_num = 1
    main_function = 'main'

    # Store code lines for reference
    code_lines = []

    if not main_function and disassembly:
        # Use first function if main not found
        main_function = list(disassembly.keys())[0]

    # Configure tags on the underlying tkinter Text widget
    tk_assembly_text.tag_configure("function_header", font=("Courier", 12, "bold"))
    tk_assembly_text.tag_configure("current_line", background="#4A6CD4")
    tk_assembly_text.tag_configure("breakpoint", background="#D44A4A")
    tk_assembly_text.tag_configure("arrow", foreground="#00FF00", font=("Courier", 12, "bold"))

    # Add function header
    if main_function:
        tk_assembly_text.insert("end", f"{main_function}:\n", "function_header")
        tk_line_numbers.insert("end", f"{line_num}\n")
        line_num += 1
        code_lines.append(None)  # Header line

        # Insert instructions
        for instruction in disassembly[main_function]:
            line_text = f"    {instruction}\n"
            tk_assembly_text.insert("end", line_text)
            tk_line_numbers.insert("end", f"{line_num}\n")

            # Save this code line for later reference
            code_lines.append((main_function, instruction))
            line_num += 1

    # Highlight the first instruction
    if len(code_lines) > 1:
        tk_assembly_text.tag_add("current_line", "2.0", "2.end+1c")
        tk_assembly_text.tag_add("arrow", "2.0", "2.4")
        tk_assembly_text.insert("2.0", "→ ")

    # Make both text areas read-only
    assembly_text.configure(state="disabled")
    line_numbers.configure(state="disabled")

    # Store debugging state with both the CTkTextbox and underlying Text widgets
    root.debug_state = {
        "pc": 0,
        "branch_count": 0,
        "instr_count": 0,
        "breakpoints": set(),
        "running": False,
        "code_lines": code_lines,
        "assembly_text": assembly_text,
        "tk_assembly_text": tk_assembly_text,  # Store reference to tkinter widget
        "line_numbers": line_numbers,
        "tk_line_numbers": tk_line_numbers,  # Store reference to tkinter widget
        "pc_var": pc_var,
        "branch_var": branch_var,
        "status_var": status_var,
        "breakpoints_list": breakpoints_list
    }

    # Modify the line_click function to use tk_assembly_text
    def line_click(event):
        if not hasattr(root, 'debug_state'):
            return

        # Get line number from click position
        index = tk_line_numbers.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])

        # First line is function name, can't set breakpoint there
        if line_num == 1 or line_num >= len(code_lines):
            return

        # Toggle breakpoint
        if line_num in root.debug_state["breakpoints"]:
            # Remove breakpoint
            root.debug_state["breakpoints"].remove(line_num)
            tk_assembly_text.tag_remove("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")
        else:
            # Add breakpoint
            root.debug_state["breakpoints"].add(line_num)
            tk_assembly_text.tag_add("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")

        # Update breakpoints list
        update_breakpoints_list(root)

        # Enable editing temporarily to make changes
        assembly_text.configure(state="normal")
        line_numbers.configure(state="normal")

        # Restore read-only state
        assembly_text.configure(state="disabled")
        line_numbers.configure(state="disabled")

    # Bind click event to line numbers
    tk_line_numbers.bind("<Button-1>", line_click)

    # Start the virtual machine
    Thread(
        target=vm.run,
        args=(vm.root, functions, namespace),
        daemon=True
    ).start()

def update_breakpoints_list(root):
    """Update the display of current breakpoints"""
    if not hasattr(root, 'debug_state'):
        return

    breakpoints_list = root.debug_state["breakpoints_list"]
    code_lines = root.debug_state["code_lines"]

    # Enable editing temporarily
    breakpoints_list.configure(state="normal")
    breakpoints_list.delete("1.0", "end")

    if not root.debug_state["breakpoints"]:
        breakpoints_list.insert("1.0", "No breakpoints set")
    else:
        for bp in sorted(root.debug_state["breakpoints"]):
            if 1 <= bp < len(code_lines):
                func, instr = code_lines[bp-1]
                breakpoints_list.insert("end", f"Line {bp}: {instr}\n")

    breakpoints_list.configure(state="disabled")

# Debugging control functions

quit = None
last_pc = 0
execution_lock = 0
last_function = 'main'
def debug_hook(branch: vm.Branch) -> bool:
    """
    Debug hook function called by the VM before executing each instruction.

    Returns:
        - True: Continue execution
        - False: Pause execution (wait)
        - 'quit': Terminate the VM
    """
    global execution_lock, quit, last_function, last_pc, root

    # Make the current branch available globally for inspection
    globals()["branch"] = branch

    # Update the UI with the current execution state
    if hasattr(root, 'debug_state'):
        # Update basic branch info
        root.debug_state["pc"] = branch.program_counter
        root.debug_state["branch_count"] = len(vm.branches)
        root.debug_state["running"] = bool(execution_lock != 0)

        # Update UI elements
        if "pc_var" in root.debug_state:
            root.debug_state["pc_var"].set(str(branch.program_counter))
        if "branch_var" in root.debug_state:
            root.debug_state["branch_var"].set(str(len(vm.branches)))

        # Track instructions executed
        if "instr_count" in root.debug_state and (branch.function != last_function or branch.program_counter != last_pc):
            root.debug_state["instr_count"] += 1

        # Check if the current position has changed
        if branch.function != last_function or branch.program_counter != last_pc:
            # Update the highlighted line in the UI
            update_execution_pointer(root, branch.program_counter)

            # Update the UI
            root.update_idletasks()

    # Update tracking variables
    last_function = branch.function
    last_pc = branch.program_counter

    # Handle execution control
    if quit is not None:
        # Reset the quit flag and terminate VM
        temp = quit
        quit = None
        return temp

    # If execution_lock is positive, decrement it (for step mode)
    if execution_lock > 0:
        execution_lock -= 1

    # Return true if we should continue executing (non-zero execution_lock)
    return bool(execution_lock != 0)

def update_highlight(root, new_line_index):
    """
    Update the highlighting for the current execution line.
    """
    global branch
    if not hasattr(root, 'debug_state'):
        return

    # Don't recreate the entire text - just update highlighting
    update_execution_pointer(root, new_line_index)

    # Update the current line in debug state
    root.debug_state["current_line"] = new_line_index

def update_execution_pointer(root, new_line_index):
    """
    Remove all arrows and highlighting, then mark the current line.
    """
    if not hasattr(root, 'debug_state'):
        return

    assembly_text = root.debug_state.get("assembly_text")
    tk_assembly_text = root.debug_state.get("tk_assembly_text")

    if not assembly_text or not tk_assembly_text:
        return

    # Enable editing
    assembly_text.configure(state="normal")

    try:
        # Remove current line highlighting
        tk_assembly_text.tag_remove("current_line", "1.0", "end")

        # Find and remove all arrow characters
        for i in range(1, int(tk_assembly_text.index('end').split('.')[0])):
            line_text = tk_assembly_text.get(f"{i}.0", f"{i}.end")
            if "→" in line_text:
                arrow_idx = line_text.find("→")
                tk_assembly_text.delete(f"{i}.{arrow_idx}", f"{i}.{arrow_idx + 2}")

        # Calculate the line number for highlighting
        # +1 for 0-based indexing, +1 for function header
        current_line = new_line_index + 2

        # Add highlighting to the current line
        tk_assembly_text.tag_add("current_line", f"{current_line}.0", f"{current_line}.end+1c")

        # Insert the arrow at the beginning of the line
        tk_assembly_text.insert(f"{current_line}.0", "→ ")
        tk_assembly_text.tag_add("arrow", f"{current_line}.0", f"{current_line}.2")

        # Make sure the line is visible
        tk_assembly_text.see(f"{current_line}.0")

        # Store the current line index
        root.debug_state["current_line"] = new_line_index
    except Exception as e:
        print(f"Error updating execution pointer: {e}")
    finally:
        # Restore read-only state
        assembly_text.configure(state="disabled")

def start_execution(root):
    global execution_lock
    """Start or resume execution of the code"""
    if not hasattr(root, 'debug_state'):
        return

    root.debug_state["running"] = True
    root.debug_state["status_var"].set("Running")

    # Allow execution
    execution_lock = -1

    # Set status
    update_status(root, "Started execution")

def pause_execution(root):
    global execution_lock
    """Pause execution"""
    if not hasattr(root, 'debug_state') or not root.debug_state["running"]:
        return

    execution_lock = 0

    root.debug_state["running"] = False
    root.debug_state["status_var"].set("Paused")
    update_status(root, "Paused execution")

def step_execution(root):
    """Execute one instruction and then pause"""
    global execution_lock
    if not hasattr(root, 'debug_state'):
        return

    # Set execution lock to allow exactly one instruction
    execution_lock = 1

    # Update UI immediately
    if "status_var" in root.debug_state:
        root.debug_state["status_var"].set("Stepped")
    update_status(root, "Stepped execution")

def reset_execution(root):
    """Reset execution to beginning"""
    global execution_lock, quit
    if not hasattr(root, 'debug_state'):
        return

    # First pause execution
    execution_lock = 0

    # Signal the VM to quit and restart
    quit = 'quit'

    # Wait a moment to ensure the VM has processed the quit signal
    root.after(100, lambda: _complete_reset(root))

def _complete_reset(root):
    """Complete the reset process after the VM has stopped"""
    global execution_lock, last_pc, last_function

    # Reset VM state
    vm.branchId = 0
    vm.branches.clear()  # Clear all existing branches
    vm.root = vm.Branch()  # Create a new root branch
    vm.branches.append(vm.root)  # Add it to the branches list

    # Clear other VM state
    vm.blocks.clear()
    vm.entities.clear()
    vm.scoreboards.clear()

    # Reinstall our debug hook
    vm.debugHook = debug_hook

    # Reset execution trackers
    last_pc = 0
    last_function = 'main'
    execution_lock = 0

    # Reset UI state
    if hasattr(root, 'debug_state'):
        root.debug_state["running"] = False
        root.debug_state["instr_count"] = 0
        root.debug_state["pc"] = 0
        root.debug_state["branch_count"] = 0

        # Update UI elements
        if "pc_var" in root.debug_state:
            root.debug_state["pc_var"].set("0")
        if "branch_var" in root.debug_state:
            root.debug_state["branch_var"].set("0")
        if "status_var" in root.debug_state:
            root.debug_state["status_var"].set("Reset")

        # Update highlighting for first instruction
        update_execution_pointer(root, 0)

    update_status(root, "Reset execution")

    # Initialize the VM with the main function
    if hasattr(vm, 'functions') and 'main' in vm.functions:
        vm.root.program = vm.functions['main']

    # Start the VM in a new thread
    Thread(
        target=vm.run,
        args=(vm.root, vm.functions, vm.namespace),
        daemon=True
    ).start()

def step_over_execution(root):
    """Step over a function call (execute it without stepping into it)"""
    if not hasattr(root, 'debug_state'):
        return

    # In a real implementation, this would need to identify function calls and skip them
    # For now, just use the regular step function as a placeholder
    step_execution(root)
    update_status(root, "Stepped over")

def clear_breakpoints(root):
    """Clear all breakpoints"""
    if not hasattr(root, 'debug_state'):
        return

    assembly_text = root.debug_state["assembly_text"]
    tk_assembly_text = root.debug_state["tk_assembly_text"]  # Get the underlying tkinter widget

    # Enable editing temporarily
    assembly_text.configure(state="normal")

    # Remove all breakpoint highlights
    for line_num in root.debug_state["breakpoints"]:
        tk_assembly_text.tag_remove("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")

    # Clear breakpoints set
    root.debug_state["breakpoints"] = set()

    # Update breakpoints list
    update_breakpoints_list(root)

    # Restore read-only state
    assembly_text.configure(state="disabled")

    update_status(root, "Cleared all breakpoints")

def show_error(root, message):
    """Show an error dialog"""
    error_window = tki.CTkToplevel(root)
    error_window.title("Error")
    error_window.geometry("400x150")
    error_window.resizable(False, False)

    tki.CTkLabel(
        error_window,
        text=message,
        font=(None, 16),
        text_color="red"
    ).pack(pady=(20, 10))

    tki.CTkButton(
        error_window,
        text="OK",
        width=100,
        command=error_window.destroy
    ).pack(pady=10)

def show_info(root, message):
    """Show an information dialog"""
    info_window = tki.CTkToplevel(root)
    info_window.title("Information")
    info_window.geometry("400x150")
    info_window.resizable(False, False)

    tki.CTkLabel(
        info_window,
        text=message,
        font=(None, 16)
    ).pack(pady=(20, 10))

    tki.CTkButton(
        info_window,
        text="OK",
        width=100,
        command=info_window.destroy
    ).pack(pady=10)

def update_status(root, message):
    """Update the status bar with a message"""
    if hasattr(root, 'status_label'):
        root.status_label.configure(text=message)
        root.update_idletasks()

def custom_popup(root, button, options):
    """Create a fully custom popup menu using CTk widgets"""
    # First destroy any existing popups to prevent multiple menus
    for widget in root.winfo_children():
        if isinstance(widget, tki.CTkToplevel) and hasattr(widget, 'is_popup'):
            widget.destroy()

    # Create popup window
    popup = tki.CTkToplevel(root)
    popup.is_popup = True  # Mark as custom popup
    popup.overrideredirect(True)  # Remove window decorations
    popup.attributes("-topmost", True)  # Keep on top

    # Add menu items
    width = 120  # Wider buttons for better text display
    button_height = 30  # Height of each button
    separator_height = 5  # Height of separator (including padding)

    # Calculate total height based on options
    total_height = 0
    buttons = []
    for option in options:
        if option["type"] == "command":
            total_height += button_height
        elif option["type"] == "separator":
            total_height += separator_height

    # Main container frame
    main_frame = tki.CTkFrame(popup, fg_color=("#EBEBEB", "#333333"), corner_radius=0, border_width=0)
    main_frame.pack(fill="both", expand=True)

    # Create buttons for each option
    for i, option in enumerate(options):
        if option["type"] == "command":
            # All buttons have square corners
            btn = tki.CTkButton(
                main_frame,
                text=option["label"],
                command=lambda cmd=option["command"]: (popup.destroy(), cmd()),
                fg_color=("#EBEBEB", "#333333"),
                hover_color=("#DBDBDB", "#555555"),
                anchor="w",
                height=button_height,
                width=width,
                corner_radius=0,  # Square corners for all buttons
                border_width=0,
                text_color=("black", "white")
            )
            btn.pack(fill="x", padx=0, pady=0)
            buttons.append(btn)

        elif option["type"] == "separator":
            separator = tki.CTkFrame(main_frame, height=1, fg_color="gray40", width=width)
            separator.pack(fill="x", padx=5, pady=3)

    # Add a rounded bottom frame to create the appearance of rounded corners
    if buttons:
        # Add rounded bottom cap
        bottom_cap = tki.CTkFrame(main_frame, height=10, fg_color=("#EBEBEB", "#333333"), corner_radius=10)
        bottom_cap.pack(side="bottom", fill="x", padx=0, pady=0)

    # Position popup below button
    x = button.winfo_rootx()
    y = button.winfo_rooty() + button.winfo_height() - 1  # Adjust to overlap slightly with button
    popup.geometry(f"{width}x{total_height}+{x}+{y}")  # Add extra height for bottom cap

    # Function to close the popup
    def close_popup(event=None):
        popup.destroy()

    # Handle focus and close events
    def on_focus_out(event=None):
        if event and (event.widget == popup or event.widget in popup.winfo_children()):
            return  # Don't close if the popup or its children got focus
        close_popup()

    # Bind events and store the IDs
    button_id = root.bind("<Button-1>", on_focus_out, add="+")
    config_id = root.bind("<Configure>", close_popup, add="+")

    # Use a different approach for focus
    popup.after(200, lambda: popup.focus_set())
    popup.bind("<FocusOut>", on_focus_out)

    # Clean up bindings when the popup is destroyed
    def on_destroy(event=None):
        try:
            root.unbind("<Button-1>", button_id)
            root.unbind("<Configure>", config_id)
        except Exception:
            pass  # Silently fail if unbinding causes issues

    popup.bind("<Destroy>", on_destroy)

    return popup

def show_file_menu(root, button):
    options = [
        {"type": "command", "label": "Open...", "command": lambda: open_file(root)},
        {"type": "command", "label": "Save As...", "command": lambda: save_disassembly(root)},
        {"type": "separator"},
        {"type": "command", "label": "Exit", "command": root.quit}
    ]
    custom_popup(root, button, options)

def show_help_menu(root, button):
    options = [
        {"type": "command", "label": "About", "command": show_help}
    ]
    custom_popup(root, button, options)

if __name__ == "__main__":
    main()
