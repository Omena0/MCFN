
# Increment i
scoreboard players add i var 1

# Exit clause, if i > n
execute if score i var >= n var run return 0

# Sum one + two
scoreboard players operation next var = one var
scoreboard players operation next var += two var

# Shift downwards
scoreboard players operation one var = two var
scoreboard players operation two var = next var

# Call the loop function
function loop
