// Test file for complex conditionals and branching
scoreboard players set @s counter 0
scoreboard players set @s max 10

// Loop using execute conditionals
loop:
  execute if score @s counter < @s max run function increment
  execute if score @s counter >= @s max run say Loop complete!

function increment:
  scoreboard players add @s counter 1
  tellraw @a {"text":"Counter: ","color":"gold","extra":[{"score":{"name":"@s","objective":"counter"},"color":"green"}]}
  function loop
