About:
- Fantasy Antfarm is a fantasy world simulator, complete with diverse regions, adventurers, monsters, and immortal gods. Worlds are generated from an alphnumeric seed and populated with commoners, fighters, wardens (a ranger/rogue hybrid class) and, very rarely, wizards. Every person/npc generated has a host of personal stats and preferences and will seek to align with like-minded adventurers. Adventurers can be good protectors or align themselves with evil monsters. Commoners will attempt to simply survive and procreate, praying to their god of choice.

Usage:
- Requires Python v3.5+
- Be sure all files are in same folder.
-- fantfarm_v8.py
-- population_v4.py
-- summary_v6.py
-- class_v1.py
-- legacy_v1.py
 
- run in command prompt or powershell: ```python fantfarm_v8.py```

Optional flags:
- -v                   verbose mode, displays events by tick in terminal
- --verbose-importance 1-3, 3 = most. Filters verbose mode events by level of importance. Default =1.
- --seed               specify alphanumeric seed. simulation should always produce same results based on seed, duration may produce varying results.
- --year               sets how long simulation will run, whole numbers only, default = 1 year
- --delay              attempts to slow down verbose mode, can be int or float

Example Output (v5):
