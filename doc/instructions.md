# Insturctions

## Bytecode insturctions

### Executor insturctions

#### as \<entity>

Set the current executor to one matching \<entity>, branch if necesairy

#### at \<entity>

Set the execution position to the one of \<entity>

#### positioned \<x> \<y> \<z>

Set the execution position.

### Conditionals

#### if block/entity/score

Kill the branch if the condition is not met.

#### Unless block/entity/score

Kill the branch if the condition is met.

### Scoreboards

#### add \<target> \<objective> \<amount>

Add \<amount> to the score.

#### remove \<target> \<objective> \<amount>

Remove \<amount> from the score.

#### list

List all objectives

Return success if there are no objectives.

#### list \<target>

List all scores of \<target>

Return success if \<target> has no scores.

#### set \<target> \<objective> \<integer>

Set the score, if the objective does not exist it is created.

\<target> can be any string or \<entity>

#### get \<target> \<objective>

Get the score, defaults to 0.

#### operation \<target> \<objective> \<operation> \<target> <objective>

Perform the operation on 2 scoreboard entries.

If the objective does not exist it is created.

If the score does not exist it defaults to 0.

#### reset \<target> \<objective>

Delete all matching values.

#### store (result|success) score <targets> <objective>

Executes a command and stores its outcome into a scoreboard entry.
Use "result" to store the numerical result of the command or "success" to store whether it executed successfully.

### Output

#### say \<string>

Print "[\<executor>] \<string>" to the console

#### tellraw \<string>/\<json>

Print to the console.

### Blocks

#### setblock \<pos> \<block> [\<data>]

Set the block at \<pos> to \<block> with data

#### fill \<pos1> \<pos2> \<block> \<data>

Fill an area from pos1 to pos2 with \<block> with data.

#### clone \<from1> \<from2> \<to>

Clone area from \<from1> to \<from2> to \<to>

### Data

#### data get block \<pos> \<path>

Get data from a block at path

#### data get entity \<entity> \<path>

Get data from entity at path

#### data merge block \<pos> \<data>

Merge data from \<data> to block at \<pos>

#### data merge entity \<entity> \<data>

Merge data from \<data> to \<entity>

### Random

#### random \<start> \<end>

Return a random number from \<start> to \<end>

### Entities

#### summon \<entityId> \<pos> \<data>

Summon entity with id \<entityId> at \<pos> with \<data>

#### kill \<entity>

Kills \<entity>

### Tag

#### tag add \<entity> \<tag>

Add a tag to \<entity>

#### tag remove \<entity> \<tag>

Remove a tag from \<entity>, return fail if entity does not have tag.

#### kill_branch

Kills the current branch.

If there are instructions after this instruction they will be executed with the root branch.

#### run_func <func name>

Creates a new branch that immediately executes the function identified by <func name>.

#### return [fail] <value>

Returns the value.

#### return run <subcommand>

Run subcommand and return it's result.
