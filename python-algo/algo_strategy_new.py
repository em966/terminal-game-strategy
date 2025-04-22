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
        gamelib.debug_write('Configuring the ultimate strategy...')
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

        self.new_strategy(game_state)

        game_state.submit_turn()

    def new_strategy(self, game_state):
        self.build_initial_defenses(game_state)
        self.reactive_defense(game_state)

        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)
        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)

        # Early cheese attack
        if game_state.turn_number <= 1:
            self.cheese_rush(game_state)
            return

        # Defend against scout rushes early
        if enemy_scouts > 5:
            self.build_emergency_turrets(game_state)

        # Small interceptor every 2 turns
        if game_state.turn_number % 2 == 0:
            self.spawn_interceptors(game_state)

        # Attack decisions
        if enemy_turrets <= 4:
            self.smart_scout_rush(game_state)
        else:
            self.demolisher_push_with_protection(game_state)

        # Boost economy after 15 turns
        if game_state.turn_number >= 15 and game_state.get_resource(SP) >= 10:
            self.expand_supports(game_state)

    # Opening defense with core turrets and walls
    def build_initial_defenses(self, game_state):
        core_walls = [[13,13],[14,13],[13,12],[14,12]]
        turrets = [[12,11],[15,11]]

        for loc in core_walls:
            game_state.attempt_spawn(WALL, loc)
            game_state.attempt_upgrade(loc)

        for loc in turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    # Defend where breached
    def reactive_defense(self, game_state):
        for loc in self.scored_on_locations:
            repair = [loc[0], loc[1]+1]
            game_state.attempt_spawn(WALL, repair)
            game_state.attempt_spawn(TURRET, repair)
            game_state.attempt_upgrade(repair)

    # Early rush with scouts
    def cheese_rush(self, game_state):
        options = [[13,0],[14,0]]
        best_loc = self.least_damage_spawn_location(game_state, options)
        game_state.attempt_spawn(SCOUT, best_loc, 6)

    # Emergency turrets against scout rushes
    def build_emergency_turrets(self, game_state):
        emergency_spots = [[11,10],[12,10],[15,10],[16,10]]
        for loc in emergency_spots:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    # Interceptors for cheap blocking
    def spawn_interceptors(self, game_state):
        if game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

    # Constant scout waves if enemy is weak
    def smart_scout_rush(self, game_state):
        options = [[13,0],[14,0]]
        best_loc = self.least_damage_spawn_location(game_state, options)
        if game_state.get_resource(MP) >= 6:
            game_state.attempt_spawn(SCOUT, best_loc, 5)

    # Demolisher push with protection walls
    def demolisher_push_with_protection(self, game_state):
        funnel = [[8,11],[9,11],[18,11],[19,11]]
        for loc in funnel:
            game_state.attempt_spawn(WALL, loc)
            game_state.attempt_upgrade(loc)
        if game_state.get_resource(MP) >= 6:
            game_state.attempt_spawn(DEMOLISHER, [13,0], 4)

    # Stack support structures late-game
    def expand_supports(self, game_state):
        supports = [[13,3],[14,3],[12,3],[15,3]]
        for loc in supports:
            game_state.attempt_spawn(SUPPORT, loc)
            game_state.attempt_upgrade(loc)

    # Calculate spawn based on least danger path
    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        for loc in location_options:
            path = game_state.find_path_to_edge(loc)
            dmg = 0
            for step in path:
                attackers = game_state.get_attackers(step, 0)
                for attacker in attackers:
                    dmg += attacker.damage_i
            damages.append(dmg)
        return location_options[damages.index(min(damages))]

    # Enemy stationary units
    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total = 0
        for loc in game_state.game_map:
            if game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type):
                        if (valid_x is None or loc[0] in valid_x) and (valid_y is None or loc[1] in valid_y):
                            total += 1
        return total

    # Enemy mobile units
    def detect_enemy_mobile_units(self, game_state, unit_type):
        count = 0
        for loc in game_state.game_map:
            if not game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    if unit.player_index == 1 and unit.unit_type == unit_type:
                        count += 1
        return count

    # Log breaches to react
    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        breaches = state["events"]["breach"]
        for breach in breaches:
            loc = breach[0]
            unit_self = True if breach[4] == 1 else False
            if not unit_self:
                gamelib.debug_write(f"Got scored on at: {loc}")
                self.scored_on_locations.append(loc)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
