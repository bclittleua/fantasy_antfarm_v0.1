from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from fantfarm_v6 import Actor, Alignment, Deity, Role


class LegacyMixin:
    """
    Adventurer lineage / dynasty layer.

    This module is intentionally conservative:
    - adventurers can pair
    - adventurers can have children
    - children are born as COMMONER by default
    - parentage is tracked for future dynasty / succession systems

    It is designed to be mixed in alongside PopulationMixin.
    It expects the simulator to already provide:
        - self.world
        - self.rng
        - self._calculate_age(actor)
        - self._weighted_random_deity(alignment)
        - self._base_hp(role, constitution)
        - self._inherit_stats(parent_a, parent_b)
    """

    ADVENTURER_BIRTH_COOLDOWN_TICKS = 1080
    MAX_SOFT_CHILDREN_PER_ADVENTURER_PAIR = 6

    def _legacy_tick(self) -> None:
        self._cleanup_adventurer_spouses()
        self._handle_adventurer_pairing()
        self._handle_adventurer_births()
        self._update_ruling_houses()

    def _cleanup_adventurer_spouses(self) -> None:
        for actor in self.world.living_actors():
            if not actor.is_adventurer():
                continue
            if actor.spouse_id is None:
                continue
            spouse = self.world.actors.get(actor.spouse_id)
            if spouse is None or not spouse.alive:
                actor.spouse_id = None

    def _handle_adventurer_pairing(self) -> None:
        world = self.world

        candidates = [
            a for a in world.living_actors()
            if a.is_adventurer()
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
                and other.alive
                and other.is_adventurer()
                and other.spouse_id is None
                and self._calculate_age(other) >= 18
                and self._can_form_legacy_pair(actor, other)
            ]

            if not locals_:
                continue

            region = world.regions[actor.region_id]
            chance = 0.0015

            if region.order >= 55:
                chance += 0.001
            if region.control >= 20:
                chance += 0.001
            if region.control <= -20:
                chance -= 0.001

            if actor.party_id is not None:
                chance += 0.0005

            if self.rng.random() < max(0.0005, chance):
                partner = self.rng.choice(locals_)
                actor.spouse_id = partner.id
                partner.spouse_id = actor.id
                world.log(
                    f"{actor.short_name()} and {partner.short_name()} bind their fates in {world.region_name(actor.region_id)}.",
                    importance=2,
                    category="legacy_pairing",
                )

    def _can_form_legacy_pair(self, actor: "Actor", other: "Actor") -> bool:
        if actor.id == other.id:
            return False
        if not actor.alive or not other.alive:
            return False
        if not actor.is_adventurer() or not other.is_adventurer():
            return False

        law_gap = abs(actor.alignment.law_axis - other.alignment.law_axis)
        moral_gap = abs(actor.alignment.moral_axis - other.alignment.moral_axis)

        return law_gap <= 2 and moral_gap <= 1

    def _handle_adventurer_births(self) -> None:
        world = self.world

        for actor in list(world.living_actors()):
            if not actor.is_adventurer():
                continue
            if actor.spouse_id is None:
                continue

            spouse = world.actors.get(actor.spouse_id)
            if spouse is None or not spouse.alive or not spouse.is_adventurer():
                continue

            age_a = self._calculate_age(actor)
            age_b = self._calculate_age(spouse)

            if age_a < 18 or age_b < 18 or age_a > 45 or age_b > 60:
                continue

            if actor.id > spouse.id:
                continue

            children = self._living_children_of_pair(actor, spouse)
            last_birth_tick = self._pair_last_birth_tick(actor, spouse)

            if self.world.tick - last_birth_tick < self.ADVENTURER_BIRTH_COOLDOWN_TICKS:
                continue

            chance = self._adventurer_birth_chance_for_pair(actor, spouse)

            if children >= self.MAX_SOFT_CHILDREN_PER_ADVENTURER_PAIR:
                chance *= 0.35
            if children >= self.MAX_SOFT_CHILDREN_PER_ADVENTURER_PAIR + 1:
                chance *= 0.10
            if children >= self.MAX_SOFT_CHILDREN_PER_ADVENTURER_PAIR + 2:
                chance = 0.0

            if self.rng.random() < chance:
                child = self._create_adventurer_child(actor, spouse)
                actor.last_birth_tick = self.world.tick
                spouse.last_birth_tick = self.world.tick
                world.log(
                    f"A child is born to {actor.short_name()} and {spouse.short_name()} in {world.region_name(child.region_id)}.",
                    importance=2,
                    category="legacy_birth",
                )

    def _adventurer_birth_chance_for_pair(self, parent_a: "Actor", parent_b: "Actor") -> float:
        region = self.world.regions[parent_a.region_id]

        chance = 0.0015

        if region.order >= 60:
            chance += 0.0015
        if region.control >= 20:
            chance += 0.001
        if region.control <= -20:
            chance -= 0.001

        chance -= region.danger * 0.0003

        avg_luck = (parent_a.luck + parent_b.luck) / 2.0
        avg_rep = (parent_a.reputation + parent_b.reputation) / 2.0

        chance += (avg_luck - 10) * 0.00015
        chance += min(0.001, avg_rep * 0.00002)

        return max(0.0002, min(0.008, chance))

    def _create_adventurer_child(self, parent_a: "Actor", parent_b: "Actor") -> "Actor":
        world = self.world
        new_id = max(world.actors.keys()) + 1

        alignment = self._inherit_alignment(parent_a, parent_b)
        deity = self._inherit_deity(parent_a, parent_b, alignment)

        stats = self._inherit_stats(parent_a, parent_b)
        hp = self._base_hp(Role.COMMONER, stats[2])

        surname = parent_a.surname if self.rng.random() < 0.60 else parent_b.surname

        child = Actor(
            id=new_id,
            name=self.rng.choice(FIRST_NAMES),
            surname=surname,
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
        world.generated_by_role[Role.COMMONER] += 1
        return child

    def _inherit_alignment(self, parent_a: "Actor", parent_b: "Actor") -> "Alignment":
        if self.rng.random() < 0.40:
            return parent_a.alignment
        if self.rng.random() < 0.80:
            return parent_b.alignment
        return self.rng.choice([parent_a.alignment, parent_b.alignment, self.rng.choice(list(Alignment))])

    def _inherit_deity(self, parent_a: "Actor", parent_b: "Actor", alignment: "Alignment") -> "Deity":
        if parent_a.deity == parent_b.deity and self.rng.random() < 0.75:
            return parent_a.deity
        if self.rng.random() < 0.40:
            return self.rng.choice([parent_a.deity, parent_b.deity])
        return self._weighted_random_deity(alignment)

    def _living_children_of_pair(self, parent_a: "Actor", parent_b: "Actor") -> int:
        count = 0
        pair = {parent_a.id, parent_b.id}
        for actor in self.world.living_actors():
            mother_id = getattr(actor, "mother_id", None)
            father_id = getattr(actor, "father_id", None)
            if {mother_id, father_id} == pair:
                count += 1
        return count

    def _pair_last_birth_tick(self, parent_a: "Actor", parent_b: "Actor") -> int:
        a_tick = getattr(parent_a, "last_birth_tick", -999999)
        b_tick = getattr(parent_b, "last_birth_tick", -999999)
        return max(a_tick, b_tick)

    def _update_ruling_houses(self) -> None:
        """
        Placeholder hook for dynasty / kingdom logic.

        Intended future behavior:
        - identify stable ruling bloodlines
        - prefer succession by child / lineage before free-for-all rulership
        - found houses / dynasties for notable rulers
        """
        return


# injected globals
FIRST_NAMES: List[str]
TRAITS: List[str]

Alignment: type
Role: type
Deity: type
Actor: type
