import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

TIME_OF_DAY = ["Morning", "Midday", "Night"]
MONTH_NAMES = [
    "Dawnsreach", "Rainmoot", "Bloomtide", "Suncrest", "Goldfire", "Highsun",
    "Harvestwane", "Emberfall", "Duskmarch", "Frostturn", "Deepcold", "Yearsend",
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

    def size_tier(self) -> str:
        n = len(self.member_ids)
        if n >= 20:
            return "company"
        if n >= 15:
            return "very_large"
        if n >= 9:
            return "large"
        if n >= 5:
            return "medium"
        return "small"

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

    def full_name(self) -> str:
        if self.title:
            return f"{self.name} {self.surname}, {self.title}"
        return f"{self.name} {self.surname}"

    def short_name(self) -> str:
        return f"{self.name} {self.surname}"

    def birth_text(self) -> str:
        return f"{MONTH_NAMES[self.birth_month - 1]} {self.birth_day}"

    def notable_deeds_summary(self) -> str:
        deeds = []
        if self.dragon_kills:
            deeds.append(f"slaying {self.dragon_kills} dragon{'s' if self.dragon_kills != 1 else ''}")
        if self.horror_kills:
            deeds.append(f"destroying {self.horror_kills} ancient horror{'s' if self.horror_kills != 1 else ''}")
        if self.giant_kills:
            deeds.append(f"felling {self.giant_kills} giant{'s' if self.giant_kills != 1 else ''}")
        if self.regions_defended:
            deeds.append(f"defending {self.regions_defended} region{'s' if self.regions_defended != 1 else ''}")
        if self.regions_oppressed:
            deeds.append(f"oppressing {self.regions_oppressed} region{'s' if self.regions_oppressed != 1 else ''}")
        if self.kills and not deeds:
            deeds.append(f"claiming {self.kills} kills")
        return '; '.join(deeds) if deeds else 'living long enough to be remembered'

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
    souls_by_deity: Dict[Deity, int] = field(default_factory=lambda: {deity: 0 for deity in Deity})
    spawned_horror_titles: set = field(default_factory=set)

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


