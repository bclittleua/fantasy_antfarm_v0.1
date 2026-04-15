from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import argparse
import random
import time
from typing import Dict, List, Optional, Tuple

import summary


DEFAULT_SEED = None
REGION_COUNT = 12
INITIAL_POPULATION = 500
TICKS_PER_YEAR = 1080
DEFAULT_YEARS = 1
VERBOSE_EVENT_IMPORTANCE = 1
WIZARD_POPULATION_CAP = 0.02

BIOMES = ["Forest", "Plains", "Highlands"]
TIME_OF_DAY = ["Morning", "Midday", "Night"]
MONTH_NAMES = [
    "Dawnsreach", "Rainmoot", "Bloomtide", "Suncrest", "Goldfire", "Highsun",
    "Harvestwane", "Emberfall", "Duskmarch", "Frostturn", "Deepcold", "Yearsend",
]

FIRST_NAMES = [
    "Alden", "Brina", "Cora", "Dain", "Edda", "Fenn", "Garrik", "Hale", "Iris",
    "Joran", "Kara", "Lysa", "Marek", "Nora", "Orin", "Pella", "Quill", "Rhea",
    "Soren", "Talia", "Ulric", "Vera", "Wren", "Ysra", "Bram", "Sel", "Torin",
    "Vale", "Mira", "Galen", "Thora", "Ember", "Rook", "Niall", "Sera",
]

SURNAMES = [
    "Dunn", "Morrow", "Vale", "Briar", "Hart", "Stone", "Ash", "Tanner", "Mills",
    "Rook", "Thorne", "Crowe", "Marsh", "Voss", "Hale", "Wythe", "Fen", "Merrin",
    "Grove", "Ward", "Black", "Hollow", "Reed", "Mercer", "Cross", "Flint", "Dale",
    "Kestrel", "Rowan", "Pike", "Torr", "Wren", "Gage", "Farrow", "Dusk", "Harrow",
]

REGION_PREFIXES = [
    "Green", "Stone", "Ash", "Wolf", "Oak", "Frost", "Gold", "Mist", "Black",
    "River", "Iron", "High", "Deep", "Red",
]

REGION_SUFFIXES = [
    "vale", "run", "mere", "watch", "field", "wood", "reach", "moor", "ford",
    "crest", "pass", "hollow", "heath", "fall",
]

TRAITS = [
    "brave", "cruel", "greedy", "patient", "zealous", "proud", "loyal", "cunning",
    "rash", "suspicious", "merciful", "vengeful", "stern", "curious", "brooding",
]


class Alignment(Enum):
    LAWFUL_GOOD = "Lawful Good"
    NEUTRAL_GOOD = "Neutral Good"
    CHAOTIC_GOOD = "Chaotic Good"
    LAWFUL_NEUTRAL = "Lawful Neutral"
    TRUE_NEUTRAL = "True Neutral"
    CHAOTIC_NEUTRAL = "Chaotic Neutral"
    LAWFUL_EVIL = "Lawful Evil"
    NEUTRAL_EVIL = "Neutral Evil"
    CHAOTIC_EVIL = "Chaotic Evil"

    @property
    def law_axis(self) -> int:
        if "Lawful" in self.value:
            return 1
        if "Chaotic" in self.value:
            return -1
        return 0

    @property
    def moral_axis(self) -> int:
        if "Good" in self.value:
            return 1
        if "Evil" in self.value:
            return -1
        return 0


class Role(Enum):
    COMMONER = "Commoner"
    FIGHTER = "Fighter"
    WIZARD = "Wizard"
    WARDEN = "Warden"


class MonsterKind(Enum):
    GOBLIN = "Goblin"
    GIANT = "Giant"
    DRAGON = "Dragon"
    ANCIENT_HORROR = "Ancient Horror"


class Deity(Enum):
    LORD_OF_DARKNESS = "Lord of Darkness"
    LORD_OF_LIGHT = "Lord of Light"
    GOD_OF_CHANCE = "God of Chance"


ROLE_WEIGHTS: List[Tuple[Role, int]] = [
    (Role.COMMONER, 80),
    (Role.FIGHTER, 12),
    (Role.WARDEN, 6),
    (Role.WIZARD, 2),
]

CHROMATIC_DRAGONS = ["Red", "Blue", "Green", "Black", "White"]
GIANT_TYPES = ["Hill Giant", "Stone Giant", "Frost Giant"]
HORROR_TITLES = ["Whispering Maw", "Sleeper Below", "Many-Eyed Tide", "Void Saint"]


@dataclass
class Region:
    id: int
    name: str
    biome: str
    danger: int
    neighbors: List[int] = field(default_factory=list)
    control: int = 0
    order: int = 60
    ruler_id: Optional[int] = None


@dataclass
class Party:
    id: int
    member_ids: List[int] = field(default_factory=list)
    goal: str = "quest"
    name: Optional[str] = None
    leader_id: Optional[int] = None
    is_large_group: bool = False


