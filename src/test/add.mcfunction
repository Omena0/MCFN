$scoreboard players set num1 var $(num1)
$scoreboard players set num2 var $(num2)
scoreboard players operation num1 var += num2 var
return run scoreboard players get num1 var
