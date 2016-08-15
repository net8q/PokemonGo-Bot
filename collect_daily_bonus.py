# -*- coding: utf-8 -*-

import time

from pprint import pprint
import logging

from pokemongo_bot.base_task import BaseTask

from pokemongo_bot import logger
from pokemongo_bot.worker_result import WorkerResult

import gym_utils


class CollectDailyBonus(BaseTask):

    SUPPORTED_TASK_API_VERSION = 1

    def initialize(self):
        self.bot.event_manager.register_event(
            'collected_daily_bonus',
            parameters=(
                'defender_count',
            )
        )
        self.min_defender = 2

    def should_run(self):
        # Needs to be in a team
        current_timestamp=int(round(time.time() * 1000))
        next_collect=self.bot.player_data.get('daily_bonus',{}).get('next_defender_bonus_collect_timestamp_ms',0)
        return next_collect <  current_timestamp and gym_utils.count_pokemons_in_fort(self.bot) >= self.min_defender

    def work(self):
        if not self.should_run():
            return WorkerResult.SUCCESS

        if self.collect_bonus():
            return WorkerResult.SUCCESS
        else:
            return WorkerResult.ERROR


    def collect_bonus(self):
        responses_dict = self.bot.api.collect_daily_defender_bonus()
        try:
            result = responses_dict['responses'][
                'COLLECT_DAILY_DEFENDER_BONUS']['result']
        except KeyError:
           return False
        else:
            if result == 1:
                defender_count = responses_dict['responses']['COLLECT_DAILY_DEFENDER_BONUS']['defenders_count']
                self.emit_event(
                    'collected_daily_bonus',
                    formatted="Collected bonus for {defender_count} defenders",
                    data={'defender_count': defender_count }
                )
                return True
            else:
                self.logger.info("Collect bonus failed with code " + str(result))
                return False

