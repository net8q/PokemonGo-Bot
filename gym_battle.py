
import time

from pprint import pprint
import logging

from gym_utils import get_best_pokemons

from pokemongo_bot.base_task import BaseTask
from pokemongo_bot import logger

from pokemongo_bot import inventory

class GymBattle(BaseTask):

    def __init__(self,bot,gym_details):
        self.bot=bot
        self.logger = logging.getLogger(type(self).__name__)
        self.gym=gym_details

    @staticmethod
    def register_events(bot):
        bot.event_manager.register_event(
            'attack_gym',
            parameters=(
                'defender',
                'state'
            )
        )
        bot.event_manager.register_event(
            'start_gym_battle',
        )

    def current_milli_time(self):
        return int(round(time.time() * 1000))

    def quit_battle(self):
        self.logger.info('Quitting battle')
        return self.attack_gym(7)

    def start_gym_battle(self):
        if self.gym['gym_state']['fort_data']['owned_by_team'] == self.bot._player['team']:
            nb_attacker = 1
        else:
            nb_attacker = 6
        self.logger.info('[#] Number of attackers : ' + str(nb_attacker))
        attacker_list = get_best_pokemons(self.bot, nb_attacker)
        if len(attacker_list) < nb_attacker:
            self.logger.info('[x] Not enough attackers available')
            return False

        defender_id = self.gym.get('gym_state', {}).get(
            'memberships', [{}])[0].get('pokemon_data', {}).get('id', None)
        if defender_id is None:
            self.logger.info('[x] Error retrieving defending_pokemon_id')
            return False
        attacker_ids = [attacker_list[i - 1].id for i in range(nb_attacker)]
        response_dict = self.bot.api.start_gym_battle(gym_id=self.gym.get('gym_state').get('fort_data').get('id'),
                                                      attacking_pokemon_ids=attacker_ids,
                                                      defending_pokemon_id=defender_id,
                                                      player_latitude=self.bot.position[
                                                          0],
                                                      player_longitude=self.bot.position[
                                                          1]
                                                      )
        result = response_dict['responses'].get(
            'START_GYM_BATTLE', {}).get('result', None)
        if result == 1:
            self.emit_event('start_gym_battle','Started Gym Battle')
            self.attackers=attacker_list
            self.battle = response_dict['responses']['START_GYM_BATTLE']
            self.last_retrieved_action = self.battle[
                'battle_log']['battle_actions'][-1]
            return True
        else:
            self.logger.info('[x] Start battle failed, code ' % str(result))
            return False

    def log_attack_gym(self,attack_gym_response):
        active_defender = {}
        active_attacker = {}
        try:
            self.active_defender=inventory.Pokemon(attack_gym_response['active_defender']['pokemon_data'])
            active_defender['current_health']=attack_gym_response['active_defender']['current_health']
            active_defender['max_health']=attack_gym_response['active_defender']['pokemon_data']['stamina_max']
            active_defender['name']=self.active_defender.name
            active_defender['cp']=self.active_defender.cp
        except KeyError:
            self.logger.info("Error retrieving active defender infos")
            raise

        try:
            battle_state=attack_gym_response['battle_log']['state']
            battle_state_map= {
                0: 'unset',
                1: 'active',
                2: 'victory',
                3: 'defeated',
                4: 'timed out'
            }
            battle_state=battle_state_map[battle_state]
        except KeyError:
            self.logger.info("Error retrieving battle infos")

        self.emit_event(
            'attack_gym',
            formatted='Battle state : {state}, Attacking : {defender}',
            data={
                'defender': u"{name}, {cp}cp {current_health}/{max_health} pv".format(**active_defender),
                'state': battle_state
            }
        )

        try:
            battle_log=attack_gym_response['battle_log']['battle_actions']
        except KeyError:
            battle_log=[]

        for battle_action in battle_log:
            self.last_retrieved_action=battle_action
            action_type=battle_action['Type']
            if action_type == 4:
                pprint(battle_action)
                # SWAP
                pass
            elif action_type == 5:
                pprint(battle_action)
                # FAINT
                pass
            elif action_type == 8:
                pprint(battle_action)
                # VICTORY
                return False
            elif action_type == 9:
                pprint(battle_action)
                # DEFEAT
                return False
        return True

    def attack_gym(self, action_type):

        if action_type is None:
            action_list=None
        else:
            action = {}
            action['Type'] = action_type
            action['action_start_ms'] = self.current_milli_time()
            action['target_index'] = -1
            action_list=[action]

        response_dict = self.bot.api.attack_gym(gym_id=self.gym.get('gym_state').get('fort_data').get('id'),
                                       battle_id=self.battle.get('battle_id'),
                                       attack_actions=action_list,
                                       last_retrieved_actions=self.last_retrieved_action,
                                       player_latitude=self.bot.position[0],
                                       player_longitude=self.bot.position[1]
                                       )
        try:
            pprint(response_dict)
            attack_gym_response = response_dict['responses'].get(
                'ATTACK_GYM', {})
            result = attack_gym_response.get('result', None)
        except KeyError:
            return {}

        if result == 1:
            return self.log_attack_gym(attack_gym_response)
        else:
            self.logger.info("attack_gym error " + str(result))
            return {}

