# -*- coding: utf-8 -*-

import time

import pprint
import logging

from pgoapi.utilities import f2i

from pokemongo_bot.base_task import BaseTask

from pokemongo_bot import logger
from pokemongo_bot.constants import Constants
from pokemongo_bot.human_behaviour import sleep
from pokemongo_bot.step_walker import StepWalker
from pokemongo_bot.worker_result import WorkerResult
from pokemongo_bot.cell_workers.utils import distance, format_dist

from pokemongo_bot.cell_workers.follow_spiral import FollowSpiral

import gym_utils


class MoveToGymWorker(BaseTask):

    SUPPORTED_TASK_API_VERSION = 1

    def initialize(self):
        self.bot.event_manager.register_event(
            'moving_to_gym',
            parameters=(
                'gym_name',
                'distance'
            )
        )
        spiral_config = {
            'diameter': 4,
            'step_size': 1000
        }
        self.followspiral = FollowSpiral(self.bot, spiral_config)
        # State info to avoid spam in logs
        self.state_spiral=False

    def should_run(self):
        return True

    def work(self):

        fort = self.get_nearest_gym()
        if not self.should_run():
            return WorkerResult.SUCCESS

        if fort is None:
            if not self.state_spiral:
                # 0nly log on state change
                self.logger.info('No gym found, using spiral mode')
                self.state_spiral=True
            return self.followspiral.work()
        else:
            if self.state_spiral:
                # Logging mode change
                self.state_spiral=False
                self.logger.info('Gym found')

        lat = fort['latitude']
        lng = fort['longitude']
        details = gym_utils.get_gym_details(self.bot, fort['id'], lat, lng)
        if details is None:
            return WorkerResult.ERROR

        # Unit to use when printing formatted distance
        unit = self.bot.config.distance_unit

        dist = distance(
            self.bot.position[0],
            self.bot.position[1],
            lat,
            lng
        )


        if dist > Constants.MAX_DISTANCE_FORT_IS_REACHABLE:
            try:
                fort_name = details.get('name', 'Unknown').encode('utf8', 'replace')
                fort_name = u"{}".format(fort_name)
            except UnicodeDecodeError:
                fort_name = details.get('name', 'Unknown').encode('ascii', 'ignore')
                fort_name = u"{}".format(fort_name)

            fort_event_data = {
                'distance': format_dist(dist, unit),
                'gym_name': fort_name,
            }
            self.emit_event(
                'moving_to_gym',
                formatted="Moving towards gym {gym_name} - {distance}",
                data=fort_event_data
            )
            step_walker = StepWalker(
                self.bot,
                self.bot.config.walk,
                lat,
                lng
            )

            if not step_walker.step():
                return WorkerResult.RUNNING

        return WorkerResult.SUCCESS

    def get_nearest_gym(self):
        forts = gym_utils.get_gym(self.bot, order_by_distance=True)

        # TODO
        # Only deployable forts (neutral/same team with free slots)
        # Only forts without our own deployed pokemons
        # Only same team forts
        # Only enemy forts

        # Deployable
        forts = [x for x in forts if gym_utils.is_gym_deployable(self.bot, x)]

        # Same Team
        # forts = [x for x in forts if gym_utils.is_same_team_gym(self.bot, x)]

        # Enemy Team
        # forts = [x for x in forts if not gym_utils.is_same_team_gym(self.bot, x)]

        if len(forts) > 0:
            return forts[0]
        else:
            return None
