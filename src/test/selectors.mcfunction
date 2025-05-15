// Test file for complex target selector tests
// This tests a variety of target selector features

// Setup test data
scoreboard objectives add health dummy
scoreboard objectives add power dummy
scoreboard objectives add team dummy
scoreboard objectives add status dummy

// Create advanced target selector tests
function test_selectors:
  // Test distance
  execute as @e[distance=..10] run scoreboard players add @s status 1
  
  // Test score matches
  execute as @e[scores={health=10..20}] run scoreboard players add @s status 1
  
  // Test score ranges with brackets
  execute as @e[scores={power=[5]..[15]}] run scoreboard players add @s status 1
  
  // Test combined conditions
  execute as @e[type=zombie,scores={health=20,team=1}] run say I'm a healthy team 1 zombie!
  
  // Test sorting
  execute as @e[sort=nearest,limit=3] run scoreboard players add @s status 1
  
  // Test complex NBT
  execute as @e[nbt={Tags:["boss"],Health:20}] run tellraw @a {"text":"Found boss!","color":"red"}
  
  // Return number of entities with status > 0
  execute store result score result test run execute if entity @e[scores={status=1..}]
  return run scoreboard players get result test
