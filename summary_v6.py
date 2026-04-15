from __future__ import annotations
from typing import Optional, Tuple, List
import io
from contextlib import redirect_stdout


def _pick_top_hero_and_villain(sim) -> Tuple[Optional[object], Optional[object]]:
    everyone = list(sim.world.actors.values())
    heroes = [a for a in everyone if a.is_adventurer() and not a.is_evil()]
    villains = [a for a in everyone if a.is_adventurer() and a.is_evil()]
    hero = max(
        heroes,
        key=lambda a: (
            a.reputation,
            a.dragon_kills,
            a.horror_kills,
            a.monster_kills,
            a.kills,
            a.power_rating(),
        ),
        default=None,
    )
    villain = max(
        villains,
        key=lambda a: (
            a.reputation,
            a.regions_oppressed,
            a.kills,
            a.monster_kills,
            a.power_rating(),
        ),
        default=None,
    )
    return hero, villain


def _deity_influence_summary(sim) -> List[Tuple[object, int, int, int, float]]:
    surviving = sim.world.living_actors()
    soul_weight = 2
    results = []
    total_influence = 0

    for deity in sim.Deity:
        living = len([actor for actor in surviving if actor.deity == deity])
        souls = sim.world.souls_by_deity.get(deity, 0)
        influence = living + (souls * soul_weight)
        results.append((deity, living, souls, influence, 0.0))
        total_influence += influence

    if total_influence <= 0:
        return [(deity, living, souls, influence, 0.0) for deity, living, souls, influence, _ in results]

    final = []
    for deity, living, souls, influence, _ in results:
        share = influence / total_influence * 100.0
        final.append((deity, living, souls, influence, share))
    return final


def _top_region(sim):
    return max(sim.world.regions.values(), key=lambda r: (r.order, r.control, -r.danger))


def _top_deity(sim):
    return max(_deity_influence_summary(sim), key=lambda item: item[3])


