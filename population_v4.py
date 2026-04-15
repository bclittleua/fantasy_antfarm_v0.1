from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    from fantfarm_v4 import Actor, Alignment, Deity, MonsterKind, Region, Role


class PopulationMixin:
    """
    Population and civilian-lifecycle logic.
    """
    # =========================
    # --- v3 population core ---
    # =========================

    BIRTH_COOLDOWN_TICKS = 720
    MAX_SOFT_CHILDREN_PER_COUPLE = 13
    
    def _random_person_name(self) -> Tuple[str, str]:
        return self.rng.choice(FIRST_NAMES), self.rng.choice(SURNAMES)

    def _weighted_random_deity(self, alignment: "Alignment") -> "Deity":
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

    def _roll_stats(self, role: "Role") -> Tuple[int, int, int, int, int, int, int]:
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

    def _base_hp(self, role: "Role", constitution: int) -> int:
        con_mod = max(-2, (constitution - 10) // 2)

        if role == Role.COMMONER:
            return max(3, 6 + con_mod)
        if role == Role.FIGHTER:
            return max(6, 12 + con_mod)
        if role == Role.WIZARD:
            return max(5, 9 + con_mod)
        return max(5, 10 + con_mod)

    def _generate_population(self, count: int, regions: Dict[int, "Region"]) -> Dict[int, "Actor"]:
        actors: Dict[int, Actor] = {}
        role_choices = [role for role, _ in ROLE_WEIGHTS]
        role_weights = [weight for _, weight in ROLE_WEIGHTS]

        current_year = 1

        for actor_id in range(1, count + 1):
            role = self.rng.choices(role_choices, weights=role_weights, k=1)[0]
            alignment = self.rng.choice(list(Alignment))
            deity = self._weighted_random_deity(alignment)
            stats = self._roll_stats(role)
            hp = self._base_hp(role, stats[2])
            region_id = self.rng.choice(list(regions.keys()))
            first, surname = self._random_person_name()
            traits = self.rng.sample(TRAITS, k=2)

            age = self._initial_age_for_role(role)
            birth_year = current_year - age

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
                birth_year=birth_year,
                birth_month=self.rng.randint(1, 12),
                birth_day=self.rng.randint(1, 30),
                spouse_id=None,
            )
        self._seed_initial_households(actors)
        return actors

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

    def _commoner_turn(self, actor: "Actor") -> None:
        world = self.world

        threats = [
            other
            for other in world.actors_in_region(actor.region_id)
            if other.alive and other.is_adventurer() and other.is_evil()
        ]
        monsters = [
            monster
            for monster in world.monsters_in_region(actor.region_id)
            if monster.kind in (
                MonsterKind.GOBLIN,
                MonsterKind.GIANT,
                MonsterKind.DRAGON,
                MonsterKind.ANCIENT_HORROR,
            )
        ]

        if threats or monsters:
            region = world.regions[actor.region_id]

            if region.neighbors:
                actor.region_id = self.rng.choice(region.neighbors)

            if self.rng.random() < 0.10:
                world.log(
                    f"Commoners flee {world.region_name(region.id)} after reports of oppression and monsters.",
                    importance=1,
                    category="flight",
                )

            world.adjust_region_state(region.id, control_delta=-1, order_delta=-1)
            return

        if self.rng.random() < 0.04:
            region = world.regions[actor.region_id]
            if region.neighbors:
                actor.region_id = self.rng.choice(region.neighbors)

    # =========================
    # --- v4 longevity system ---
    # =========================

    def _initial_age_for_role(self, role: "Role") -> int:
        if role == Role.COMMONER:
            roll = self.rng.random()
            if roll < 0.18:
                return self.rng.randint(0, 15)
            if roll < 0.80:
                return self.rng.randint(16, 45)
            if roll < 0.97:
                return self.rng.randint(46, 70)
            return self.rng.randint(71, 90)

        roll = self.rng.random()
        if roll < 0.15:
            return self.rng.randint(16, 24)
        if roll < 0.75:
            return self.rng.randint(25, 50)
        if roll < 0.96:
            return self.rng.randint(51, 75)
        return self.rng.randint(76, 95)

    def _calculate_age(self, actor: "Actor") -> int:
        year, _, _, _, _ = self.world.current_calendar()
        return max(0, year - actor.birth_year)

    def _longevity_score(self, actor: "Actor") -> float:
        return (
            actor.constitution * 1.5 +
            actor.wisdom * 1.3 +
            actor.luck * 1.4 +
            actor.dexterity * 1.1 +
            actor.strength * 0.9 +
            actor.intelligence * 1.2 +
            actor.charisma * 0.8
        ) / 7.0

    def _environment_modifier(self, region: "Region") -> float:
        mod = 1.0
        mod *= (1.0 - (region.order - 50) * 0.002)
        mod *= (1.0 + abs(min(region.control, 0)) * 0.002)
        mod *= (1.0 + region.danger * 0.02)
        return max(0.5, min(1.8, mod))

    def _age_curve(self, age: int) -> float:
        if age < 45:
            return 0.0002
        if age < 55:
            return 0.002
        if age < 65:
            return 0.009
        if age < 75:
            return 0.028
        if age < 85:
            return 0.07
        if age < 95:
            return 0.15
        if age < 105:
            return 0.28
        if age < 115:
            return 0.48
        return 0.72 + min(0.22, (age - 115) * 0.025)

    def _natural_death_check(self, actor: "Actor") -> None:
        age = self._calculate_age(actor)
        region = self.world.regions[actor.region_id]

        base = self._age_curve(age)
        stats = self._longevity_score(actor)
        env = self._environment_modifier(region)

        stat_mod = max(0.55, 1.45 - (stats - 10) * 0.03)
        death_chance = max(0.0, min(0.98, base * stat_mod * env))

        if self.rng.random() < death_chance:
            self._mark_actor_dead(actor, "old age", importance=2)

    def _coming_of_age_check(self, actor: "Actor") -> None:
        if actor.role != Role.COMMONER:
            return

        age = self._calculate_age(actor)
        if age != 16:
            return

        region = self.world.regions[actor.region_id]

        chance = 0.04
        if actor.strength >= 13 or actor.constitution >= 13:
            chance += 0.01
        if actor.dexterity >= 13 or actor.wisdom >= 13:
            chance += 0.01
        if actor.intelligence >= 14 or actor.luck >= 14:
            chance += 0.01

        if region.order >= 70:
            chance += 0.005
        if region.control >= 50:
            chance += 0.005
        if region.control <= -20:
            chance -= 0.01

        chance = max(0.01, min(0.10, chance))

        if self.rng.random() >= chance:
            return

        new_role = self._roll_new_adventurer_role(actor)
        self._promote_commoner_to_role(actor, new_role)

    def _roll_new_adventurer_role(self, actor: "Actor") -> "Role":
        wizard_weight = WIZARD_PROMOTION_CHANCE
        fighter_weight = 0.60
        warden_weight = 0.38 - wizard_weight

        if actor.intelligence >= 14 or actor.wisdom >= 14:
            wizard_weight += 0.01
        if actor.luck >= 15:
            wizard_weight += 0.01

        if actor.dexterity >= actor.strength:
            warden_weight += 0.05
        else:
            fighter_weight += 0.05

        total = fighter_weight + warden_weight + wizard_weight
        roll = self.rng.random() * total

        if roll < fighter_weight:
            return Role.FIGHTER
        if roll < fighter_weight + warden_weight:
            return Role.WARDEN
        return Role.WIZARD

    def _promote_commoner_to_role(self, actor: "Actor", new_role: "Role") -> None:
        actor.role = new_role

        stats = self._roll_stats(new_role)
        actor.strength = stats[0]
        actor.dexterity = stats[1]
        actor.constitution = stats[2]
        actor.intelligence = stats[3]
        actor.wisdom = stats[4]
        actor.charisma = stats[5]
        actor.luck = stats[6]

        actor.max_hp = self._base_hp(new_role, actor.constitution)
        actor.hp = max(actor.hp, actor.max_hp)

        self.world.generated_by_role[new_role] += 1

        self.world.log(
            f"{actor.short_name()} comes of age in {self.world.region_name(actor.region_id)} and takes up the life of a {new_role.value.lower()}.",
            importance=2,
            category="coming_of_age",
        )


    # =========================
    # --- v4 population tick ---
    # =========================

    def _population_tick(self) -> None:
        world = self.world
        _, month, day, _, _ = world.current_calendar()

        for actor in list(world.living_actors()):
            if actor.birth_month == month and actor.birth_day == day:
                self._coming_of_age_check(actor)
                self._natural_death_check(actor)

        for actor in list(world.living_actors()):
            age = self._calculate_age(actor)
            if age < 5:
                region = world.regions[actor.region_id]

                infant_risk = 0.0015

                if region.order <= 35:
                    infant_risk += 0.003
                elif region.order >= 85:
                    infant_risk -= 0.001
                elif region.order >= 70:
                    infant_risk -= 0.0007

                if region.control <= -20:
                    infant_risk += 0.002
                elif region.control >= 80:
                    infant_risk -= 0.001
                elif region.control >= 50:
                    infant_risk -= 0.0007

                infant_risk += region.danger * 0.0005

                infant_risk -= max(0, actor.constitution - 10) * 0.0002
                infant_risk -= max(0, actor.luck - 10) * 0.0002

                infant_risk = max(0.0, min(0.015, infant_risk))

                if self.rng.random() < infant_risk:
                    self._mark_actor_dead(actor, "childhood illness", importance=1)

        self._cleanup_spouses()
        self._handle_pairing()
        self._handle_births()

    def _cleanup_spouses(self) -> None:
        for actor in self.world.living_actors():
            if actor.spouse_id is None:
                continue
            spouse = self.world.actors.get(actor.spouse_id)
            if spouse is None or not spouse.alive:
                actor.spouse_id = None

    def _seed_initial_households(self, actors: Dict[int, "Actor"]) -> None:
        by_region: Dict[int, List[Actor]] = {}
        for actor in actors.values():
            if actor.role == Role.COMMONER and actor.spouse_id is None and self._calculate_age_static(actor, current_year=1) >= 18:
                by_region.setdefault(actor.region_id, []).append(actor)

        for region_id, people in by_region.items():
            self.rng.shuffle(people)
            pair_count = int(len(people) * 0.05)
            i = 0
            made = 0
            while i + 1 < len(people) and made < pair_count:
                a = people[i]
                b = people[i + 1]
                if a.spouse_id is None and b.spouse_id is None:
                    a.spouse_id = b.id
                    b.spouse_id = a.id
                    made += 1
                i += 2

    def _calculate_age_static(self, actor: "Actor", current_year: int) -> int:
        return max(0, current_year - actor.birth_year)

    def _handle_pairing(self) -> None:
        world = self.world

        candidates = [
            a for a in world.living_actors()
            if a.role == Role.COMMONER
            and a.spouse_id is None
            and self._calculate_age(a) >= 18
        ]

        self.rng.shuffle(candidates)

        for actor in candidates:
            if actor.spouse_id is not None:
                continue

            locals_ = [
                other for other in world.actors_in_region(actor.region_id)
                if other.id != actor.id
                and other.role == Role.COMMONER
                and other.spouse_id is None
                and self._calculate_age(other) >= 18
            ]

            if not locals_:
                continue
                
            region = world.regions[actor.region_id]
            chance = 0.002
            if region.order >= 55:
                chance += 0.0015
            if region.control >= 20:
                chance += 0.001
            if region.control <= -20:
                chance -= 0.0015
            if region.order <= 35:
                chance -= 0.001

            if self.rng.random() < max(0.001, chance):
                partner = self.rng.choice(locals_)
                actor.spouse_id = partner.id
                partner.spouse_id = actor.id

    def _living_children_of_pair(self, parent_a: "Actor", parent_b: "Actor") -> int:
        count = 0
        for actor in self.world.living_actors():
            if actor.role != Role.COMMONER:
                continue
            mother_id = getattr(actor, "mother_id", None)
            father_id = getattr(actor, "father_id", None)
            pair = {parent_a.id, parent_b.id}
            if {mother_id, father_id} == pair:
                count += 1
        return count

    def _pair_last_birth_tick(self, parent_a: "Actor", parent_b: "Actor") -> int:
        a_tick = getattr(parent_a, "last_birth_tick", -999999)
        b_tick = getattr(parent_b, "last_birth_tick", -999999)
        return max(a_tick, b_tick)
    
    def _handle_births(self) -> None:
        world = self.world

        for actor in list(world.living_actors()):
            if actor.spouse_id is None:
                continue
            if actor.role != Role.COMMONER:
                continue

            spouse = world.actors.get(actor.spouse_id)
            if spouse is None or not spouse.alive or spouse.role != Role.COMMONER:
                continue

            age_a = self._calculate_age(actor)
            age_b = self._calculate_age(spouse)
            if age_a < 18 or age_b < 18 or age_a > 45 or age_b > 55:
                continue

            if actor.id > spouse.id:
                continue

            children = self._living_children_of_pair(actor, spouse)
            last_birth_tick = self._pair_last_birth_tick(actor, spouse)

            if self.world.tick - last_birth_tick < self.BIRTH_COOLDOWN_TICKS:
                continue

            chance = self._birth_chance_for_pair(actor, spouse)

            if children >= self.MAX_SOFT_CHILDREN_PER_COUPLE:
                chance *= 0.35
            if children >= self.MAX_SOFT_CHILDREN_PER_COUPLE + 1:
                chance *= 0.15
            if children >= self.MAX_SOFT_CHILDREN_PER_COUPLE + 2:
                chance = 0.0

            if self.rng.random() < chance:
                self._create_child(actor, spouse)
                actor.last_birth_tick = self.world.tick
                spouse.last_birth_tick = self.world.tick

    def _birth_chance_for_pair(self, parent_a: "Actor", parent_b: "Actor") -> float:
        region = self.world.regions[parent_a.region_id]

        chance = 0.003

        if region.order >= 60:
            chance += 0.002
        if region.order <= 35:
            chance -= 0.0015

        if region.control >= 20:
            chance += 0.001
        if region.control <= -20:
            chance -= 0.0015

        chance -= region.danger * 0.0005

        avg_luck = (parent_a.luck + parent_b.luck) / 2.0
        chance += (avg_luck - 10) * 0.0003

        return max(0.0002, min(0.01, chance))

    def _create_child(self, parent_a: "Actor", parent_b: "Actor") -> None:
        world = self.world
        new_id = max(world.actors.keys()) + 1

        alignment = self.rng.choice([parent_a.alignment, parent_b.alignment, self.rng.choice(list(Alignment))])
        deity = self._weighted_random_deity(alignment)

        stats = self._inherit_stats(parent_a, parent_b)
        hp = self._base_hp(Role.COMMONER, stats[2])

        child = Actor(
            id=new_id,
            name=self.rng.choice(FIRST_NAMES),
            surname=parent_a.surname,
            role=Role.COMMONER,
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
            region_id=parent_a.region_id,
            traits=self.rng.sample(TRAITS, 2),
            birth_year=self.world.current_calendar()[0],
            birth_month=self.rng.randint(1, 12),
            birth_day=self.rng.randint(1, 30),
            spouse_id=None,
            mother_id=parent_a.id,
            father_id=parent_b.id,
            last_birth_tick=-999999,
        )

        world.actors[new_id] = child

    def _inherit_stats(self, a: "Actor", b: "Actor") -> Tuple[int, ...]:
        stats = []
        for stat in [
            "strength", "dexterity", "constitution",
            "intelligence", "wisdom", "charisma", "luck"
        ]:
            avg = (getattr(a, stat) + getattr(b, stat)) / 2
            rolled = int(round(avg + self.rng.randint(-2, 2)))
            stats.append(max(3, min(18, rolled)))
        return tuple(stats)


# injected globals
FIRST_NAMES: List[str]
SURNAMES: List[str]
TRAITS: List[str]
ROLE_WEIGHTS: List[Tuple["Role", int]]
WIZARD_PROMOTION_CHANCE: float

Alignment: type
Role: type
Deity: type
MonsterKind: type
Actor: type
