import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 3)
        game_state.suppress_warnings(False)

        self.dynamic_strategy(game_state)

        game_state.submit_turn()

    def dynamic_strategy(self, game_state):
        self.build_defenses(game_state)
        self.build_funnels(game_state)
        self.reactive_defense(game_state)
        
        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)
        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)
        
        # Early attack, cheese rush
        if game_state.turn_number <= 1:
            self.cheese_rush(game_state)
            return
        
        # Emergency defense if they scout rush
        if enemy_scouts > 5:
            self.emergency_defense(game_state)

        # Keep building 1-2 interceptors every few turns
        if game_state.turn_number % 2 == 0:
            self.spawn_interceptors(game_state)

        # Attack decisions based on enemy turrets and our MP
        if game_state.turn_number >= 5:
            if enemy_turrets <= 4 and game_state.get_resource(MP) >= 8:
                self.smart_scout_rush(game_state)
            elif enemy_turrets > 4 and game_state.get_resource(MP) >= 8:
                self.demolisher_push(game_state)

        # Extra supports if resources allow
        if game_state.get_resource(SP) >= 10:
            self.build_extra_supports(game_state)

    # Builds a full defense with more walls and upgrades than scout rush strat
    def build_defenses(self, game_state):
        walls = [
            [13,13],[14,13],[12,13],[15,13],[11,13],[16,13],
            [13,12],[14,12],[12,12],[15,12],[11,12],[16,12],
            [13,11],[14,11],[12,11],[15,11]
        ]
        turrets = [[3,12],[24,12],[13,10],[14,10]]

        for location in walls:
            game_state.attempt_spawn(WALL, location)
            game_state.attempt_upgrade(location)

        for location in turrets:
            game_state.attempt_spawn(TURRET, location)
            game_state.attempt_upgrade(location)

    def build_extra_supports(self, game_state):
        support_locations = [[13,3],[14,3],[13,4],[14,4],[12,3],[15,3]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        for loc in support_locations:
            game_state.attempt_upgrade(loc)

    # Builds a funnel to block enemy units and turrets and channel attacks
    def build_funnels(self, game_state):
        funnel_walls = [[12,1],[13,1],[14,1],[15,1],[12,2],[13,2],[14,2],[15,2]]
        game_state.attempt_spawn(WALL, funnel_walls)
        game_state.attempt_upgrade(funnel_walls)

    def spawn_interceptors(self, game_state):
        if game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

    def reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            repair_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, repair_location)
            game_state.attempt_spawn(WALL, repair_location)
            game_state.attempt_upgrade(repair_location)

    def cheese_rush(self, game_state):
        spawn_locations = [[13,0],[14,0]]
        best_location = self.least_damage_spawn_location(game_state, spawn_locations)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    def emergency_defense(self, game_state):
        emergency_turrets = [[12,10],[15,10],[13,10],[14,10]]
        for loc in emergency_turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)
        # Added interceptors for emergency defense
        if game_state.get_resource(MP) >= 3:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

    def smart_scout_rush(self, game_state):
        spawn_options = [[13,0],[14,0]]
        best_spawn = self.best_path_spawn(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_spawn, 1000)

    def demolisher_push(self, game_state):
        game_state.attempt_spawn(DEMOLISHER, [13,0], 1000)

    def best_path_spawn(self, game_state, spawn_options):
        damages = []
        for location in spawn_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                attackers = game_state.get_attackers(path_location, 0)
                for unit in attackers:
                    damage += unit.damage_i
            damages.append(damage)
        return spawn_options[damages.index(min(damages))]

    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type):
                        if (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                            total_units += 1
        return total_units

    def detect_enemy_mobile_units(self, game_state, unit_type):
        count = 0
        for location in game_state.game_map:
            if not game_state.contains_stationary_unit(location):
                units = game_state.game_map[location]
                for unit in units:
                    if unit.player_index == 1 and unit.unit_type == unit_type:
                        count += 1
        return count

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