def _join_phrases(parts: List[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _hero_tale(sim, hero) -> str:
    parts = []
    if hero.dragon_kills:
        parts.append(f"slew {hero.dragon_kills} dragon{'s' if hero.dragon_kills != 1 else ''}")
    if hero.horror_kills:
        parts.append(f"destroyed {hero.horror_kills} ancient horror{'s' if hero.horror_kills != 1 else ''}")
    if hero.giant_kills:
        parts.append(f"felled {hero.giant_kills} giant{'s' if hero.giant_kills != 1 else ''}")
    if hero.regions_defended:
        parts.append(f"defended {hero.regions_defended} region{'s' if hero.regions_defended != 1 else ''}")
    if not parts:
        parts.append(f"earned renown through {hero.kills} victories")
    return f"{hero.full_name()} {_join_phrases(parts)} in {sim.world.region_name(hero.region_id)}."


def _villain_tale(sim, villain) -> str:
    parts = []
    if villain.regions_oppressed:
        parts.append(f"oppressed {villain.regions_oppressed} region{'s' if villain.regions_oppressed != 1 else ''}")
    if villain.kills:
        parts.append(f"left {villain.kills} bodies in their wake")
    if villain.dragon_kills:
        parts.append(f"slew {villain.dragon_kills} dragon{'s' if villain.dragon_kills != 1 else ''}")
    if villain.horror_kills:
        parts.append(f"destroyed {villain.horror_kills} ancient horror{'s' if villain.horror_kills != 1 else ''}")
    if villain.giant_kills:
        parts.append(f"felled {villain.giant_kills} giant{'s' if villain.giant_kills != 1 else ''}")
    if not parts:
        parts.append(f"spread fear from {sim.world.region_name(villain.region_id)}")
    return f"{villain.full_name()} {_join_phrases(parts)}."


def _chronicle_title(sim, hero, top_region, top_deity) -> str:
    if hero is not None:
        return f"The Chronicle of {hero.short_name()}, {top_region.name}, and {top_deity.value}"
    return f"The Chronicle of {top_region.name} under {top_deity.value}"


def _death_line(world, actor) -> str:
    if not actor.death_timestamp:
        return "Still living"

    killer_id = getattr(actor, "death_killer_id", None)
    if killer_id is not None and killer_id in world.actors:
        killer = world.actors[killer_id]
        return f"{actor.death_timestamp} — {actor.death_cause} (caused by {killer.full_name()})"

    return f"{actor.death_timestamp} — {actor.death_cause}"


def print_summary(sim, years=None) -> None:
    world = sim.world
    for region_id in world.regions:
        world.evaluate_region_rule(region_id)

    hero, villain = _pick_top_hero_and_villain(sim)
    top_region = _top_region(sim)
    top_deity, _, _, _, _ = _top_deity(sim)

    influential_party = max(
        world.parties.values(),
        key=lambda p: (
            len(p.member_ids),
            sum(world.actors[mid].reputation for mid in p.member_ids if mid in world.actors),
        ),
        default=None,
    )

    print("=" * 72)
    print("WORLD SUMMARY")
    print("=" * 72)
    print(f"Seed: {world.seed_used}")
    print(f"Ticks simulated: {world.tick}")
    runtime_seconds = getattr(world, "runtime_seconds", None)
    if runtime_seconds is not None:
        runtime_minutes = runtime_seconds / 60.0
        print(f"Realtime duration: {runtime_seconds:.2f} seconds ({runtime_minutes:.2f} minutes)")
    year, month, day, tod, season = world.current_calendar()
    print(f"Current date: Year {year}, {season}, {sim.MONTH_NAMES[month - 1]} {day}, {tod}")
    print(f"Living population: {len(world.living_actors())} / {len(world.actors)}")
    print(f"Living monsters: {len(world.living_monsters())} / {sum(world.generated_monsters_by_kind.values())}")
    print(f"Active parties: {len(world.parties)}")
    print()

    if hero is not None:
        print("Most celebrated hero:")
        print(f"  {hero.full_name()} — {hero.alignment.value}, {hero.role.value}, rep={hero.reputation}, dragon kills={hero.dragon_kills}, horror kills={hero.horror_kills}, region={world.region_name(hero.region_id)}")
        print(f"  Birth: {hero.birth_text()}")
        print(f"  Death: {_death_line(world, hero)}")
        print(f"  Deeds: {hero.notable_deeds_summary()}")
        print()

    if villain is not None:
        print("Most feared villain:")
        print(f"  {villain.full_name()} — {villain.alignment.value}, {villain.role.value}, rep={villain.reputation}, kills={villain.kills}, oppressed regions={villain.regions_oppressed}, region={world.region_name(villain.region_id)}")
        print(f"  Birth: {villain.birth_text()}")
        print(f"  Death: {_death_line(world, villain)}")
        print(f"  Deeds: {villain.notable_deeds_summary()}")
        print()

    print(_chronicle_title(sim, hero, top_region, top_deity))
    avg_order = sum(region.order for region in world.regions.values()) / len(world.regions)
    good_regions = len([r for r in world.regions.values() if r.control >= 20])
    evil_regions = len([r for r in world.regions.values() if r.control <= -20])
    contested = len(world.regions) - good_regions - evil_regions

    if avg_order >= 70 and good_regions > evil_regions:
        state_line = "The continent ends the year bruised but standing, with villages still able to breathe and sow."
    elif evil_regions > good_regions and avg_order < 50:
        state_line = "The continent ends the year under a darker sky, with fear spreading more quickly than harvest."
    else:
        state_line = "The continent ends the year divided, its fate unresolved and its borders morally uncertain."

    print(f"  {top_region.name} emerged as the strongest region, carrying order {top_region.order} under the broadest surviving favor of {top_deity.value}.")
    if hero is not None:
        print(f"  {_hero_tale(sim, hero)}")
    if villain is not None:
        print(f"  {_villain_tale(sim, villain)}")
    print(f"  {state_line}")
    print()

    print("Population by role:")
    living_by_role = {role: 0 for role in sim.Role}
    for actor in world.living_actors():
        living_by_role[actor.role] += 1
    for role in sim.Role:
        print(f"  {role.value:10} {living_by_role[role]:3} / {world.generated_by_role[role]:3}")
    print()

    print("Immortal influence:")
    for deity, living, souls, influence, pct in _deity_influence_summary(sim):
        print(f"  {deity.value:16} living={living:3} souls={souls:3} influence={influence:4} share={pct:5.1f}%")
    print()

    print("Regional state:")
    for region in world.regions.values():
        leaning = "Good" if region.control >= 20 else "Evil" if region.control <= -20 else "Contested"
        ruler = world.actors[region.ruler_id].short_name() if region.ruler_id is not None and world.actors[region.ruler_id].alive else "None"
        print(
            f"  {region.name:14} {region.biome:10} danger={region.danger} "
            f"control={region.control:4} order={region.order:3} lean={leaning:9} ruler={ruler}"
        )
    print()

    print("Monsters still abroad:")
    living_monsters_by_kind = {kind: 0 for kind in sim.MonsterKind}
    for monster in world.living_monsters():
        living_monsters_by_kind[monster.kind] += 1
    for kind in sim.MonsterKind:
        print(f"  {kind.value:14} {living_monsters_by_kind[kind]:3} / {world.generated_monsters_by_kind[kind]:3}")
    print()

    legendary_events = [event for event in world.events if event.category == "legendary_monster_kill"]
    if legendary_events:
        print("Legendary events:")
        seen = set()
        for event in legendary_events[-10:]:
            key = (event.timestamp, event.text)
            if key in seen:
                continue
            seen.add(key)
            print(f"  [{event.timestamp}] {event.text}")
        print()

    notable = [event for event in world.events if event.importance >= 2]
    print("Notable events:")
    for event in notable[-40:]:
        print(f"  [{event.timestamp}] {event.text}")
    print()

    if world.commemorations:
        print("Commemorations:")
        for item in sorted(world.commemorations, key=lambda c: (c.month, c.day, c.name))[:20]:
            region_text = f" in {world.region_name(item.region_id)}" if item.region_id is not None else ""
            print(f"  {sim.MONTH_NAMES[item.month - 1]} {item.day}: {item.name}{region_text} — {item.reason}")
            extra_reason = None
            if item.actor_id is not None and item.actor_id in world.actors:
                extra_reason = world.actors[item.actor_id].notable_deeds_summary()
            if extra_reason:
                print(f"    For {extra_reason}.")
        print()

    if evil_regions == len(world.regions) or (avg_order < 15 and evil_regions >= len(world.regions) - 1):
        assessment = "The continent is fully lost to darkness. Little hope remains."
    elif avg_order >= 60 and good_regions >= evil_regions:
        assessment = "The continent is broadly stable and still capable of thriving."
    elif avg_order < 35 or evil_regions > good_regions + 2:
        assessment = "The continent is slipping into chaos and oppression."
    else:
        assessment = "The continent remains divided, with pockets of order resisting wider instability."

    print("World condition:")
    print(f"  Good-leaning regions: {good_regions}")
    print(f"  Evil-leaning regions: {evil_regions}")
    print(f"  Contested regions: {contested}")
    print(f"  Average order: {avg_order:.1f}")
    print(f"  Assessment: {assessment}")
    print()

    if influential_party is not None:
        leader_name = world.actors[influential_party.leader_id].short_name() if influential_party.leader_id in world.actors else 'Unknown'
        group_name = influential_party.name or f'Party {influential_party.id}'
        print("Most influential party:")
        print(f"  {group_name} — leader={leader_name}, size={len(influential_party.member_ids)}, large_group={influential_party.is_large_group}")
        print()

    adventurers = sorted(
        [actor for actor in world.actors.values() if actor.is_adventurer()],
        key=lambda actor: (
            actor.reputation,
            actor.dragon_kills,
            actor.horror_kills,
            actor.monster_kills,
            actor.kills,
            actor.power_rating(),
        ),
        reverse=True,
    )

    print("Top adventurers, living and dead:")
    shown = 0
    for actor in adventurers:
        birth = f"{sim.MONTH_NAMES[actor.birth_month - 1]} {actor.birth_day}"
        status = "living" if actor.alive else "dead"
        print(
            f"  {actor.full_name():28} {actor.role.value:9} {actor.alignment.value:16} "
            f"{actor.deity.value:16} rep={actor.reputation:3} kills={actor.kills:2} "
            f"mkills={actor.monster_kills:2} dragons={actor.dragon_kills:2} "
            f"horrors={actor.horror_kills:2} luck={actor.luck:2} "
            f"birth={birth:15} status={status:6} region={world.region_name(actor.region_id)}"
        )
        if not actor.alive:
            print(f"    Death: {_death_line(world, actor)}")
        shown += 1
        if shown >= 12:
            break


def write_summary(sim, years) -> None:
    seed = sim.world.seed_used
    filename = f"fantfarm_{seed}_{years}year_summary.txt"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        print_summary(sim, years)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())