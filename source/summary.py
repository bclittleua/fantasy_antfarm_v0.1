from __future__ import annotations

from typing import Optional, Tuple, List


def _pick_top_hero_and_villain(sim) -> Tuple[Optional[object], Optional[object]]:
    living = sim.world.living_actors()
    heroes = [a for a in living if a.is_adventurer() and not a.is_evil()]
    villains = [a for a in living if a.is_adventurer() and a.is_evil()]
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


def _deity_influence_summary(sim) -> List[Tuple[object, int, float]]:
    surviving = sim.world.living_actors()
    total = len(surviving)
    results = []
    for deity in sim.Deity:
        count = len([actor for actor in surviving if actor.deity == deity])
        pct = (count / total * 100.0) if total else 0.0
        results.append((deity, count, pct))
    return results


def _top_region(sim):
    return max(sim.world.regions.values(), key=lambda r: (r.order, r.control, -r.danger))


def _top_deity(sim):
    return max(_deity_influence_summary(sim), key=lambda item: item[2])


def _hero_tale(sim, hero) -> str:
    pieces = []
    if hero.title:
        pieces.append(f"Known as {hero.title}")
    if hero.dragon_kills:
        pieces.append(f"slew {hero.dragon_kills} dragon{'s' if hero.dragon_kills != 1 else ''}")
    if hero.horror_kills:
        pieces.append(f"broke {hero.horror_kills} ancient horror{'s' if hero.horror_kills != 1 else ''}")
    if hero.regions_defended:
        pieces.append(
            f"defended {hero.regions_defended} threatened frontier{'s' if hero.regions_defended != 1 else ''}"
        )
    if not pieces:
        pieces.append(f"earned renown through {hero.kills} victories")
    return f"{hero.full_name()} {'; '.join(pieces)} from {sim.world.region_name(hero.region_id)}."


def _villain_tale(sim, villain) -> str:
    pieces = []
    if villain.title:
        pieces.append(f"Bearing the name {villain.title}")
    if villain.regions_oppressed:
        pieces.append(
            f"oppressed {villain.regions_oppressed} region{'s' if villain.regions_oppressed != 1 else ''}"
        )
    if villain.kills:
        pieces.append(f"left {villain.kills} bodies in their wake")
    if not pieces:
        pieces.append(f"spread fear from {sim.world.region_name(villain.region_id)}")
    return f"{villain.full_name()} {'; '.join(pieces)}."


def _chronicle_title(sim, hero, top_region, top_deity) -> str:
    if hero is not None:
        return f"The Chronicle of {hero.short_name()}, {top_region.name}, and {top_deity.value}"
    return f"The Chronicle of {top_region.name} under {top_deity.value}"


def print_summary(sim) -> None:
    world = sim.world
    for region_id in world.regions:
        world.evaluate_region_rule(region_id)

    hero, villain = _pick_top_hero_and_villain(sim)
    top_region = _top_region(sim)
    top_deity, _, _ = _top_deity(sim)

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
    year, month, day, tod, season = world.current_calendar()
    print(f"Current date: Year {year}, {season}, {sim.MONTH_NAMES[month - 1]} {day}, {tod}")
    print(f"Living population: {len(world.living_actors())} / {len(world.actors)}")
    print(f"Living monsters: {len(world.living_monsters())} / {sum(world.generated_monsters_by_kind.values())}")
    print(f"Active parties: {len(world.parties)}")
    print()

    if hero is not None:
        print("Most celebrated hero:")
        print(
            f"  {hero.full_name()} — {hero.alignment.value}, {hero.role.value}, "
            f"rep={hero.reputation}, dragon kills={hero.dragon_kills}, "
            f"horror kills={hero.horror_kills}, region={world.region_name(hero.region_id)}"
        )
        print()

    if villain is not None:
        print("Most feared villain:")
        print(
            f"  {villain.full_name()} — {villain.alignment.value}, {villain.role.value}, "
            f"rep={villain.reputation}, kills={villain.kills}, "
            f"oppressed regions={villain.regions_oppressed}, region={world.region_name(villain.region_id)}"
        )
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
    for deity, count, pct in _deity_influence_summary(sim):
        print(f"  {deity.value:16} followers={count:3} surviving share={pct:5.1f}%")
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
        print()

    print("World condition:")
    print(f"  Good-leaning regions: {good_regions}")
    print(f"  Evil-leaning regions: {evil_regions}")
    print(f"  Contested regions: {contested}")
    print(f"  Average order: {avg_order:.1f}")
    print()

    if influential_party is not None:
        leader_name = world.actors[influential_party.leader_id].short_name() if influential_party.leader_id in world.actors else 'Unknown'
        group_name = influential_party.name or f'Party {influential_party.id}'
        print("Most influential party:")
        print(f"  {group_name} — leader={leader_name}, size={len(influential_party.member_ids)}, large_group={influential_party.is_large_group}")
        print()

    survivors = sorted(
        world.living_actors(),
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
    print("Top surviving adventurers:")
    shown = 0
    for actor in survivors:
        if not actor.is_adventurer():
            continue
        birth = f"{sim.MONTH_NAMES[actor.birth_month - 1]} {actor.birth_day}"
        print(
            f"  {actor.full_name():28} {actor.role.value:9} {actor.alignment.value:16} "
            f"{actor.deity.value:16} rep={actor.reputation:2} kills={actor.kills:2} "
            f"mkills={actor.monster_kills:2} dragons={actor.dragon_kills:2} "
            f"horrors={actor.horror_kills:2} luck={actor.luck:2} "
            f"hp={actor.hp:2}/{actor.max_hp:2} birth={birth:15} "
            f"region={world.region_name(actor.region_id)}"
        )
        shown += 1
        if shown >= 10:
            break