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
        game_state.suppress_warnings(False)

        self.pro_strategy(game_state)

        game_state.submit_turn()

    def pro_strategy(self, game_state):
        self.build_full_defense(game_state)
        self.reactive_defense(game_state)

        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)
        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)

        # Emergency defense if they Scout rush
        if enemy_scouts > 5:
            self.spawn_interceptors(game_state)

        # Attack only after strong defense built
        if game_state.turn_number >= 5:
            if enemy_turrets <= 4 and game_state.get_resource(MP) >= 8:
                self.smart_scout_attack(game_state)

        # Extra Supports if spare SP
        if game_state.get_resource(SP) >= 10:
            self.build_extra_supports(game_state)

    def build_full_defense(self, game_state):
        # Double walls
        wall_locations = [[13,13],[14,13],[12,13],[15,13],[11,13],[16,13],
                          [13,12],[14,12],[12,12],[15,12],[11,12],[16,12]]
        # Front turrets
        turret_locations = [[3,12],[24,12],[13,11],[14,11]]

        for loc in wall_locations:
            game_state.attempt_spawn(WALL, loc)
            game_state.attempt_upgrade(loc)

        for loc in turret_locations:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    def build_extra_supports(self, game_state):
        support_locations = [[13,2],[14,2],[12,3],[15,3],[13,3],[14,3]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        for loc in support_locations:
            game_state.attempt_upgrade(loc)

    def reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            repair_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, repair_location)
            game_state.attempt_spawn(WALL, repair_location)
            game_state.attempt_upgrade(repair_location)

    def spawn_interceptors(self, game_state):
        if game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13, 0], 2)

    def smart_scout_attack(self, game_state):
        spawn_side = self.choose_attack_side(game_state)
        game_state.attempt_spawn(SCOUT, spawn_side, 1000)

    def choose_attack_side(self, game_state):
        left_units = self.detect_enemy_unit(game_state, valid_x=range(0,14))
        right_units = self.detect_enemy_unit(game_state, valid_x=range(14,28))

        if left_units < right_units:
            return [13,0]  # Attack left
        else:
            return [14,0]  # Attack right

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
