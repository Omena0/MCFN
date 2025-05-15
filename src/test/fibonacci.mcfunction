// Test file for Fibonacci sequence calculator
// Usage: function fibonacci.mcfunction {"n": 10}

$scoreboard players set n fib $(n)
scoreboard players set a fib 0
scoreboard players set b fib 1
scoreboard players set i fib 0

// Iterative implementation
function calculate_fibonacci:
  // Check if n is 0 or 1 (special cases)
  execute if score n fib matches 0 run return run scoreboard players get a fib
  execute if score n fib matches 1 run return run scoreboard players get b fib
  
  // Loop for n >= 2
  loop:
    // Check if we've calculated enough terms
    execute if score i fib < n fib run function calculate_next
    execute if score i fib >= n fib run return run scoreboard players get a fib
    
function calculate_next:
  // Store old values  
  scoreboard players operation temp fib = a fib
  scoreboard players operation a fib = b fib
  scoreboard players operation b fib += temp fib
  
  // Increment counter
  scoreboard players add i fib 1
  
  // Continue loop
  function loop
