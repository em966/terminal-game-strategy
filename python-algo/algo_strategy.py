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
        """
        Read in config and perform any initial setup here
        """
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

        self.my_strategy_1(game_state)

        game_state.submit_turn()

    def my_strategy_1(self, game_state):
        # CHEESE RUSH early game
        if game_state.turn_number == 0 or game_state.turn_number == 1:
            self.cheese_rush(game_state)
            return

        self.build_strong_defenses(game_state)
        self.reactive_defense(game_state)

        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)
        if enemy_scouts > 5:
            self.scout_defense_mode(game_state)


        if game_state.turn_number >= 3:
            enemy_interceptors = self.detect_enemy_mobile_units(game_state, INTERCEPTOR)
            if enemy_interceptors > 5:
              self.scout_rush(game_state)
            elif self.detect_enemy_unit(game_state, unit_type=TURRET, valid_x=None, valid_y=[14, 15]) > 4:
                self.demolisher_attack(game_state)
            else:
                self.scout_rush(game_state)


        # Smart Economy Decisions
        if game_state.get_resource(SP) > 15:
            self.upgrade_defenses(game_state)

        if game_state.get_resource(MP) > 12:
            self.extra_supports(game_state)

        if game_state.turn_number >= 5 and game_state.my_health < 15:
            # Play very defensively if low health
            self.heavy_defense_mode(game_state)
        else:
            # Normal attack logic
            if game_state.turn_number >= 3:
                if self.detect_enemy_unit(game_state, unit_type=TURRET, valid_x=None, valid_y=[14, 15]) > 4:
                    self.demolisher_attack(game_state)
                else:
                    self.scout_rush(game_state)

    def build_strong_defenses(self, game_state):
        walls = [[0, 13], [1, 13], [2, 13], [3, 13], [24, 13], [25, 13], [26, 13], [27, 13]]
        turrets = [[3, 12], [24, 12], [6, 11], [21, 11]]
        supports = [[13, 2], [14, 2], [13, 3], [14, 3]]

        for location in walls:
            game_state.attempt_spawn(WALL, location)
        for location in turrets:
            game_state.attempt_spawn(TURRET, location)
        game_state.attempt_spawn(SUPPORT, supports)

    def reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            repair_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, repair_location)
            game_state.attempt_spawn(WALL, repair_location)
            game_state.attempt_upgrade(repair_location)

    def upgrade_defenses(self, game_state):
        wall_upgrades = [[0,13], [1,13], [26,13], [27,13]]
        support_upgrades = [[13,2], [14,2]]
        turret_upgrades = [[3,12], [24,12]]

        for location in wall_upgrades:
            game_state.attempt_upgrade(location)
        for location in support_upgrades:
            game_state.attempt_upgrade(location)
        for location in turret_upgrades:
            game_state.attempt_upgrade(location)

    def extra_supports(self, game_state):
        extra_support_locations = [[12, 3], [15, 3], [12, 4], [15, 4]]
        game_state.attempt_spawn(SUPPORT, extra_support_locations)
        for loc in extra_support_locations:
            game_state.attempt_upgrade(loc)

    def heavy_defense_mode(self, game_state):
        wall_positions = [[i, 12] for i in range(5, 23)]
        turret_positions = [[5, 11], [22, 11]]

        for loc in wall_positions:
            game_state.attempt_spawn(WALL, loc)
        for loc in turret_positions:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    def demolisher_attack(self, game_state):
        wall_line = [[i,11] for i in range(5, 23, 3)]
        for location in wall_line:
            game_state.attempt_spawn(WALL, location)

        game_state.attempt_spawn(DEMOLISHER, [13, 0], 1000)

    def scout_rush(self, game_state):
        spawn_options = [[13, 0], [14, 0]]
        best_spawn = self.least_damage_spawn_location(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_spawn, 1000)

    def cheese_rush(self, game_state):
        rush_locations = [[13, 0], [14, 0]]
        best_location = self.least_damage_spawn_location(game_state, rush_locations)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

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
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
    
    def detect_enemy_mobile_units(self, game_state, unit_type):
        count = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                continue
            units = game_state.game_map[location]
            for unit in units:
                if unit.player_index == 1 and unit.unit_type == unit_type:
                    count += 1
        return count

    def scout_defense_mode(self, game_state):
        """
        Build fast defense against Scout spam.
        """
    # Defensive turrets at edges
        emergency_turrets = [[13, 12], [14, 12], [12, 11], [15, 11]]
        for loc in emergency_turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    # Send interceptors
        if game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13, 0], 2)


    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

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