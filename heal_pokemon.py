import json
import os
from pokemongo_bot import logger
from pokemongo_bot.base_task import BaseTask
from pokemongo_bot.worker_result import WorkerResult
from pokemongo_bot.tree_config_builder import ConfigException
from pokemongo_bot.item_list import Item
from pokemongo_bot.human_behaviour import sleep
from pokemongo_bot import inventory

# TODO
# Revive
# Choose best items to heal (Knapsack problem like)


class HealPokemon(BaseTask):

    SUPPORTED_TASK_API_VERSION = 1

    def initialize(self):
        self.bot.event_manager.register_event(
            'healed_pokemon',
            parameters=(
                'name',
                'cp',
                'item'
            )
        )
        self.bot.event_manager.register_event(
            'revived_pokemon',
            parameters=(
                'name',
                'cp',
                'item'
            )
        )
        self.heal_item = Item.ITEM_SUPER_POTION

    def should_run(self):
        return True

    def work(self):

        if not self.should_run():
            return WorkerResult.SUCCESS

        wounded_list = self.get_wounded()

        # Nothing to do
        if len(wounded_list) == 0:
            return WorkerResult.SUCCESS

        for pk in wounded_list:
            self.do_heal(pk)

        # After running, update health info
        inventory.refresh_inventory()
        return WorkerResult.SUCCESS

    def get_wounded(self):
        return [ x for x in inventory.pokemons().all() if x.hp < x.hp_max and not x.in_fort ]

    def get_best_heal_item(self,hp_to_heal):
        items=inventory.items().all()
        for item in items:
            # Not a potion
            if item.id < 100 or item.id > 200:
                continue

            if item.count == 0:
                continue

            # Get rid of low quality first
            # Assuming ordered by id
            return item

    def do_heal(self, pk):

        item=self.get_best_heal_item(pk.hp_max - pk.hp)
        response_dict = self.bot.api.use_item_potion(
            item_id=item.id,
            pokemon_id=pk.id
        )

        result = response_dict['responses'].get(
            'USE_ITEM_POTION', {}).get('result', None)

        if(result == 1):
            self.emit_event(
                'healed_pokemon',
                formatted='Healed {name} ({cp}cp) with {item}',
                data={
                    'name': pk.name,
                    'cp': pk.cp,
                    'item': item.name
                }
            )
            item.remove(1)
            # Simulate app
            sleep(1)
        else:
            self.logger.info("Error using potion : " + str(result))

