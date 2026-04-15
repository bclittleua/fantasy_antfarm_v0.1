About:

Fantasy Antfarm is a fantasy world simulator, complete with diverse regions, adventurers, monsters, and immortal gods. Worlds are generated from an alphnumeric seed and populated with commoners, fighters, wardens (a ranger/rogue hybrid class) and, very rarely, wizards. Every person/npc generated has a host of personal stats and preferences and will seek to align with like-minded adventurers. Adventurers can be good protectors or align themselves with evil monsters. Commoners will attempt to simply survive and procreate, praying to their god of choice.


```
Usage:
Requires Python v3.5+
Be sure all files are in same folder.
- fantfarm_v8.py     main file
- population_v4.py   functions for commoner population/procreation
- summary_v6.py      formats the simulation report at end of sim
- class_v1.py        dataclasses separated from main file for better organization
- legacy_v1.py       functions for adventurer procreation including establishing dynasties/kingdoms
``` 
run in command prompt or powershell: ```python fantfarm_v8.py```

```
Optional flags:
-v                   verbose mode, displays events by tick in terminal
--verbose-importance 1-3, 3 = most. Filters verbose mode events by level of importance. Default =1.
--seed               specify alphanumeric seed. simulation should always produce same results based on seed, duration may produce varying results.
--year               sets how long simulation will run, whole numbers only, default = 1 year
--delay              attempts to slow down verbose mode, can be int or float
```
Example:

```python fantfarm_v8.py -v --verbose-importance 3 --delay .001 --seed GJHasoij2f2JYA --year 50```

Example Output (v5): ```see latest fantfarm_SEED_#year_summary.txt```


POINTS OF INTEREST:

All actors (adventurers, commoners, monsters) broadly use the same stats and make descisions/interactions based on this dataclass:
```
class Actor:
    id: int
    name: str
    role: Role
    alignment: Alignment
    deity: Deity
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    luck: int
    hp: int
    max_hp: int
    region_id: int
    traits: List[str]
    birth_year: int
    birth_month: int
    birth_day: int
    surname: str
    spouse_id: Optional[int] = None
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    last_birth_tick: int = -999999
    title: Optional[str] = None
    alive: bool = True
    party_id: Optional[int] = None
    kills: int = 0
    recovering: int = 0
    reputation: int = 0
    monster_kills: int = 0
    dragon_kills: int = 0
    horror_kills: int = 0
    giant_kills: int = 0
    regions_defended: int = 0
    regions_oppressed: int = 0
    protects_region: Optional[int] = None
    death_timestamp: Optional[str] = None
    death_cause: Optional[str] = None
    death_killer_id: Optional[int] = None
```
