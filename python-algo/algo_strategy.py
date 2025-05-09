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
        gamelib.debug_write('Configuring Inspired Strategy...')
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

        self.inspired_strategy(game_state)

        game_state.submit_turn()

    def inspired_strategy(self, game_state):
        self.build_defenses(game_state)
        self.reactive_defense(game_state)

        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)
        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)

        if game_state.turn_number <= 1:
            self.initial_attack(game_state)
            return

        if enemy_scouts > 5:
            self.emergency_defense(game_state)

        if game_state.turn_number <= 2 and game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13, 0], 2)

        if game_state.turn_number >= 12 and game_state.get_resource(MP) >= 15:
            self.demolisher_scout_combo(game_state)
        elif enemy_turrets == 0 and game_state.get_resource(MP) >= 6:
            self.scout_rush(game_state)
        elif game_state.get_resource(MP) >= 10:
            self.scout_rush(game_state)

        if game_state.get_resource(SP) >= 8:
            self.expand_supports(game_state)

    def build_defenses(self, game_state):
        wall_locations = [
            [0,13],[1,13],[2,13],[3,13],[4,13],[5,13],[6,13],[7,13],
            [8,13],[9,13],[10,13],            [17,13],[18,13],[19,13],
            [20,13],[21,13],[22,13],[23,13],[24,13],[25,13],[26,13],[27,13]
        ]
        turret_locations = [[3,12],[24,12],[13,11],[14,11]]

        for loc in wall_locations:
            game_state.attempt_spawn(WALL, loc)

        for loc in turret_locations:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    def expand_supports(self, game_state):
        support_locs = [[13,3],[14,3],[12,3],[15,3]]
        game_state.attempt_spawn(SUPPORT, support_locs)
        for loc in support_locs:
            game_state.attempt_upgrade(loc)

    def reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            repair_location = [location[0], location[1]+1]
            game_state.attempt_spawn(WALL, repair_location)
            game_state.attempt_spawn(TURRET, repair_location)
            game_state.attempt_upgrade(repair_location)

        gap_locations = [[13, 11], [14, 11]]
        for loc in gap_locations:
            if not game_state.contains_stationary_unit(loc):
                game_state.attempt_spawn(WALL, loc)

    def initial_attack(self, game_state):
        spawn = [[13,0],[14,0]]
        best = self.least_damage_spawn_location(game_state, spawn)
        game_state.attempt_spawn(SCOUT, best, 8)

    def massive_attack(self, game_state):
        spawn = [[13,0],[14,0]]
        best = self.choose_attack_side(game_state)
        game_state.attempt_spawn(SCOUT, best, 20)
        if game_state.get_resource(MP) > 15:
            game_state.attempt_spawn(DEMOLISHER, best, 5)

    def demolisher_scout_combo(self, game_state):
        side = self.choose_attack_side(game_state)
        game_state.attempt_spawn(DEMOLISHER, side, 3)
        game_state.attempt_spawn(SCOUT, side, 100)

    def scout_rush(self, game_state):
        best_location = self.choose_attack_side(game_state)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    def emergency_defense(self, game_state):
        emergency_turrets = [[12,11],[15,11],[13,11],[14,11]]
        for loc in emergency_turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

        if game_state.get_resource(MP) >= 3:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

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

    def choose_attack_side(self, game_state):
        spawn_left = [13, 0]
        spawn_right = [14, 0]
        path_left = game_state.find_path_to_edge(spawn_left)
        path_right = game_state.find_path_to_edge(spawn_right)

        left_damage = sum([len(game_state.get_attackers(p, 0)) for p in path_left])
        right_damage = sum([len(game_state.get_attackers(p, 0)) for p in path_right])

        return spawn_left if left_damage < right_damage else spawn_right

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