@dataclass
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
    birth_month: int
    birth_day: int
    surname: str
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

    def full_name(self) -> str:
        if self.title:
            return f"{self.name} {self.surname}, {self.title}"
        return f"{self.name} {self.surname}"

    def short_name(self) -> str:
        return f"{self.name} {self.surname}"

    def ideology(self) -> Tuple[int, int]:
        return (self.alignment.law_axis, self.alignment.moral_axis)

    def is_adventurer(self) -> bool:
        return self.role != Role.COMMONER

    def is_good(self) -> bool:
        return self.alignment.moral_axis > 0

    def is_evil(self) -> bool:
        return self.alignment.moral_axis < 0

    def is_neutral_morality(self) -> bool:
        return self.alignment.moral_axis == 0

    def needs_rest(self) -> bool:
        return self.hp <= max(2, self.max_hp // 2) or self.recovering > 0

    def mind_score(self) -> int:
        return self.intelligence + self.wisdom

    def level_estimate(self) -> int:
        if self.role == Role.COMMONER:
            return 1
        return 2

    def power_rating(self) -> int:
        base = self.level_estimate() * 3
        base += (self.strength + self.dexterity + self.constitution) // 4
        base += self.reputation // 3
        base += (self.luck - 10) // 3
        if self.role == Role.FIGHTER:
            base += (self.strength + self.constitution) // 4
        elif self.role == Role.WIZARD:
            base += (self.intelligence + self.wisdom) // 3
            base += 2
        elif self.role == Role.WARDEN:
            base += (self.dexterity + self.wisdom) // 4
        return max(1, base)

    def can_join_party_with(self, other: "Actor") -> bool:
        if not self.alive or not other.alive:
            return False
        if not self.is_adventurer() or not other.is_adventurer():
            return False
        if self.id == other.id:
            return False

        law_gap = abs(self.alignment.law_axis - other.alignment.law_axis)
        moral_gap = abs(self.alignment.moral_axis - other.alignment.moral_axis)
        return law_gap <= 1 and moral_gap <= 1

    def is_ideological_enemy(self, other: "Actor") -> bool:
        law_gap = abs(self.alignment.law_axis - other.alignment.law_axis)
        moral_gap = abs(self.alignment.moral_axis - other.alignment.moral_axis)
        return law_gap + moral_gap >= 3

    def attitude_toward(self, other: "Actor") -> str:
        if self.id == other.id or not self.alive or not other.alive:
            return "ignore"

        if self.is_adventurer() and other.role == Role.COMMONER:
            if self.is_good():
                return "protect"
            if self.is_evil():
                return "prey"
            return "ignore"

        if self.role == Role.COMMONER and other.is_adventurer():
            if other.is_evil():
                return "fear"
            if other.is_good():
                return "trust"
            return "ignore"

        if self.is_adventurer() and other.is_adventurer() and self.is_ideological_enemy(other):
            return "oppose"

        return "ignore"


@dataclass
class Monster:
    id: int
    name: str
    kind: MonsterKind
    region_id: int
    power: int
    hostility: int
    charisma: int
    intelligence: int
    alive: bool = True
    horde_size: int = 1
    reputation: int = 0
    patron_actor_id: Optional[int] = None

    def effective_power(self) -> int:
        return self.power + max(0, self.horde_size - 1)


@dataclass
class Event:
    tick: int
    timestamp: str
    text: str
    importance: int = 1
    category: str = "general"


@dataclass
class Commemoration:
    name: str
    month: int
    day: int
    reason: str
    region_id: Optional[int] = None
    actor_id: Optional[int] = None


@dataclass
class World:
    rng: random.Random
    regions: Dict[int, Region]
    actors: Dict[int, Actor]
    monsters: Dict[int, Monster]
    parties: Dict[int, Party]
    events: List[Event] = field(default_factory=list)
    commemorations: List[Commemoration] = field(default_factory=list)
    tick: int = 0
    next_party_id: int = 1
    next_monster_id: int = 1
    seed_used: Optional[str] = None
    generated_by_role: Dict[Role, int] = field(default_factory=lambda: {role: 0 for role in Role})
    generated_monsters_by_kind: Dict[MonsterKind, int] = field(default_factory=lambda: {kind: 0 for kind in MonsterKind})

    def season_name(self, month: int) -> str:
        if month <= 3:
            return "Spring"
        if month <= 6:
            return "Summer"
        if month <= 9:
            return "Autumn"
        return "Winter"

    def current_calendar(self) -> Tuple[int, int, int, str, str]:
        day_index = self.tick // 3
        year = day_index // 360 + 1
        day_of_year = day_index % 360
        month = day_of_year // 30 + 1
        day = day_of_year % 30 + 1
        tod = TIME_OF_DAY[self.tick % 3]
        season = self.season_name(month)
        return year, month, day, tod, season

    def current_timestamp(self) -> str:
        year, month, day, tod, season = self.current_calendar()
        return f"Year {year}, {season}, {MONTH_NAMES[month - 1]} {day}, {tod}"

    def log(self, text: str, importance: int = 1, category: str = "general") -> None:
        self.events.append(Event(tick=self.tick, timestamp=self.current_timestamp(), text=text, importance=importance, category=category))

    def living_actors(self) -> List[Actor]:
        return [actor for actor in self.actors.values() if actor.alive]

    def living_monsters(self) -> List[Monster]:
        return [monster for monster in self.monsters.values() if monster.alive]

    def region_name(self, region_id: int) -> str:
        return self.regions[region_id].name

    def actors_in_region(self, region_id: int) -> List[Actor]:
        return [actor for actor in self.living_actors() if actor.region_id == region_id]

    def monsters_in_region(self, region_id: int) -> List[Monster]:
        return [monster for monster in self.living_monsters() if monster.region_id == region_id]

    def adjust_region_state(self, region_id: int, control_delta: int = 0, order_delta: int = 0) -> None:
        region = self.regions[region_id]
        region.control = max(-100, min(100, region.control + control_delta))
        region.order = max(0, min(100, region.order + order_delta))

    def evaluate_region_rule(self, region_id: int) -> None:
        region = self.regions[region_id]
        local = [actor for actor in self.actors_in_region(region_id) if actor.is_adventurer()]
        if not local:
            region.ruler_id = None
            return

        ranked = sorted(local, key=lambda actor: (actor.reputation, actor.kills, actor.power_rating(), actor.charisma), reverse=True)
        candidate = ranked[0]
        if abs(region.control) >= 30 and region.order >= 25 and candidate.reputation >= 10:
            region.ruler_id = candidate.id
        else:
            region.ruler_id = None

    def add_commemoration(self, name: str, month: int, day: int, reason: str, region_id: Optional[int] = None, actor_id: Optional[int] = None) -> None:
        for item in self.commemorations:
            if item.name == name and item.month == month and item.day == day and item.region_id == region_id:
                return
        self.commemorations.append(
            Commemoration(name=name, month=month, day=day, reason=reason, region_id=region_id, actor_id=actor_id)
        )

    def commemorations_today(self) -> List[Commemoration]:
        _, month, day, _, _ = self.current_calendar()
        return [item for item in self.commemorations if item.month == month and item.day == day]

    def generate_party_name(self, leader: Actor, region_id: int) -> str:
        good_words = ["Wardens", "Shield", "Dawn", "Watch", "Lantern"]
        evil_words = ["Black", "Dominion", "Pact", "Fang", "Hand"]
        neutral_words = ["Company", "Band", "Order", "Road", "Circle"]
        suffixes = ["Company", "Pact", "Watch", "Band", "Circle", "Host"]
        place = self.region_name(region_id)
        if leader.is_good():
            if self.rng.random() < 0.5:
                return f"{self.rng.choice(good_words)} of {place}"
            return f"{place} {self.rng.choice(suffixes)}"
        if leader.is_evil():
            if self.rng.random() < 0.5:
                return f"{self.rng.choice(evil_words)} {self.rng.choice(suffixes)}"
            return f"{leader.surname}'s {self.rng.choice(suffixes)}"
        if self.rng.random() < 0.5:
            return f"{self.rng.choice(neutral_words)} of {place}"
        return f"{place} {self.rng.choice(suffixes)}"

    def remove_from_party(self, actor: Actor) -> None:
        if actor.party_id is None:
            return
        party = self.parties.get(actor.party_id)
        if party and actor.id in party.member_ids:
            party.member_ids.remove(actor.id)
        actor.party_id = None
        if party and len(party.member_ids) <= 1:
            for member_id in list(party.member_ids):
                self.actors[member_id].party_id = None
            self.parties.pop(party.id, None)

    def cleanup_parties(self) -> None:
        for party_id in list(self.parties.keys()):
            party = self.parties[party_id]
            party.member_ids = [mid for mid in party.member_ids if self.actors[mid].alive]
            for mid in party.member_ids:
                self.actors[mid].party_id = party_id
            if len(party.member_ids) >= 6:
                party.is_large_group = True
            if len(party.member_ids) <= 1:
                for mid in party.member_ids:
                    self.actors[mid].party_id = None
                self.parties.pop(party_id, None)

    def create_party(self, members: List[Actor], goal: str = "quest") -> Optional[Party]:
        unique_members = []
        seen = set()
        for member in members:
            if member.alive and member.id not in seen:
                unique_members.append(member)
                seen.add(member.id)
        if len(unique_members) < 2:
            return None

        party = Party(id=self.next_party_id, goal=goal)
        self.next_party_id += 1
        self.parties[party.id] = party
        party.leader_id = unique_members[0].id

        for member in unique_members:
            self.remove_from_party(member)
            member.party_id = party.id
            party.member_ids.append(member.id)

        if len(party.member_ids) >= 3:
            party.name = self.generate_party_name(unique_members[0], unique_members[0].region_id)
        if len(party.member_ids) >= 6:
            party.is_large_group = True

        names = ", ".join(self.actors[mid].short_name() for mid in party.member_ids)
        if party.name:
            self.log(f"A party forms in {self.region_name(unique_members[0].region_id)}: {party.name} ({names}).", importance=2, category="party")
        else:
            self.log(f"A party forms in {self.region_name(unique_members[0].region_id)}: {names}.", importance=2, category="party")
        return party

    def get_party(self, actor: Actor) -> Optional[Party]:
        if actor.party_id is None:
            return None
        return self.parties.get(actor.party_id)

    def side_members(self, actor: Actor) -> List[Actor]:
        party = self.get_party(actor)
        if party is None:
            return [actor] if actor.alive else []
        return [self.actors[mid] for mid in party.member_ids if self.actors[mid].alive]

    def side_power(self, actor: Actor) -> int:
        return sum(member.power_rating() for member in self.side_members(actor))

    def side_charisma(self, actor: Actor) -> float:
        members = self.side_members(actor)
        if not members:
            return 0.0
        return sum(member.charisma for member in members) / len(members)

    def side_mind(self, actor: Actor) -> float:
        members = self.side_members(actor)
        if not members:
            return 0.0
        return sum(member.mind_score() for member in members) / len(members)


class Simulator:
    Role = Role
    MonsterKind = MonsterKind
    Deity = Deity
    MONTH_NAMES = MONTH_NAMES

    def __init__(
        self,
        seed: Optional[str] = DEFAULT_SEED,
        verbose: bool = False,
        verbose_delay: float = 0.0,
        verbose_min_importance: int = VERBOSE_EVENT_IMPORTANCE,
    ) -> None:
        if seed is None:
            seed = self._random_seed_string()
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.verbose_delay = max(0.0, verbose_delay)
        self.verbose_min_importance = max(1, verbose_min_importance)
        self._last_printed_event_index = 0
        self._monster_id_counter = 1
        self.world = self._build_world(seed)

    def _random_seed_string(self) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.SystemRandom().choice(alphabet) for _ in range(12))

    def _weighted_random_deity(self, alignment: Alignment) -> Deity:
        if alignment.moral_axis > 0:
            return self.rng.choices(
                [Deity.LORD_OF_LIGHT, Deity.GOD_OF_CHANCE, Deity.LORD_OF_DARKNESS],
                weights=[65, 25, 10],
                k=1,
            )[0]
        if alignment.moral_axis < 0:
            return self.rng.choices(
                [Deity.LORD_OF_DARKNESS, Deity.GOD_OF_CHANCE, Deity.LORD_OF_LIGHT],
                weights=[65, 25, 10],
                k=1,
            )[0]
        return self.rng.choices(
            [Deity.GOD_OF_CHANCE, Deity.LORD_OF_LIGHT, Deity.LORD_OF_DARKNESS],
            weights=[55, 22, 23],
            k=1,
        )[0]

    def _build_world(self, seed: str) -> World:
        regions = self._generate_regions(REGION_COUNT)
        actors = self._generate_population(INITIAL_POPULATION, regions)
        monsters = self._generate_initial_monsters(regions)
        world = World(rng=self.rng, regions=regions, actors=actors, monsters=monsters, parties={}, seed_used=seed)
        world.generated_by_role = self._count_generated_roles(actors)
        world.generated_monsters_by_kind = self._count_generated_monsters(monsters)
        world.log(
            "A small continent of forest, plains, and highlands fills with common folk, wandering adventurers, lurking monsters, and distant divine attention.",
            importance=3,
            category="world",
        )
        return world

    def _count_generated_roles(self, actors: Dict[int, Actor]) -> Dict[Role, int]:
        counts = {role: 0 for role in Role}
        for actor in actors.values():
            counts[actor.role] += 1
        return counts

    def _count_generated_monsters(self, monsters: Dict[int, Monster]) -> Dict[MonsterKind, int]:
        counts = {kind: 0 for kind in MonsterKind}
        for monster in monsters.values():
            counts[monster.kind] += 1
        return counts

    def _generate_regions(self, count: int) -> Dict[int, Region]:
        regions: Dict[int, Region] = {}
        used_names = set()

        for region_id in range(count):
            regions[region_id] = Region(
                id=region_id,
                name=self._unique_region_name(used_names),
                biome=BIOMES[region_id % len(BIOMES)],
                danger=self.rng.randint(1, 5),
            )

        for region_id in range(count):
            neighbors = set()
            if region_id > 0:
                neighbors.add(region_id - 1)
            if region_id < count - 1:
                neighbors.add(region_id + 1)
            while len(neighbors) < min(3, count - 1) and self.rng.random() < 0.55:
                pick = self.rng.randrange(count)
                if pick != region_id:
                    neighbors.add(pick)
            regions[region_id].neighbors = sorted(neighbors)

        for region_id, region in regions.items():
            for neighbor_id in list(region.neighbors):
                if region_id not in regions[neighbor_id].neighbors:
                    regions[neighbor_id].neighbors.append(region_id)
                    regions[neighbor_id].neighbors.sort()

        return regions

    def _unique_region_name(self, used_names: set[str]) -> str:
        while True:
            name = f"{self.rng.choice(REGION_PREFIXES)}{self.rng.choice(REGION_SUFFIXES)}"
            if name not in used_names:
                used_names.add(name)
                return name

    def _random_person_name(self) -> Tuple[str, str]:
        return self.rng.choice(FIRST_NAMES), self.rng.choice(SURNAMES)

    def _generate_population(self, count: int, regions: Dict[int, Region]) -> Dict[int, Actor]:
        actors: Dict[int, Actor] = {}
        role_choices = [role for role, _ in ROLE_WEIGHTS]
        role_weights = [weight for _, weight in ROLE_WEIGHTS]

        for actor_id in range(1, count + 1):
            role = self.rng.choices(role_choices, weights=role_weights, k=1)[0]
            alignment = self.rng.choice(list(Alignment))
            deity = self._weighted_random_deity(alignment)
            stats = self._roll_stats(role)
            hp = self._base_hp(role, stats[2])
            region_id = self.rng.choice(list(regions.keys()))
            first, surname = self._random_person_name()
            traits = self.rng.sample(TRAITS, k=2)
            actors[actor_id] = Actor(
                id=actor_id,
                name=first,
                surname=surname,
                role=role,
                alignment=alignment,
                deity=deity,
                strength=stats[0],
                dexterity=stats[1],
                constitution=stats[2],
                intelligence=stats[3],
                wisdom=stats[4],
                charisma=stats[5],
                luck=stats[6],
                hp=hp,
                max_hp=hp,
                region_id=region_id,
                traits=traits,
                birth_month=self.rng.randint(1, 12),
                birth_day=self.rng.randint(1, 30),
            )

        wizard_cap = max(1, int(count * WIZARD_POPULATION_CAP))
        wizards = [actor for actor in actors.values() if actor.role == Role.WIZARD]
        if len(wizards) > wizard_cap:
            for actor in wizards[wizard_cap:]:
                actor.role = Role.FIGHTER if self.rng.random() < 0.70 else Role.WARDEN
                stats = self._roll_stats(actor.role)
                actor.strength = stats[0]
                actor.dexterity = stats[1]
                actor.constitution = stats[2]
                actor.intelligence = stats[3]
                actor.wisdom = stats[4]
                actor.charisma = stats[5]
                actor.luck = stats[6]
                actor.max_hp = self._base_hp(actor.role, actor.constitution)
                actor.hp = actor.max_hp

        return actors

    def _generate_initial_monsters(self, regions: Dict[int, Region]) -> Dict[int, Monster]:
        monsters: Dict[int, Monster] = {}
        for region_id in regions:
            goblins = self.rng.randint(2, 5)
            for _ in range(goblins):
                monster = self._make_goblin(region_id)
                monsters[monster.id] = monster
            if self.rng.random() < 0.30:
                monster = self._make_giant(region_id)
                monsters[monster.id] = monster
            if self.rng.random() < 0.03:
                monster = self._make_dragon(region_id)
                monsters[monster.id] = monster
            if self.rng.random() < 0.05:
                monster = self._make_horror(region_id)
                monsters[monster.id] = monster
        return monsters

    def _make_goblin(self, region_id: int) -> Monster:
        monster_id = self._consume_monster_id()
        return Monster(
            id=monster_id,
            name=f"Goblin rabble {monster_id}",
            kind=MonsterKind.GOBLIN,
            region_id=region_id,
            power=self.rng.randint(2, 4),
            hostility=6,
            charisma=self.rng.randint(2, 6),
            intelligence=self.rng.randint(4, 8),
            horde_size=self.rng.randint(4, 12),
            reputation=1,
        )

    def _make_giant(self, region_id: int) -> Monster:
        monster_id = self._consume_monster_id()
        return Monster(
            id=monster_id,
            name=self.rng.choice(GIANT_TYPES),
            kind=MonsterKind.GIANT,
            region_id=region_id,
            power=self.rng.randint(12, 18),
            hostility=7,
            charisma=4,
            intelligence=6,
            horde_size=1,
            reputation=5,
        )

    def _make_dragon(self, region_id: int) -> Monster:
        monster_id = self._consume_monster_id()
        return Monster(
            id=monster_id,
            name=f"{self.rng.choice(CHROMATIC_DRAGONS)} Dragon",
            kind=MonsterKind.DRAGON,
            region_id=region_id,
            power=self.rng.randint(28, 40),
            hostility=9,
            charisma=8,
            intelligence=12,
            horde_size=1,
            reputation=12,
        )

    def _make_horror(self, region_id: int) -> Monster:
        monster_id = self._consume_monster_id()
        return Monster(
            id=monster_id,
            name=self.rng.choice(HORROR_TITLES),
            kind=MonsterKind.ANCIENT_HORROR,
            region_id=region_id,
            power=self.rng.randint(22, 34),
            hostility=9,
            charisma=10,
            intelligence=15,
            horde_size=1,
            reputation=12,
        )

    def _consume_monster_id(self) -> int:
        monster_id = self._monster_id_counter
        self._monster_id_counter += 1
        return monster_id

    def _roll_stats(self, role: Role) -> Tuple[int, int, int, int, int, int, int]:
        stats = [self.rng.randint(6, 15) for _ in range(7)]
        if role == Role.FIGHTER:
            stats[0] += 2
            stats[2] += 1
        elif role == Role.WIZARD:
            stats[3] += 4
            stats[4] += 2
            stats[6] += 1
        elif role == Role.WARDEN:
            stats[1] += 2
            stats[4] += 1
        return tuple(min(stat, 18) for stat in stats)

    def _base_hp(self, role: Role, constitution: int) -> int:
        con_mod = max(-2, (constitution - 10) // 2)
        if role == Role.COMMONER:
            return max(3, 6 + con_mod)
        if role == Role.FIGHTER:
            return max(6, 12 + con_mod)
        if role == Role.WIZARD:
            return max(5, 9 + con_mod)
        return max(5, 10 + con_mod)

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            self.step()
            if self.verbose:
                self._print_new_events()
                if self.verbose_delay > 0:
                    time.sleep(self.verbose_delay)

    def step(self) -> None:
        world = self.world
        world.tick += 1
        world.cleanup_parties()

        for actor in world.living_actors():
            if actor.recovering > 0:
                actor.recovering -= 1
            heal_chance = 0.20 + max(0, actor.luck - 10) * 0.01
            if actor.hp < actor.max_hp and (actor.recovering > 0 or self.rng.random() < heal_chance):
                actor.hp = min(actor.max_hp, actor.hp + 1)

        if world.tick % 3 == 1:
            self._observe_birthdays_and_commemorations()
        self._apply_seasonal_drift()
        self._monster_spawn_check()

        actor_ids = list(world.actors.keys())
        self.rng.shuffle(actor_ids)
        for actor_id in actor_ids:
            actor = world.actors[actor_id]
            if not actor.alive:
                continue
            if actor.is_adventurer():
                self._adventurer_turn(actor)
            else:
                self._commoner_turn(actor)

        monster_ids = list(world.monsters.keys())
        self.rng.shuffle(monster_ids)
        for monster_id in monster_ids:
            monster = world.monsters[monster_id]
            if monster.alive:
                self._monster_turn(monster)

        if world.tick % 30 == 0:
            for region_id in world.regions:
                world.evaluate_region_rule(region_id)
            self._emit_monthly_summary()
        if world.tick % 90 == 0:
            self._emit_season_summary()

    def _monster_spawn_check(self) -> None:
        world = self.world
        if world.tick % 15 != 0:
            return
        region_id = self.rng.choice(list(world.regions.keys()))
        roll = self.rng.random()
        new_monster: Optional[Monster] = None
        if roll < 0.20:
            new_monster = self._make_goblin(region_id)
        elif roll < 0.26:
            new_monster = self._make_giant(region_id)
        elif roll < 0.267:
            new_monster = self._make_dragon(region_id)
        elif roll < 0.277:
            new_monster = self._make_horror(region_id)
        if new_monster is not None:
            world.monsters[new_monster.id] = new_monster
            world.generated_monsters_by_kind[new_monster.kind] += 1
            if new_monster.kind != MonsterKind.GOBLIN:
                world.log(f"Rumors spread of a {new_monster.name} appearing near {world.region_name(region_id)}.", importance=2, category="monster_spawn")

    def _observe_birthdays_and_commemorations(self) -> None:
        world = self.world
        _, month, day, _, _ = world.current_calendar()
        for actor in world.living_actors():
            if actor.birth_month == month and actor.birth_day == day:
                region = world.regions[actor.region_id]
                chance = 0.015 if actor.role == Role.COMMONER else 0.06 + min(0.12, actor.reputation * 0.01)
                if region.order >= 40:
                    chance += 0.03
                if self.rng.random() < chance:
                    if actor.reputation >= 12:
                        holiday_name = f"{actor.name}'s Day"
                        world.add_commemoration(
                            holiday_name,
                            month,
                            day,
                            f"Observed in honor of {actor.short_name()}.",
                            region_id=actor.region_id,
                            actor_id=actor.id,
                        )
                        world.log(
                            f"The people of {world.region_name(actor.region_id)} proclaim {holiday_name} in honor of {actor.short_name()}.",
                            importance=3,
                            category="commemoration",
                        )
                    else:
                        world.log(
                            f"A small gathering in {world.region_name(actor.region_id)} marks the birthday of {actor.short_name()}.",
                            importance=1,
                            category="birthday",
                        )
        for item in world.commemorations_today():
            if self.rng.random() < 0.35:
                if item.region_id is None:
                    world.log(f"The continent observes {item.name}. {item.reason}", importance=2, category="commemoration")
                else:
                    world.log(f"{world.region_name(item.region_id)} observes {item.name}. {item.reason}", importance=2, category="commemoration")

    def _apply_seasonal_drift(self) -> None:
        world = self.world
        _, month, _, tod, season = world.current_calendar()
        if tod != "Night":
            return
        for region in world.regions.values():
            local = [actor for actor in world.actors_in_region(region.id) if actor.is_adventurer()]
            good = len([actor for actor in local if actor.is_good()])
            evil = len([actor for actor in local if actor.is_evil()])
            if good > evil:
                world.adjust_region_state(region.id, control_delta=1, order_delta=1)
            elif evil > good:
                world.adjust_region_state(region.id, control_delta=-1, order_delta=-1)
            else:
                if region.order < 55:
                    world.adjust_region_state(region.id, order_delta=1)
            if season == "Winter" and region.biome in ("Forest", "Highlands"):
                world.adjust_region_state(region.id, order_delta=-1)
            elif season == "Summer" and region.biome == "Plains":
                world.adjust_region_state(region.id, order_delta=1)

    def _emit_monthly_summary(self) -> None:
        world = self.world
        _, month, _, _, season = world.current_calendar()
        good_regions = len([r for r in world.regions.values() if r.control >= 20])
        evil_regions = len([r for r in world.regions.values() if r.control <= -20])
        contested = len(world.regions) - good_regions - evil_regions
        world.log(
            f"{MONTH_NAMES[month - 1]} closes in {season}: {good_regions} regions lean toward order, {evil_regions} toward oppression, {contested} remain contested.",
            importance=2,
            category="monthly",
        )

    def _emit_season_summary(self) -> None:
        world = self.world
        _, _, _, _, season = world.current_calendar()
        avg_order = sum(region.order for region in world.regions.values()) / len(world.regions)
        world.log(
            f"{season} ends with the continent's average order at {avg_order:.1f}.",
            importance=2,
            category="seasonal",
        )

    def _commoner_turn(self, actor: Actor) -> None:
        world = self.world
        threats = [other for other in world.actors_in_region(actor.region_id) if other.alive and other.is_adventurer() and other.is_evil()]
        monsters = [monster for monster in world.monsters_in_region(actor.region_id) if monster.kind in (MonsterKind.GOBLIN, MonsterKind.GIANT, MonsterKind.DRAGON, MonsterKind.ANCIENT_HORROR)]
        if threats or monsters:
            region = world.regions[actor.region_id]
            if region.neighbors:
                actor.region_id = self.rng.choice(region.neighbors)
                if self.rng.random() < 0.10:
                    world.log(f"Commoners flee {world.region_name(region.id)} after reports of oppression and monsters.", importance=1, category="flight")
                world.adjust_region_state(region.id, control_delta=-1, order_delta=-1)
            return
        if self.rng.random() < 0.04:
            region = world.regions[actor.region_id]
            if region.neighbors:
                actor.region_id = self.rng.choice(region.neighbors)

    def _adventurer_turn(self, actor: Actor) -> None:
        world = self.world
        if actor.needs_rest():
            self._rest_or_retreat(actor)
            return
        if actor.party_id is None:
            self._try_form_party(actor)
        if actor.is_good():
            if self._rally_defenders(actor):
                return
            if self._protect_commoners(actor):
                return
        elif actor.is_evil():
            if self._recruit_goblins(actor):
                return
            if self._oppress_commoners(actor):
                return
        if self._hunt_monsters(actor):
            return
        target = self._find_enemy_target(actor)
        if target is not None:
            if self._should_attack(actor, target):
                self._resolve_battle(actor, target)
                return
            if self._should_retreat(actor, target):
                self._retreat(actor, reason="an opposing force proves too strong")
                return
        move_chance = 0.45 + max(0, actor.luck - 10) * 0.005
        _, _, _, tod, season = world.current_calendar()
        if tod == "Night":
            move_chance -= 0.10
        if season == "Winter":
            move_chance -= 0.10
        if actor.role == Role.WARDEN:
            move_chance += 0.10
        if self.rng.random() < max(0.10, move_chance):
            self._quest_move(actor)

    def _monster_turn(self, monster: Monster) -> None:
        world = self.world
        if monster.kind == MonsterKind.GOBLIN:
            self._goblin_turn(monster)
            return
        if self.rng.random() < 0.22:
            region = world.regions[monster.region_id]
            if region.neighbors:
                monster.region_id = self.rng.choice(region.neighbors)
        locals_ = world.actors_in_region(monster.region_id)
        if monster.kind in (MonsterKind.DRAGON, MonsterKind.GIANT, MonsterKind.ANCIENT_HORROR) and locals_ and self.rng.random() < 0.20:
            victims = self.rng.sample(locals_, k=min(len(locals_), self.rng.randint(1, 3)))
            deaths = 0
            for victim in victims:
                if self.rng.random() < 0.30:
                    victim.alive = False
                    victim.hp = 0
                    deaths += 1
                else:
                    victim.recovering = max(victim.recovering, 2)
            world.adjust_region_state(monster.region_id, control_delta=-2, order_delta=-3)
            world.log(f"{monster.name} brings ruin to {world.region_name(monster.region_id)}, leaving {deaths} dead.", importance=2, category="monster_attack")

    def _goblin_turn(self, monster: Monster) -> None:
        world = self.world
        if monster.patron_actor_id is not None:
            patron = world.actors.get(monster.patron_actor_id)
            if patron and patron.alive:
                monster.region_id = patron.region_id
                if self.rng.random() < 0.30:
                    monster.horde_size += 1
                return
            monster.patron_actor_id = None
        evil_leaders = [actor for actor in world.actors_in_region(monster.region_id) if actor.is_adventurer() and actor.is_evil() and actor.reputation >= 8 and actor.charisma >= 12]
        if evil_leaders and self.rng.random() < 0.30:
            leader = max(evil_leaders, key=lambda a: (a.reputation, a.charisma))
            monster.patron_actor_id = leader.id
            world.log(f"{leader.short_name()} brings {monster.name} to heel in {world.region_name(monster.region_id)}.", importance=2, category="goblin_loyalty")
            return
        if self.rng.random() < 0.25:
            region = world.regions[monster.region_id]
            if region.neighbors:
                monster.region_id = self.rng.choice(region.neighbors)
        locals_ = world.actors_in_region(monster.region_id)
        if locals_ and self.rng.random() < 0.30:
            commoners = [actor for actor in locals_ if actor.role == Role.COMMONER]
            if commoners:
                losses = min(len(commoners), self.rng.randint(0, 2))
                if losses > 0:
                    victims = self.rng.sample(commoners, k=losses)
                    for victim in victims:
                        victim.alive = False
                        victim.hp = 0
                if self.rng.random() < 0.35:
                    monster.horde_size += 1
                world.adjust_region_state(monster.region_id, control_delta=-2, order_delta=-2)
                world.log(f"{monster.name} raids {world.region_name(monster.region_id)} with {monster.horde_size} goblins at its back.", importance=2, category="goblin_raid")

    def _try_form_party(self, actor: Actor) -> None:
        world = self.world
        if actor.party_id is not None:
            return
        regional_adventurers = [other for other in world.actors_in_region(actor.region_id) if other.id != actor.id and other.party_id is None and actor.can_join_party_with(other)]
        if not regional_adventurers:
            return
        candidates = [actor]
        self.rng.shuffle(regional_adventurers)
        for other in regional_adventurers:
            if len(candidates) >= 8:
                break
            if all(other.can_join_party_with(existing) for existing in candidates):
                candidates.append(other)
        if len(candidates) >= 2 and self.rng.random() < 0.55:
            world.create_party(candidates, goal="quest")

    def _find_enemy_target(self, actor: Actor) -> Optional[Actor]:
        world = self.world
        local = [other for other in world.actors_in_region(actor.region_id) if other.id != actor.id and other.alive]
        enemies = [other for other in local if actor.attitude_toward(other) == "oppose"]
        if not enemies:
            return None
        solo_or_party_enemies = []
        seen = set()
        for enemy in enemies:
            party = world.get_party(enemy)
            key = (party.id if party else -enemy.id)
            if key not in seen:
                seen.add(key)
                solo_or_party_enemies.append(enemy)
        return self.rng.choice(solo_or_party_enemies) if solo_or_party_enemies else None

    def _should_attack(self, actor: Actor, target: Actor) -> bool:
        world = self.world
        own_power = world.side_power(actor)
        enemy_power = world.side_power(target)
        own_mind = world.side_mind(actor)
        if enemy_power <= 0:
            return False
        if own_power >= enemy_power:
            return True
        desperate_ratio = own_power / enemy_power
        if own_mind < 14 and desperate_ratio >= 0.75:
            return True
        if own_mind < 10 and desperate_ratio >= 0.55:
            return True
        if own_mind < 8:
            return True
        return False

    def _should_retreat(self, actor: Actor, target: Actor) -> bool:
        world = self.world
        own_power = world.side_power(actor)
        enemy_power = world.side_power(target)
        own_mind = world.side_mind(actor)
        if enemy_power <= own_power:
            return False
        if own_mind < 8:
            return False
        return own_power / enemy_power < 0.85

    def _hunt_monsters(self, actor: Actor) -> bool:
        world = self.world
        monsters = [monster for monster in world.monsters_in_region(actor.region_id) if monster.alive]
        if not monsters:
            return False
        if actor.is_good() or actor.reputation >= 8:
            target = max(monsters, key=lambda m: m.effective_power())
            if target.kind == MonsterKind.DRAGON:
                party = world.get_party(actor)
                party_size = len(party.member_ids) if party else 1
                if actor.reputation < 12 and party_size < 3 and actor.mind_score() >= 10:
                    return False
            return self._resolve_monster_battle(actor, target)
        return False

    def _recruit_goblins(self, actor: Actor) -> bool:
        world = self.world
        goblins = [monster for monster in world.monsters_in_region(actor.region_id) if monster.kind == MonsterKind.GOBLIN and monster.alive and monster.patron_actor_id is None]
        if not goblins:
            return False
        if actor.reputation < 8 or actor.charisma < 12:
            return False
        if self.rng.random() < 0.35:
            goblin = max(goblins, key=lambda g: g.horde_size)
            goblin.patron_actor_id = actor.id
            goblin.reputation += 2
            actor.reputation += 1
            actor.regions_oppressed += 1
            self._grant_title(actor, f"Boss of {world.region_name(actor.region_id)}")
            world.log(f"{actor.short_name()} wins the loyalty of {goblin.name} in {world.region_name(actor.region_id)}.", importance=2, category="goblin_loyalty")
            return True
        return False

    def _rally_defenders(self, actor: Actor) -> bool:
        world = self.world
        if actor.reputation < 8 or actor.charisma < 12:
            return False
        goblin_threats = [monster for monster in world.monsters_in_region(actor.region_id) if monster.kind == MonsterKind.GOBLIN and monster.alive and monster.horde_size >= 8]
        if not goblin_threats:
            return False
        commoners = [person for person in world.actors_in_region(actor.region_id) if person.role == Role.COMMONER and person.alive]
        allied_heroes = [person for person in world.actors_in_region(actor.region_id) if person.is_adventurer() and person.alive and person.id != actor.id and not person.is_evil()]
        if len(commoners) + len(allied_heroes) < 6:
            return False
        if self.rng.random() < 0.40:
            threat = max(goblin_threats, key=lambda g: g.horde_size)
            army_power = actor.power_rating() + len(commoners) // 4 + sum(hero.power_rating() for hero in allied_heroes[:3])
            if army_power >= threat.effective_power() or actor.mind_score() < 10:
                threat.horde_size = max(1, threat.horde_size - self.rng.randint(2, 5))
                actor.reputation += 2
                actor.regions_defended += 1
                world.adjust_region_state(actor.region_id, control_delta=2, order_delta=2)
                self._grant_title(actor, f"Defender of {world.region_name(actor.region_id)}")
                world.log(f"{actor.short_name()} rallies the people of {world.region_name(actor.region_id)} against a goblin horde.", importance=3, category="defense")
                if threat.horde_size <= 2:
                    threat.alive = False
                    actor.kills += 1
                    actor.monster_kills += 1
                    world.log(f"The goblin threat in {world.region_name(actor.region_id)} is broken.", importance=3, category="defense")
                return True
        return False

    def _resolve_monster_battle(self, actor: Actor, monster: Monster) -> bool:
        world = self.world
        side_power = world.side_power(actor)
        side_power += world.side_charisma(actor) // 4
        side_power += max(0, actor.luck - 10) // 2
        if actor.role == Role.WIZARD:
            side_power += 3
        monster_power = monster.effective_power()
        own_mind = world.side_mind(actor)
        if monster.kind == MonsterKind.DRAGON and side_power < monster_power and own_mind >= 9 and self.rng.random() < 0.85:
            self._retreat(actor, reason=f"{monster.name} is too dangerous")
            return True
        if monster_power > side_power and own_mind >= 10 and self.rng.random() < 0.65:
            self._retreat(actor, reason=f"{monster.name} is too dangerous")
            return True

        battle_roll = side_power + self.rng.randint(1, 10) + max(0, actor.luck - 10) // 2
        monster_roll = monster_power + self.rng.randint(1, 10)
        if monster.kind == MonsterKind.DRAGON:
            monster_roll += 8
        if battle_roll >= monster_roll:
            monster.alive = False
            for member in world.side_members(actor):
                member.reputation += 2
                member.monster_kills += 1
                if monster.kind == MonsterKind.DRAGON:
                    member.dragon_kills += 1
                elif monster.kind == MonsterKind.ANCIENT_HORROR:
                    member.horror_kills += 1
                elif monster.kind == MonsterKind.GIANT:
                    member.giant_kills += 1
                if monster.kind != MonsterKind.GOBLIN:
                    member.kills += 1
            slayer = actor
            if monster.kind == MonsterKind.DRAGON:
                self._grant_title(slayer, "Dragonslayer")
                world.log(f"{actor.short_name()} slays {monster.name} in {world.region_name(actor.region_id)}.", importance=3, category="legendary_monster_kill")
            elif monster.kind == MonsterKind.GIANT:
                self._grant_title(slayer, "Giantbreaker")
                world.log(f"{actor.short_name()} fells {monster.name} in {world.region_name(actor.region_id)}.", importance=2, category="monster_kill")
            elif monster.kind == MonsterKind.ANCIENT_HORROR:
                self._grant_title(slayer, "Bane of the Deep")
                world.log(f"{actor.short_name()} destroys the {monster.name} in {world.region_name(actor.region_id)}.", importance=3, category="legendary_monster_kill")
            else:
                world.log(f"{actor.short_name()} defeats {monster.name} in {world.region_name(actor.region_id)}.", importance=2, category="monster_kill")
            world.adjust_region_state(actor.region_id, control_delta=3, order_delta=3)
            return True

        casualties = self._apply_losses(world.side_members(actor), severity=0.12 + monster_power / 100)
        self._apply_rout(world.side_members(actor))
        world.adjust_region_state(actor.region_id, control_delta=-1, order_delta=-2)
        world.log(f"{monster.name} repels {actor.short_name()} in {world.region_name(actor.region_id)}, leaving {casualties} dead.", importance=2, category="monster_attack")
        return True

    def _grant_title(self, actor: Actor, title: str) -> None:
        if actor.title is None:
            actor.title = title

    def _resolve_battle(self, attacker: Actor, defender: Actor) -> None:
        world = self.world
        attackers = world.side_members(attacker)
        defenders = world.side_members(defender)
        if not attackers or not defenders:
            return

        attack_power = sum(member.power_rating() for member in attackers)
        defend_power = sum(member.power_rating() for member in defenders)

        attack_roll = attack_power + self.rng.randint(1, 8) + max(0, attacker.luck - 10) // 3
        defend_roll = defend_power + self.rng.randint(1, 8) + max(0, defender.luck - 10) // 3
        if attacker.role == Role.WIZARD:
            attack_roll += 2
        if defender.role == Role.WIZARD:
            defend_roll += 2

        atk_names = self._format_side_names(attackers)
        def_names = self._format_side_names(defenders)
        region_name = world.region_name(attacker.region_id)

        if attack_roll >= defend_roll:
            casualties = self._apply_losses(defenders, severity=0.22)
            routed = self._apply_rout(defenders)
            self._apply_wounds(attackers, severity=0.10)
            for winner in attackers:
                winner.kills += casualties
                winner.reputation += 1
            world.log(f"In {region_name}, {atk_names} defeated {def_names}, leaving {casualties} dead and {routed} routed.", importance=3, category="battle")
            control_shift = 2 if any(a.is_good() for a in attackers) else -2 if any(a.is_evil() for a in attackers) else 0
            world.adjust_region_state(attacker.region_id, control_delta=control_shift, order_delta=-1)
        else:
            casualties = self._apply_losses(attackers, severity=0.22)
            routed = self._apply_rout(attackers)
            self._apply_wounds(defenders, severity=0.10)
            for winner in defenders:
                winner.kills += casualties
                winner.reputation += 1
            world.log(f"In {region_name}, {atk_names} attacked {def_names} and were repelled, losing {casualties} dead and {routed} routed.", importance=3, category="battle")
            control_shift = 2 if any(d.is_good() for d in defenders) else -2 if any(d.is_evil() for d in defenders) else 0
            world.adjust_region_state(attacker.region_id, control_delta=control_shift, order_delta=-1)

        world.cleanup_parties()

    def _apply_losses(self, side: List[Actor], severity: float) -> int:
        deaths = 0
        for actor in side:
            if not actor.alive:
                continue
            lethal_chance = severity
            if actor.role == Role.FIGHTER:
                lethal_chance -= 0.05
            elif actor.role == Role.WIZARD:
                lethal_chance += 0.02
            elif actor.role == Role.COMMONER:
                lethal_chance += 0.08
            lethal_chance -= max(0, actor.luck - 10) * 0.005
            lethal_chance = max(0.03, min(0.50, lethal_chance))
            if self.rng.random() < lethal_chance:
                actor.alive = False
                actor.hp = 0
                actor.recovering = 0
                deaths += 1
                continue
            actor.hp = max(1, actor.hp - self.rng.randint(1, max(2, actor.max_hp // 3)))
            actor.recovering = max(actor.recovering, self.rng.randint(2, 5))
        return deaths

    def _apply_rout(self, side: List[Actor]) -> int:
        routed = 0
        for actor in side:
            if not actor.alive:
                continue
            actor.recovering = max(actor.recovering, self.rng.randint(2, 5))
            if actor.party_id is not None and self.rng.random() < 0.45:
                self.world.remove_from_party(actor)
            if self.rng.random() < 0.70:
                region = self.world.regions[actor.region_id]
                if region.neighbors:
                    actor.region_id = self.rng.choice(region.neighbors)
                    routed += 1
        return routed

    def _apply_wounds(self, side: List[Actor], severity: float) -> None:
        for actor in side:
            if not actor.alive:
                continue
            if self.rng.random() < severity:
                actor.hp = max(1, actor.hp - self.rng.randint(1, max(2, actor.max_hp // 4)))
                actor.recovering = max(actor.recovering, self.rng.randint(1, 3))

    def _rest_or_retreat(self, actor: Actor) -> None:
        if actor.recovering > 0 and self.rng.random() < 0.40:
            self._retreat(actor, reason="they need time to recover")

    def _retreat(self, actor: Actor, reason: str) -> None:
        world = self.world
        party = world.get_party(actor)
        region = world.regions[actor.region_id]
        if not region.neighbors:
            return
        target_region_id = self.rng.choice(region.neighbors)
        if party is not None:
            for member_id in party.member_ids:
                member = world.actors[member_id]
                if member.alive:
                    member.region_id = target_region_id
                    member.recovering = max(member.recovering, 1)
            if self.rng.random() < 0.30:
                world.log(f"{self._format_side_names([world.actors[mid] for mid in party.member_ids if world.actors[mid].alive])} withdraw to {world.region_name(target_region_id)} because {reason}.", importance=2, category="retreat")
        else:
            actor.region_id = target_region_id
            actor.recovering = max(actor.recovering, 1)
            if self.rng.random() < 0.15:
                world.log(f"{actor.short_name()} retreats to {world.region_name(target_region_id)} because {reason}.", importance=1, category="retreat")

    def _protect_commoners(self, actor: Actor) -> bool:
        world = self.world
        local = world.actors_in_region(actor.region_id)
        villains = [other for other in local if other.alive and other.is_adventurer() and other.is_evil()]
        commoners = [other for other in local if other.alive and other.role == Role.COMMONER]
        if not villains or not commoners:
            return False
        target = self.rng.choice(villains)
        if self._should_attack(actor, target):
            world.log(f"{actor.short_name()} moves to defend the common folk of {world.region_name(actor.region_id)}.", importance=2, category="defense")
            world.adjust_region_state(actor.region_id, control_delta=2, order_delta=1)
            actor.protects_region = actor.region_id
            actor.regions_defended += 1
            self._grant_title(actor, f"Defender of {world.region_name(actor.region_id)}")
            self._resolve_battle(actor, target)
            return True
        if self._should_retreat(actor, target):
            self._retreat(actor, reason="the local villains are too strong to face openly")
            return True
        return False

    def _oppress_commoners(self, actor: Actor) -> bool:
        world = self.world
        local = world.actors_in_region(actor.region_id)
        commoners = [other for other in local if other.alive and other.role == Role.COMMONER]
        protectors = [other for other in local if other.alive and other.is_adventurer() and other.is_good()]
        if protectors:
            target = self.rng.choice(protectors)
            if self._should_attack(actor, target):
                world.log(f"{actor.short_name()} tries to break resistance in {world.region_name(actor.region_id)}.", importance=2, category="oppression")
                world.adjust_region_state(actor.region_id, control_delta=-2, order_delta=-1)
                actor.regions_oppressed += 1
                self._resolve_battle(actor, target)
                return True
            if self._should_retreat(actor, target):
                self._retreat(actor, reason="local defenders are stronger than expected")
                return True
            return False
        if commoners and self.rng.random() < 0.35:
            victims = self.rng.sample(commoners, k=min(len(commoners), self.rng.randint(1, 3)))
            deaths = 0
            for victim in victims:
                if self.rng.random() < 0.18:
                    victim.alive = False
                    victim.hp = 0
                    deaths += 1
                else:
                    victim.recovering = max(victim.recovering, self.rng.randint(1, 3))
            actor.reputation += 1
            actor.regions_oppressed += 1
            world.log(f"{actor.short_name()} terrorizes commoners in {world.region_name(actor.region_id)}, leaving {deaths} dead.", importance=2, category="oppression")
            world.adjust_region_state(actor.region_id, control_delta=-3, order_delta=-2)
            return True
        return False

    def _quest_move(self, actor: Actor) -> None:
        world = self.world
        party = world.get_party(actor)
        if party is not None and party.leader_id is not None and party.leader_id != actor.id:
            leader = world.actors[party.leader_id]
            actor.region_id = leader.region_id
            return
        region = world.regions[actor.region_id]
        if not region.neighbors:
            return
        target_region_id = self.rng.choice(region.neighbors)
        actor.region_id = target_region_id
        if party is not None:
            for member_id in party.member_ids:
                if member_id != actor.id and world.actors[member_id].alive:
                    world.actors[member_id].region_id = target_region_id
            if self.rng.random() < 0.25:
                world.log(f"{self._format_side_names([world.actors[mid] for mid in party.member_ids if world.actors[mid].alive])} set out for {world.region_name(target_region_id)}.", importance=1, category="travel")
        else:
            if self.rng.random() < 0.15:
                world.log(f"{actor.short_name()} wanders into {world.region_name(target_region_id)}.", importance=1, category="travel")

    def _format_side_names(self, side: List[Actor]) -> str:
        if not side:
            return "nobody"
        party = self.world.get_party(side[0]) if side[0].alive else None
        if party and party.name and all(member.party_id == party.id for member in side if member.alive):
            return party.name
        living = [actor.short_name() for actor in side if actor.alive]
        if not living:
            return "nobody"
        if len(living) == 1:
            return living[0]
        if len(living) == 2:
            return f"{living[0]} and {living[1]}"
        return ", ".join(living[:-1]) + f", and {living[-1]}"

    def _print_new_events(self) -> None:
        world = self.world
        new_events = world.events[self._last_printed_event_index:]
        for event in new_events:
            if event.importance >= self.verbose_min_importance:
                print(f"[{event.timestamp}] {event.text}")
        self._last_printed_event_index = len(world.events)

    def _pick_top_hero_and_villain(self) -> Tuple[Optional[Actor], Optional[Actor]]:
        living = self.world.living_actors()
        heroes = [a for a in living if a.is_adventurer() and not a.is_evil()]
        villains = [a for a in living if a.is_adventurer() and a.is_evil()]
        hero = max(heroes, key=lambda a: (a.reputation, a.dragon_kills, a.horror_kills, a.monster_kills, a.kills, a.power_rating()), default=None)
        villain = max(villains, key=lambda a: (a.reputation, a.regions_oppressed, a.kills, a.monster_kills, a.power_rating()), default=None)
        return hero, villain

    def _deity_influence_summary(self) -> List[Tuple[Deity, int, float]]:
        surviving = self.world.living_actors()
        total = len(surviving)
        results: List[Tuple[Deity, int, float]] = []
        for deity in Deity:
            count = len([actor for actor in surviving if actor.deity == deity])
            pct = (count / total * 100.0) if total else 0.0
            results.append((deity, count, pct))
        return results

    def _top_region(self) -> Region:
        return max(self.world.regions.values(), key=lambda r: (r.order, r.control, -r.danger))

    def _top_deity(self) -> Tuple[Deity, int, float]:
        return max(self._deity_influence_summary(), key=lambda item: item[2])

    def _hero_tale(self, hero: Actor) -> str:
        pieces = []
        if hero.title:
            pieces.append(f"Known as {hero.title}")
        if hero.dragon_kills:
            pieces.append(f"slew {hero.dragon_kills} dragon{'s' if hero.dragon_kills != 1 else ''}")
        if hero.horror_kills:
            pieces.append(f"broke {hero.horror_kills} ancient horror{'s' if hero.horror_kills != 1 else ''}")
        if hero.regions_defended:
            pieces.append(f"defended {hero.regions_defended} threatened frontier{'s' if hero.regions_defended != 1 else ''}")
        if not pieces:
            pieces.append(f"earned renown through {hero.kills} victories")
        return f"{hero.full_name()} {'; '.join(pieces)} from {self.world.region_name(hero.region_id)}."

    def _villain_tale(self, villain: Actor) -> str:
        pieces = []
        if villain.title:
            pieces.append(f"Bearing the name {villain.title}")
        if villain.regions_oppressed:
            pieces.append(f"oppressed {villain.regions_oppressed} region{'s' if villain.regions_oppressed != 1 else ''}")
        if villain.kills:
            pieces.append(f"left {villain.kills} bodies in their wake")
        if not pieces:
            pieces.append(f"spread fear from {self.world.region_name(villain.region_id)}")
        return f"{villain.full_name()} {'; '.join(pieces)}."

    def _chronicle_title(self, hero: Optional[Actor], top_region: Region, top_deity: Deity) -> str:
        if hero is not None:
            return f"The Chronicle of {hero.short_name()}, {top_region.name}, and {top_deity.value}"
        return f"The Chronicle of {top_region.name} under {top_deity.value}"

    def print_summary(self) -> None:
        summary.print_summary(self)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fantasy antfarm simulation.",
        epilog=(
            "Operators: --verbose/-v for live events, --delay for pacing live output, "
            "--seed for reproducible alphanumeric worlds, --years for yearly duration override, "
            "--verbose-importance to filter live event noise."
        ),
    )
    parser.add_argument("--seed", type=str, default=DEFAULT_SEED, help="Alphanumeric seed for world generation. Omit for a fresh random world.")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS, help="How many years to simulate. Whole years only. Default is 1.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print events as the simulation runs instead of waiting for the final summary.")
    parser.add_argument("--delay", type=float, default=0.0, help="Optional delay in seconds between ticks when verbose mode is enabled.")
    parser.add_argument("--verbose-importance", type=int, default=VERBOSE_EVENT_IMPORTANCE, help="Only print live events at or above this importance level in verbose mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    years = max(1, args.years)
    ticks = years * TICKS_PER_YEAR
    simulator = Simulator(
        seed=args.seed,
        verbose=args.verbose,
        verbose_delay=args.delay,
        verbose_min_importance=args.verbose_importance,
    )
    simulator.run(ticks)
    simulator.print_summary()


if __name__ == "__main__":
    main()
