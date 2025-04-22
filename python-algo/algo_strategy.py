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
        gamelib.debug_write('Setting up PressureWave Strategy...')
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
        game_state.suppress_warnings(False)

        self.execute_pressure_strategy(game_state)

        game_state.submit_turn()

    def execute_pressure_strategy(self, game_state):
        self.build_defenses(game_state)
        self.reactive_defense(game_state)

        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)
        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)

        # Cheese rush very early
        if game_state.turn_number <= 1:
            self.cheese_rush(game_state)
            return

        # Emergency defense if enemy Scout rushes
        if enemy_scouts >= 5:
            self.emergency_defense(game_state)

        # Attack logic
        if enemy_turrets <= 3 and game_state.get_resource(MP) >= 6:
            self.scout_rush(game_state)
        elif game_state.get_resource(MP) >= 10:
            self.demolisher_push(game_state)

        # Build extra Supports for late-game scaling
        if game_state.get_resource(SP) >= 12:
            self.build_extra_supports(game_state)

    def build_defenses(self, game_state):
        walls = [
            [13,13],[14,13],[12,13],[15,13],[11,13],[16,13],
            [13,12],[14,12],[12,12],[15,12]
        ]
        turrets = [[3,12],[24,12],[13,11],[14,11]]

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

    def scout_rush(self, game_state):
        spawn_options = [[13,0],[14,0]]
        best_location = self.least_damage_spawn_location(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    def demolisher_push(self, game_state):
        # Spawn Demolishers protected by some Interceptors
        game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)
        game_state.attempt_spawn(DEMOLISHER, [13,0], 1000)

    def emergency_defense(self, game_state):
        # Quick walls and turrets when under heavy Scout attack
        emergency_locations = [[12,11],[15,11],[13,11],[14,11]]
        for loc in emergency_locations:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

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

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
