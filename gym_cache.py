import time
from pprint import pprint
from pokemongo_bot.cell_workers.utils import distance, format_dist


class GymCache(object):

    class __GymCache(object):

        def __init__(self, bot):
            self.bot = bot
            self.cache = {}
            self.last_fetch = 0
            self.fetch_delay = 2
            self.cache_length_seconds = 60 * 10

        def get(self, gym_id, player_latitude, player_longitude, gym_latitude, gym_longitude,refresh=False):
            dist = distance(
                player_latitude,
                player_longitude,
                gym_latitude,
                gym_longitude
            )

            current_time = time.time()
            if gym_id not in self.cache or refresh:
                if dist > 1000:
                    # Too Far, needs to be < 1km
                    return self.cache.get('gym_id',{})

                fetch_timer = current_time - self.fetch_delay
                if fetch_timer < self.fetch_delay:
                    sleep(self.fetch_delay - fetch_timer)

                response_gym_details = self.bot.api.get_gym_details(
                    gym_id=gym_id,
                    player_latitude=player_latitude,
                    player_longitude=player_longitude,
                    gym_latitude=gym_latitude,
                    gym_longitude=gym_longitude
                )

                try:
                    result = response_gym_details['responses'][
                        'GET_GYM_DETAILS']['result']
                except KeyError:
                    self.cache[gym_id] = {}
                else:
                    if result == 1:
                        current_time = time.time()
                        response_gym_details['last_fetched'] = current_time
                        self.last_fetch = current_time
                        self.cache[gym_id] = response_gym_details
                    else:
                        self.cache[gym_id]={}

            gym_info = self.cache[gym_id]
            gym_info['last_accessed'] = current_time

            self._remove_stale_gyms()
            return gym_info

        def _remove_stale_gyms(self):
            for gym_id, gym_details in self.cache.items():
                try:
                    if gym_details['last_fetched'] < time.time() - self.cache_length_seconds:
                        del self.cache[gym_id]
                except KeyError:
                    # Invalid/response empty Gym
                    del self.cache[gym_id]

    instance = None

    def __init__(self, bot):
        if not GymCache.instance:
            GymCache.instance = GymCache.__GymCache(bot)

    def __getattr__(self, name):
        return getattr(self.instance, name)
