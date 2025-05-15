// Test file for recursion limit testing and complex chain execution
// This will create a deep call stack to test VM limits

$scoreboard players set depth recursive $(depth)
scoreboard players set max_depth recursive 100
scoreboard players set result recursive 0

// Start recursion
function recursive:
  // Add to depth counter
  scoreboard players add result recursive 1
  
  // Log depth
  tellraw @a {"text":"Depth: ","extra":[{"score":{"name":"result","objective":"recursive"}}]}
  
  // Check if we reached requested depth or max depth
  execute if score result recursive >= depth recursive run return run scoreboard players get result recursive
  execute if score result recursive >= max_depth recursive run return run scoreboard players get result recursive
  
  // Complex conditional chain
  execute 
    as @s 
    positioned ~ ~1 ~ 
    if score result recursive matches 5..10 
    run tellraw @a {"text":"Special depth level!","color":"gold"}
  
  // Continue recursion
  function recursive
