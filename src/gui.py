from disassembler import disassemble_executable
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog
from threading import Thread
import customtkinter as tki
import tkinter as tk
import time
import zlib
import sys
import os
import vm

VERSION = "0.0.1"

branch = vm.root

pending_ui_updates = {}
is_resetting = False
last_button_click = {}  # For debouncing

class CustomRoot(tki.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        tki.CTk.__init__(self)
        self.TkdndVersion = TkinterDnD._require(self)

def disassemble_file(file_path:str):
    with open(file_path, 'rb') as f:
        bytecode = zlib.decompress(f.read())

    return disassemble_executable(bytecode)

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
        global file_path
        file_path = event.data.strip('{}')  # Remove curly braces that might be added
        set_file(root, file_path)

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
        disassembly = disassemble_file(file_path)[1]

        # Store the current disassembly for later use
        root.current_disassembly = disassembly
        root.current_filename = os.path.basename(file_path)

        show_disassembly(root, disassembly, os.path.basename(file_path))
        update_status(root, f"Opened {os.path.basename(file_path)}")

    except Exception as e:
        raise e

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

    executable, namespace, functions = initialize_vm(filename)

    main = functions['main']

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
        current_function = root.debug_state.get("current_function", "main")

        # First line is function name, can't set breakpoint there
        if line_num == 1 or line_num >= len(root.debug_state["code_lines"]):
            return

        # Make sure breakpoints is a dict
        update_debug_state(root)

        # Toggle breakpoint
        bp_key = (current_function, line_num)
        if bp_key in root.debug_state["breakpoints"]:
            # Remove breakpoint
            del root.debug_state["breakpoints"][bp_key]
            root.debug_state["tk_assembly_text"].tag_remove("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")
        else:
            # Add breakpoint
            root.debug_state["breakpoints"][bp_key] = True
            root.debug_state["tk_assembly_text"].tag_add("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")

        # Update breakpoints list
        update_breakpoints_list(root)

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

    # Make sure breakpoints is a dict
    update_debug_state(root)

    breakpoints_list = root.debug_state["breakpoints_list"]
    code_lines = root.debug_state["code_lines"]

    # Enable editing temporarily
    breakpoints_list.configure(state="normal")
    breakpoints_list.delete("1.0", "end")

    if not root.debug_state["breakpoints"]:
        breakpoints_list.insert("1.0", "No breakpoints set")
    else:
        # Sort breakpoints by function name and line number
        sorted_breakpoints = sorted(root.debug_state["breakpoints"].keys())
        for func, line_num in sorted_breakpoints:
            if 1 <= line_num < len(code_lines) and code_lines[line_num-1]:
                instruction = root.current_disassembly[func][line_num-2]  # -1 for 0-index, -1 for header
                breakpoints_list.insert("end", f"{func}:{line_num}: {instruction}\n")

    breakpoints_list.configure(state="disabled")

def initialize_vm(filename):
    """Initialize the VM with the executable read and namespace/functions parsed."""
    executable = vm.read_executable(filename)
    namespace, functions = vm.parse_executable(executable)
    vm.namespace = namespace
    vm.functions = functions
    return executable, namespace, functions


# Debugging control functions

def signal(signal:str):
    """Send a signal to the debug hook"""
    global signals
    signals.append(signal)

last_pc = 0
signals = ['update']
execution_lock = 0
last_function = 'main'
step_over_target = None
skip_current_breakpoint = False
def debug_hook(branch: vm.Branch, message_in:str=None) -> bool:
    """
    Debug hook function called by the VM before executing each instruction.
    Must be thread-safe and handle UI updates properly.
    """
    global execution_lock, last_function, last_pc
    global root, signals, skip_current_breakpoint
    global step_over_target

    # Check if we've reached step over target
    if step_over_target and branch.function == step_over_target[0] and branch.program_counter == step_over_target[1]:
        # We've reached the target, pause execution
        execution_lock = 0
        step_over_target = None  # Reset the target
        if root and hasattr(root, 'debug_state'):
            root.debug_state["status_var"].set("Paused")
            update_status(root, "Step over complete")

    # Make the current branch available globally for inspection
    # But in a thread-safe way
    def update_ui():
        global last_function, last_pc
        if not hasattr(root, 'debug_state'):
            return

        # Store current values
        current_pc = branch.program_counter
        current_function = branch.function

        # Cache branch information in the debug_state
        root.debug_state["pc"] = current_pc
        root.debug_state["branch_count"] = len(vm.branches)
        root.debug_state["running"] = execution_lock != 0
        root.debug_state["current_branch"] = branch  # Store reference to current branch

        # Update UI elements
        if "pc_var" in root.debug_state:
            root.debug_state["pc_var"].set(str(current_pc))
        if "branch_var" in root.debug_state:
            root.debug_state["branch_var"].set(str(len(vm.branches)))

        # Check if we need to update the function view first
        if current_function != last_function:
            update_disassembly_view(root, current_function)
        else:
            # PC may or may not have changed, but always update pointer
            update_execution_pointer(root, current_pc)
            root.update_idletasks()

        # Update tracking variables - AFTER using them for comparison
        last_function = current_function
        last_pc = current_pc

    # First handle any messages
    if message_in:
        vm.log.debug(f'Received message: {message_in}')
        if message_in == 'quit':
            _complete_reset(root)

    # Process outgoing messages first for more responsive UI
    while signals:
        signal = signals.pop(0)
        print(f'Signal: {signal}')

        # If we're resetting, only process reset or update signals
        if is_resetting and signal not in ['reset', 'update']:
            print(f"Ignoring signal {signal} during reset")
            continue

        if signal == 'pause':
            # Pause execution
            execution_lock = 0
            if root and hasattr(root, 'debug_state'):
                root.debug_state["status_var"].set("Paused")
                update_status(root, "Paused execution")

        elif signal == 'step':
            # Step execution
            execution_lock = 1
            if root and hasattr(root, 'debug_state'):
                root.debug_state["status_var"].set("Stepping")
                update_status(root, "Stepping execution")

        elif signal == 'step_over':
            # Get current instruction to check if it's a function call
            if branch.program_counter < len(branch.program):

                # Set target for where to pause (current function, next instruction)
                step_over_target = (branch.function, branch.program_counter + 1)

                # Continue execution until we hit the target
                execution_lock = -1

                if root and hasattr(root, 'debug_state'):
                    root.debug_state["status_var"].set("Stepping Over")
                    update_status(root, "Stepping over")

        elif signal == 'continue':
            execution_lock = -1
            if root and hasattr(root, 'debug_state'):
                root.debug_state["status_var"].set("Running")
                update_status(root, "Continued execution")

        elif signal == 'reset':
            vm.log.debug('Resetting VM')
            signals.clear()
            return 'quit'

        elif signal == 'update':
            # Always process update signals
            root.after(0, update_ui)

    # Schedule UI updates on the main thread
    try:
        if ( # Dont update when stepping over function
                root and (
                    branch.program_counter != last_pc
                     or branch.function != last_function
                ) and not step_over_target
            ):
            root.after(0, update_ui)
    except Exception as e:
        print(f"Error scheduling UI update: {e}")

    # Store a global reference to the branch (needed for manual inspection)
    globals()["branch"] = branch

    # If execution_lock is positive, decrement it
    if execution_lock > 0:
        execution_lock -= 1
        return True

    # Return true if we should continue executing (non-zero execution_lock)
    return execution_lock != 0

def show_breakpoint_info(root, branch):
    """Show detailed state information when a breakpoint is hit"""

    # Create a new window
    info_window = tki.CTkToplevel(root)
    info_window.title(f"Breakpoint at {branch.function}:{branch.program_counter}")
    info_window.geometry("700x600")

    # Create a notebook (tabbed interface)
    notebook_frame = tki.CTkFrame(info_window)
    notebook_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create tabs using buttons and frames
    tab_buttons_frame = tki.CTkFrame(notebook_frame)
    tab_buttons_frame.pack(fill="x", pady=5)

    tab_content_frame = tki.CTkFrame(notebook_frame)
    tab_content_frame.pack(fill="both", expand=True, pady=5)

    # Create frames for each tab
    scoreboards_frame = tki.CTkFrame(tab_content_frame)
    entities_frame = tki.CTkFrame(tab_content_frame)
    branch_frame = tki.CTkFrame(tab_content_frame)
    stack_frame = tki.CTkFrame(tab_content_frame)

    # Active tab tracking
    active_tab = tk.StringVar(value="scoreboards")

    def show_tab(tab_name):
        # Hide all tabs
        scoreboards_frame.pack_forget()
        entities_frame.pack_forget()
        branch_frame.pack_forget()
        stack_frame.pack_forget()

        # Update active tab
        active_tab.set(tab_name)

        # Show selected tab
        if tab_name == "scoreboards":
            scoreboards_frame.pack(fill="both", expand=True)
        elif tab_name == "entities":
            entities_frame.pack(fill="both", expand=True)
        elif tab_name == "branch":
            branch_frame.pack(fill="both", expand=True)
        elif tab_name == "stack":
            stack_frame.pack(fill="both", expand=True)

        # Update button colors
        for btn in tab_buttons:
            # Use cget() instead of dictionary access
            if btn.cget("text").lower() == tab_name:
                btn.configure(fg_color="#1F6AA5")
            else:
                btn.configure(fg_color="transparent")

    # Create tab buttons
    tab_buttons = []
    for tab_name in ["Scoreboards", "Entities", "Branch", "Stack"]:
        btn = tki.CTkButton(
            tab_buttons_frame,
            text=tab_name,
            command=lambda t=tab_name.lower(): show_tab(t),
            fg_color="transparent" if tab_name.lower() != active_tab.get() else "#1F6AA5",
            hover_color="#2A8AC0",
            corner_radius=0,
            border_width=0,
            height=30
        )
        btn.pack(side="left", fill="x", expand=True)
        tab_buttons.append(btn)

    # Fill the Scoreboards tab
    tki.CTkLabel(scoreboards_frame, text="Scoreboards", font=("Arial", 16, "bold")).pack(anchor="w", pady=5)
    scoreboard_list = tki.CTkTextbox(scoreboards_frame)
    scoreboard_list.pack(fill="both", expand=True, pady=5)

    # Fill scoreboard data
    scoreboard_list.insert("end", "Scoreboard Values:\n\n")
    if vm.scoreboards:
        for objective, values in vm.scoreboards.items():
            scoreboard_list.insert("end", f"Objective: {objective}\n")
            for target, value in values.items():
                scoreboard_list.insert("end", f"  {target}: {value}\n")
            scoreboard_list.insert("end", "\n")
    else:
        scoreboard_list.insert("end", "No scoreboards defined.")

    # Fill the Entities tab
    tki.CTkLabel(entities_frame, text="Entities", font=("Arial", 16, "bold")).pack(anchor="w", pady=5)
    entities_list = tki.CTkTextbox(entities_frame)
    entities_list.pack(fill="both", expand=True, pady=5)

    # Fill entity data
    entities_list.insert("end", "Entities:\n\n")
    if vm.entities:
        for i, entity in enumerate(vm.entities):
            entities_list.insert("end", f"Entity {i}:\n")
            for key, value in entity.items():
                entities_list.insert("end", f"  {key}: {value}\n")
            entities_list.insert("end", "\n")
    else:
        entities_list.insert("end", "No entities defined.")

    # Fill the Branch tab
    tki.CTkLabel(branch_frame, text="Current Branch", font=("Arial", 16, "bold")).pack(anchor="w", pady=5)
    branch_info = tki.CTkTextbox(branch_frame)
    branch_info.pack(fill="both", expand=True, pady=5)

    # Fill branch data
    branch_info.insert("end", "Branch Information:\n\n")
    branch_info.insert("end", f"ID: {branch.id}\n")
    branch_info.insert("end", f"Function: {branch.function}\n")
    branch_info.insert("end", f"Program Counter: {branch.program_counter}\n")
    branch_info.insert("end", f"Position: {branch.position}\n")
    branch_info.insert("end", f"Executor: {branch.executor}\n")
    branch_info.insert("end", f"Variables: {branch.vars}\n")
    branch_info.insert("end", f"Last Value: {branch.last_value}\n")
    if branch.pending_store:
        store_type, target, objective = branch.pending_store
        branch_info.insert("end", f"Pending Store: {store_type} {target} {objective}\n")

    # Fill the Stack tab
    tki.CTkLabel(stack_frame, text="Call Stack", font=("Arial", 16, "bold")).pack(anchor="w", pady=5)
    stack_info = tki.CTkTextbox(stack_frame)
    stack_info.pack(fill="both", expand=True, pady=5)

    # Fill stack data
    stack_info.insert("end", "Call Stack:\n\n")
    current = branch
    depth = 0
    while current:
        stack_info.insert("end", f"[{depth}] {current.function}:{current.program_counter}\n")
        if current.vars:
            stack_info.insert("end", f"    Variables: {current.vars}\n")

        current = current.caller
        depth += 1

    # Add control buttons
    button_frame = tki.CTkFrame(info_window)
    button_frame.pack(fill="x", pady=10)

    # Continue
    tki.CTkButton(
        button_frame,
        text="Continue",
        command=lambda: (
            info_window.destroy(),  # Close the window
            continue_from_breakpoint(root)  # Call our new function instead
        )
    ).pack(side="left", padx=5)

    tki.CTkButton(
        button_frame,
        text="Step",
        command=lambda: step_execution(root)
    ).pack(side="left", padx=5)

    tki.CTkButton(
        button_frame,
        text="Close",
        command=info_window.destroy
    ).pack(side="right", padx=5)

    # Show the first tab
    show_tab(active_tab.get())

def continue_from_breakpoint(root):
    """Continue execution from a breakpoint, ignoring the current breakpoint"""
    global execution_lock, skip_current_breakpoint, last_pc, last_function, current_position

    # Set flag to skip the current breakpoint
    skip_current_breakpoint = True

    # Store the current position to avoid hitting the same breakpoint again
    current_position = (branch.function, branch.program_counter)

    # Resume execution
    root.debug_state["running"] = True
    root.debug_state["status_var"].set("Running")
    execution_lock = -1

    update_status(root, "Continued execution from breakpoint")

def update_disassembly_view(root, function_name):
    """Update the disassembly view to show the specified function"""
    global pending_ui_updates, is_resetting

    if not hasattr(root, 'debug_state') or not hasattr(root, 'current_disassembly'):
        return

    # If we're resetting, only allow updates to 'main' function
    if (is_resetting or root.debug_state.get("resetting")) and function_name != 'main':
        print(f"Skipping disassembly update for {function_name} during reset")
        return

    # Get references to the UI elements
    assembly_text = root.debug_state.get("assembly_text")
    tk_assembly_text = root.debug_state.get("tk_assembly_text")
    line_numbers = root.debug_state.get("line_numbers")
    tk_line_numbers = root.debug_state.get("tk_line_numbers")

    if not assembly_text or not tk_assembly_text:
        return

    # Cancel any pending disassembly updates
    if "disassembly_update" in pending_ui_updates:
        root.after_cancel(pending_ui_updates["disassembly_update"])
        pending_ui_updates.pop("disassembly_update")

    # Schedule UI update on main thread to avoid race conditions
    task_id = root.after(0, lambda: _do_update_disassembly(
        root,
        function_name,
        assembly_text,
        tk_assembly_text,
        line_numbers,
        tk_line_numbers
    ))
    pending_ui_updates["disassembly_update"] = task_id

def _do_update_disassembly(root, function_name, assembly_text, tk_assembly_text, line_numbers, tk_line_numbers):
    """Actually perform the disassembly update on the main thread"""
    try:
        # Enable editing
        assembly_text.configure(state="normal")
        line_numbers.configure(state="normal")

        # Clear existing content
        tk_assembly_text.delete("1.0", "end")
        tk_line_numbers.delete("1.0", "end")

        # Check if the function exists in the disassembly
        if function_name in root.current_disassembly:
            # Add function header
            tk_assembly_text.insert("end", f"{function_name}:\n", "function_header")
            line_num = 1

            tk_line_numbers.insert("end", f"{line_num}\n")
            line_num += 1
                    # Reset code lines array
            code_lines = [None]
            # Insert instructions
            for instruction in root.current_disassembly[function_name]:
                line_text = f"    {instruction}\n"
                tk_assembly_text.insert("end", line_text)
                tk_line_numbers.insert("end", f"{line_num}\n")

                # Save this code line for later reference
                code_lines.append((function_name, instruction))
                line_num += 1

            # Store the updated code lines
            root.debug_state["code_lines"] = code_lines
            root.debug_state["current_function"] = function_name

            # Update execution pointer highlighting for the current position
            # Use the cached branch state rather than the global branch
            current_pc = root.debug_state.get("pc", 0)
            root.after(10, lambda: _do_update_execution_pointer(root, current_pc, tk_assembly_text))

            # Update breakpoints
            for bp_key in root.debug_state["breakpoints"]:
                if isinstance(bp_key, tuple) and len(bp_key) == 2:
                    func, bp_line = bp_key
                    if func == function_name:
                        try:
                            tk_assembly_text.tag_add("breakpoint", f"{bp_line}.0", f"{bp_line}.end+1c")
                        except Exception as e:
                            print(f"Error adding breakpoint tag: {e}")
        else:
            # Function not found in disassembly
            error_msg = f"Function '{function_name}' not found in disassembly"
            tk_assembly_text.insert("end", error_msg)
            root.debug_state["code_lines"] = []
    except Exception as e:
        print(f"Error updating disassembly: {e}")
    finally:
        # Restore read-only state
        assembly_text.configure(state="disabled")
        line_numbers.configure(state="disabled")

    # Update status
    update_status(root, f"Viewing function: {function_name}")

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
    Schedule this to run on the main thread to avoid race conditions.
    """
    global pending_ui_updates, is_resetting

    if not hasattr(root, 'debug_state') or is_resetting:
        return

    assembly_text = root.debug_state.get("assembly_text")
    tk_assembly_text = root.debug_state.get("tk_assembly_text")

    if not assembly_text or not tk_assembly_text:
        return

    # Cancel any pending pointer updates
    if "pointer_update" in pending_ui_updates:
        root.after_cancel(pending_ui_updates["pointer_update"])
        pending_ui_updates.pop("pointer_update")

    # Schedule the update on the main thread
    task_id = root.after(0, lambda: _do_update_execution_pointer(root, new_line_index, tk_assembly_text))
    pending_ui_updates["pointer_update"] = task_id

def _do_update_execution_pointer(root, new_line_index, tk_assembly_text):
    """Actually perform the execution pointer update on the main thread"""
    if not hasattr(root, 'debug_state'):
        return

    assembly_text = root.debug_state.get("assembly_text")

    if not assembly_text:
        return

    # Enable editing
    assembly_text.configure(state="normal")

    try:
        # Clear existing highlighting and arrows more safely
        tk_assembly_text.tag_remove("current_line", "1.0", "end")
        tk_assembly_text.tag_remove("arrow", "1.0", "end")

        # More aggressively remove all arrow characters
        start_index = "1.0"
        while True:
            arrow_pos = tk_assembly_text.search("→", start_index, "end")
            if not arrow_pos:
                break
            tk_assembly_text.delete(arrow_pos, f"{arrow_pos}+1c")
            start_index = arrow_pos

        # Calculate the line number for highlighting
        # +1 for 0-based indexing, +1 for function header
        current_line = new_line_index + 2

        # Safety check for line number
        line_count = int(tk_assembly_text.index('end').split('.')[0])
        if current_line >= line_count:
            current_line = min(current_line, line_count-1)
        current_line = max(current_line, 1)

        # Add highlighting to the current line
        try:
            tk_assembly_text.tag_add("current_line", f"{current_line}.0", f"{current_line}.end+1c")

            # Insert the arrow at the beginning of the line
            tk_assembly_text.insert(f"{current_line}.0", "→")
            tk_assembly_text.tag_add("arrow", f"{current_line}.0", f"{current_line}.1")

            # Make sure the line is visible
            tk_assembly_text.see(f"{current_line}.0")

            # Force update the UI immediately
            root.update_idletasks()
        except Exception as e:
            print(f"Error highlighting line {current_line}: {e}")

        # Store the current line index
        root.debug_state["current_line"] = new_line_index
    except Exception as e:
        print(f"Error updating execution pointer: {e}")
    finally:
        # Restore read-only state
        assembly_text.configure(state="disabled")

def update_debug_state(root):
    """Update the debug state to use function-specific breakpoints"""
    if not hasattr(root, 'debug_state'):
        return

    # Create breakpoints dict if it doesn't exist
    if "breakpoints" not in root.debug_state:
        root.debug_state["breakpoints"] = {}

    elif isinstance(root.debug_state["breakpoints"], set):
        old_breakpoints = root.debug_state["breakpoints"]
        current_function = root.debug_state.get("current_function", "main")

        new_breakpoints = {
            (current_function, line_num): True
            for line_num in old_breakpoints
            if isinstance(line_num, int)
        }
        root.debug_state["breakpoints"] = new_breakpoints

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
    global execution_lock, skip_current_breakpoint
    if not hasattr(root, 'debug_state'):
        return

    # Send step message
    signal('step')

def reset_execution(root):
    """Reset execution to beginning with debouncing"""
    global execution_lock, signals, last_button_click, is_resetting

    # Prevent rapid button clicks (debouncing)
    current_time = time.time()
    if "reset" in last_button_click and current_time - last_button_click["reset"] < 0.5:
        return  # Ignore clicks that happen within 0.5 seconds

    last_button_click["reset"] = current_time

    if not hasattr(root, 'debug_state') or is_resetting:
        return

    # First pause execution
    execution_lock = 0

    # Signal the VM to reset (handled by debug_hook)
    signal('reset')

def _complete_reset(root):
    """Complete the reset process after the VM has stopped"""
    global execution_lock, last_pc, last_function, signals
    global signals, step_over_target, skip_current_breakpoint
    global pending_ui_updates, is_resetting

    # Set global resetting flag
    is_resetting = True

    # Clear any pending signals
    signals = [s for s in signals if s == 'update']  # Keep only update signals

    # Clear any pending UI updates - Fix the iteration error
    # Make a copy of the keys to prevent dictionary changed size during iteration
    update_keys = list(pending_ui_updates.keys())
    for key in update_keys:
        task_id = pending_ui_updates.get(key)
        if task_id:
            try:
                root.after_cancel(task_id)
            except Exception as e:
                print(f"Error canceling task {key}: {e}")
    pending_ui_updates.clear()

    print('COMPLETE RESET CALLED')

    # Reset VM state
    vm.branchId = 0

    # Create a new root branch
    vm.root.kill()
    vm.root = vm.Branch()
    vm.branches = [vm.root]

    # Clear other VM state
    vm.blocks.clear()
    vm.entities.clear()
    vm.scoreboards.clear()

    # Reinstall our debug hook (just in case)
    vm.debugHook = debug_hook

    # Reset execution trackers
    last_pc = 0
    last_function = 'main'
    execution_lock = 0
    skip_current_breakpoint = False
    step_over_target = None

    # Reset UI state
    if hasattr(root, 'debug_state'):
        # Add a reset flag to prevent duplicate updates
        root.debug_state["resetting"] = True
        root.debug_state["running"] = False
        root.debug_state["pc"] = 0
        root.debug_state["branch_count"] = 0

        # Update status first to show we're resetting
        update_status(root, "Resetting execution...")

        # Do a single update to refresh the view
        def complete_ui_reset():
            if hasattr(root, 'current_disassembly'):
                # First update the disassembly view
                _do_update_disassembly(
                    root,
                    'main',
                    root.debug_state.get("assembly_text"),
                    root.debug_state.get("tk_assembly_text"),
                    root.debug_state.get("line_numbers"),
                    root.debug_state.get("tk_line_numbers")
                )
                # Then update the execution pointer
                _do_update_execution_pointer(
                    root,
                    0,
                    root.debug_state.get("tk_assembly_text")
                )
            # Clear the reset flag
            root.debug_state["resetting"] = False
            # Final status update
            update_status(root, "Reset execution complete")
            # Allow new signals
            global is_resetting
            is_resetting = False

        # Schedule a single UI update with sufficient delay
        task_id = root.after(100, complete_ui_reset)
        pending_ui_updates["complete_ui_reset"] = task_id

    # Start the VM in a new thread after UI is updated
    def start_vm():
        vm.log.info('Started new vm')
        Thread(
            target=vm.run,
            args=(vm.root, vm.functions, vm.namespace),
            daemon=True
        ).start()
        # Only send update signal after VM is started
        signals.append('update')

    # Schedule VM start with delay to ensure UI updates first
    task_id = root.after(200, start_vm)
    pending_ui_updates["start_vm"] = task_id

def step_over_execution(root):
    """Step over a function call (execute it without stepping into it)"""
    if not hasattr(root, 'debug_state'):
        return

    # Simply send step_over message to debug_hook
    signal('step_over')

def clear_breakpoints(root):
    """Clear all breakpoints"""
    if not hasattr(root, 'debug_state'):
        return

    # Make sure breakpoints is a dict
    update_debug_state(root)

    assembly_text = root.debug_state["assembly_text"]
    tk_assembly_text = root.debug_state["tk_assembly_text"]

    # Enable editing temporarily
    assembly_text.configure(state="normal")

    # Remove all breakpoint highlights
    for func, line_num in list(root.debug_state["breakpoints"].keys()):
        if func == root.debug_state.get("current_function"):
            tk_assembly_text.tag_remove("breakpoint", f"{line_num}.0", f"{line_num}.end+1c")

    # Clear breakpoints set
    root.debug_state["breakpoints"].clear()

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
        # Don't show intermediate function view messages during reset
        if hasattr(root, 'debug_state') and root.debug_state.get("resetting") and "Viewing function" in message:
            return

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
