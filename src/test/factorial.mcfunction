// Test file for factorial calculation
// Usage: function factorial.mcfunction {"n": 5}

$scoreboard players set n math $(n)
scoreboard players set result math 1

// Recursive implementation
function calculate_factorial:
  execute if score n math matches 1.. run function factorial_step
  return run scoreboard players get result math

function factorial_step:
  scoreboard players operation result math *= n math
  scoreboard players remove n math 1
  function calculate_factorial
