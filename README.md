
# DatapackRunner

Compile minecraft functions to bytecode.

## World state

By default the world is empty, with no blocks or entities.
Insturctions can place blocks/entities in the world and access their nbt data.

## Supported commands

### Scoreboards

Acts like registers, there can be any number of scoreboards
and they can each have any number of entries.

### Execute

### Say/tellraw

### Setblock/fill

### Clone

### Data block

### Data entity

### Random

### Summon

### Tag

## Supported entities/blocks

Entity/block physics or interactions are not calculated,
entities/blocks can only be spawned with instructions.

Entity/block id's are not checked, they can be any string.
