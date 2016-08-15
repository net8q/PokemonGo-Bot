from pokemongo_bot.cell_workers.utils import distance
from gym_cache import GymCache

from pprint import pprint

from pokemongo_bot import inventory

def get_gym_details(bot, gym_id, latitude, longitude,refresh=False):

    gym_cache = GymCache(bot)
    response_dict = gym_cache.get(
        gym_id,
        bot.position[0],
        bot.position[1],
        latitude,
        longitude,
        refresh
    )
    return response_dict.get('responses', {}).get('GET_GYM_DETAILS', None)


def get_gym(bot, order_by_distance=False):
    forts = [fort
             for fort in bot.cell['forts']
             if 'latitude' in fort and not 'type' in fort]

    if order_by_distance:
        forts.sort(key=lambda x: distance(
            bot.position[0],
            bot.position[1],
            x['latitude'],
            x['longitude']
        ))

    return forts

def get_best_pokemons(bot, nb=1):

    pokemons=inventory.pokemons().all()
    pokemons.sort(key=lambda x: x.cp, reverse=True)

    attacker_list = [x for x in pokemons if
                     not x.in_fort and
                     x.hp == x.hp_max
                     ]

    if len(attacker_list) < nb:
        return attacker_list
    else:
        return attacker_list[0:nb]


def get_gym_level(gym_xp):
    xp_limits_for_levels = [
        0, 2000, 4000, 8000, 12000, 16000, 20000, 30000, 40000, 50000]

    level = 0
    for xp_limit in xp_limits_for_levels:
        if gym_xp < xp_limit:
            break
        level += 1
    return level


def is_same_team_gym(bot, gym):
    bot_team = bot.player_data.get('team',0)
    owned_by_team = gym.get('owned_by_team',0)
    return bot_team == owned_by_team


def is_neutral(gym):
    owned_by_team = gym.get('owned_by_team',0)
    return owned_by_team == 0


def is_gym_deployable(bot, gym):
    try:
        if is_neutral(gym):
            return True

        if not is_same_team_gym(bot, gym):
            return False

        gym_details = get_gym_details(
            bot,
            gym['id'],
            gym['latitude'],
            gym['longitude']
        )
    except:
        raise

    try:
        # Too far/other error
        if gym_details is None:
            return False

        gym_xp = gym_details['gym_state']['fort_data']['gym_points']
        nb_guards = len(gym_details['gym_state']['memberships'])

        owner_list = [ x['pokemon_data']['owner_name'] for x in gym_details['gym_state']['memberships'] ]

        # Already deployed
        if bot.player_data['username'] in owner_list:
            return False

        # Free slots ?
        return get_gym_level(gym_xp) > nb_guards
    except (KeyError, TypeError) as e:
        pprint(gym_details)
        raise

def count_pokemons_in_fort(bot):
    pokemons=inventory.pokemons().all()
    defender_list = [x for x in pokemons if x.in_fort ]
    pprint(defender_list)
    return len(defender_list)
