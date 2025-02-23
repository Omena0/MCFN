
# Calculate the nth Fibonacci number
scoreboard players set n var 1000

scoreboard players set one var 0
scoreboard players set two var 1

function loop

# Display the current value of 'two'
tellraw @a [\
    {"text":"The "},\
    {"score": {"name": "n", "objective": "var"},"underlined": true,"bold": true},\
    {"text":"th Fibonacci number is: "},\
    {"score":{"name": "two","objective":"var"},"bold": true,"color": "green"}\
]
