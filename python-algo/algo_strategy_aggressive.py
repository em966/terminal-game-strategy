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
        gamelib.debug_write('Configuring ultimate aggressive strategy...')
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

        self.aggressive_strategy(game_state)

        game_state.submit_turn()

    def aggressive_strategy(self, game_state):
        self.minimal_defense(game_state)
        self.reactive_defense(game_state)

        # Emergency interception if getting hit badly
        if game_state.turn_number > 3 and game_state.my_health < 15:
            self.emergency_defense(game_state)

        # First turn cheese rush
        if game_state.turn_number <= 1:
            self.cheese_rush(game_state)
            return

        # Attack decision
        if game_state.get_resource(MP) >= 6:
            if self.detect_enemy_unit(game_state, unit_type=TURRET) <= 4:
                self.scout_swarm(game_state)
            else:
                self.demolisher_line_push(game_state)

        # Only build supports after turn 10 and plenty of SP
        if game_state.turn_number > 10 and game_state.get_resource(SP) >= 8:
            self.build_supports(game_state)

    def minimal_defense(self, game_state):
        basic_walls = [[13,11], [14,11], [12,11], [15,11]]
        basic_turrets = [[13,10], [14,10]]
        
        game_state.attempt_spawn(WALL, basic_walls)
        for wall in basic_walls:
            game_state.attempt_upgrade(wall)

        game_state.attempt_spawn(TURRET, basic_turrets)
        for turret in basic_turrets:
            game_state.attempt_upgrade(turret)

    def build_supports(self, game_state):
        support_locations = [[13,2],[14,2],[12,3],[15,3]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        for loc in support_locations:
            game_state.attempt_upgrade(loc)

    def cheese_rush(self, game_state):
        # Full scout rush early
        spawn_options = [[13,0],[14,0]]
        best_location = self.least_damage_spawn_location(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    def scout_swarm(self, game_state):
        spawn_options = [[13,0],[14,0]]
        best_spawn = self.least_damage_spawn_location(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_spawn, 1000)

    def demolisher_line_push(self, game_state):
        spawn_location = [13, 0]
        game_state.attempt_spawn(DEMOLISHER, spawn_location, 1000)

    def emergency_defense(self, game_state):
        emergency_turrets = [[11,10],[16,10]]
        for loc in emergency_turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)
        if game_state.get_resource(MP) >= 3:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 3)

    def reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            repair_loc = [location[0], location[1]+1]
            game_state.attempt_spawn(WALL, repair_loc)
            game_state.attempt_upgrade(repair_loc)
            game_state.attempt_spawn(TURRET, repair_loc)
            game_state.attempt_upgrade(repair_loc)

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
        total = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type):
                        if (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                            total += 1
        return total

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        breaches = state["events"]["breach"]
        for breach in breaches:
            loc = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            if not unit_owner_self:
                gamelib.debug_write('Breach at: {}'.format(loc))
                self.scored_on_locations.append(loc)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
