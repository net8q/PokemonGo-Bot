# -*- coding: utf-8 -*-

import time

from pprint import pprint
import logging

from pgoapi.utilities import f2i

from pokemongo_bot.base_task import BaseTask

from pokemongo_bot import logger
from pokemongo_bot.constants import Constants
from pokemongo_bot.step_walker import StepWalker
from pokemongo_bot.worker_result import WorkerResult
from pokemongo_bot.cell_workers.utils import distance

import gym_utils


class DeployPokemonToGym(BaseTask):

    SUPPORTED_TASK_API_VERSION = 1

    def initialize(self):
        self.bot.event_manager.register_event(
            'deploy_pokemon_to_gym',
            parameters=(
                'gym_name',
            )
        )

    def should_run(self):
        # Needs to be in a team
        return self.bot.player_data.get('team',0) > 0

    def work(self):
        fort = self.get_gym_in_range()

        if not self.should_run() or fort is None:
            return WorkerResult.SUCCESS

        lat = fort['latitude']
        lng = fort['longitude']

        # Force refresh in case we deployed the tick before
        details = gym_utils.get_gym_details(self.bot, fort['id'], lat, lng,True)

        # Check if still OK
        if not gym_utils.is_gym_deployable(self.bot,fort):
            return WorkerResult.SUCCESS

        try:
            fort_name = details.get('name', 'Unknown').encode('utf8', 'replace')
            fort_name = u"{}".format(fort_name)
        except UnicodeDecodeError:
            fort_name = details.get('name', 'Unknown').encode('ascii', 'ignore')
            fort_name = u"{}".format(fort_name)

        self.logger.info('Now at Gym: ' + fort_name)

        self.gym = details
        event_data = {
            'gym_name': fort_name,
        }

        if self.deploy_pokemon_to_fort():
            self.emit_event(
                'deploy_pokemon_to_gym',
                formatted="Deploys to gym {gym_name} succeeded",
                data=event_data
            )
            return WorkerResult.SUCCESS
        else:
            self.emit_event(
                'deploy_pokemon_to_gym',
                formatted="Deploys to gym {gym_name} failed",
                data=event_data
            )
            return WorkerResult.ERROR

    def deploy_pokemon_to_fort(self):
        deploy_list = gym_utils.get_best_pokemons(self.bot, 1)

        if len(deploy_list) < 1 or deploy_list is None:
            return False

        deploy_id = deploy_list[0].id
        responses_dict = self.bot.api.fort_deploy_pokemon(
            fort_id=self.gym.get('gym_state').get('fort_data').get('id'),
            pokemon_id=deploy_id,
            player_latitude=self.bot.position[0],
            player_longitude=self.bot.position[1]
        )
        try:
            result = responses_dict['responses'][
                'FORT_DEPLOY_POKEMON']['result']
        except KeyError:
            pprint(responses_dict)
            return False
        else:
            if result == 1:
                return True
            else:
                self.logger.info("Deploy fail with code " + str(result))
                return False

    def get_gym_in_range(self):
        forts = gym_utils.get_gym(self.bot, order_by_distance=True)
        # Only deployable gym
        forts = [x for x in forts if gym_utils.is_gym_deployable(self.bot, x)]

        if len(forts) == 0:
            return None

        fort = forts[0]

        distance_to_fort = distance(
            self.bot.position[0],
            self.bot.position[1],
            fort['latitude'],
            fort['longitude']
        )

        if distance_to_fort <= Constants.MAX_DISTANCE_FORT_IS_REACHABLE:
            return fort

        return None
