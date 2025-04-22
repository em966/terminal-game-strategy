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
        gamelib.debug_write('Configuring custom strategy...')
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

        self.dynamic_strategy_v3(game_state)

        game_state.submit_turn()

    # Main logic for attack/defense each turn
    def dynamic_strategy_v3(self, game_state):
        self.build_defenses(game_state)
        self.build_funnels(game_state)
        self.reactive_defense(game_state)

        enemy_scouts = self.detect_enemy_mobile_units(game_state, SCOUT)
        enemy_turrets = self.detect_enemy_unit(game_state, unit_type=TURRET)

        # Early cheese attack
        if game_state.turn_number <= 1:
            self.cheese_rush(game_state)
            return

        # Emergency interceptors if heavy scout rush detected
        if enemy_scouts > 5:
            self.emergency_defense(game_state)

        # Small interceptor spawn every 2 turns
        if game_state.turn_number % 2 == 0:
            self.spawn_interceptors(game_state)

        # Attack smartly based on situation
        if game_state.turn_number >= 2:
            if enemy_turrets <= 4:
                self.continuous_scout_pressure(game_state)
            else:
                self.demolisher_push_with_funnel(game_state)

        # Upgrade economy if safe
        if game_state.get_resource(SP) >= 10:
            self.build_extra_supports(game_state)

    # Setup full defense structure
    def build_defenses(self, game_state):
        walls = [
            [13,13],[14,13],[12,13],[15,13],[11,13],[16,13],
            [13,12],[14,12],[12,12],[15,12],[11,12],[16,12],
            [13,11],[14,11],[12,11],[15,11]
        ]
        turrets = [[3,12],[24,12],[13,10],[14,10]]

        for loc in walls:
            game_state.attempt_spawn(WALL, loc)
            game_state.attempt_upgrade(loc)
        for loc in turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)

    # Adds funnel walls to control enemy movement
    def build_funnels(self, game_state):
        funnel = [[12,1],[13,1],[14,1],[15,1],[12,2],[13,2],[14,2],[15,2]]
        game_state.attempt_spawn(WALL, funnel)
        game_state.attempt_upgrade(funnel)

    # Extra economy boost late-game
    def build_extra_supports(self, game_state):
        supports = [[13,3],[14,3],[13,4],[14,4],[12,3],[15,3]]
        game_state.attempt_spawn(SUPPORT, supports)
        for loc in supports:
            game_state.attempt_upgrade(loc)

    # Interceptors deployed for general defense
    def spawn_interceptors(self, game_state):
        if game_state.get_resource(MP) >= 2:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

    # Deploys defenses where enemy scored previously
    def reactive_defense(self, game_state):
        for loc in self.scored_on_locations:
            repair = [loc[0], loc[1]+1]
            game_state.attempt_spawn(WALL, repair)
            game_state.attempt_spawn(TURRET, repair)
            game_state.attempt_upgrade(repair)

    # Early-game rush to punish unbuilt defenses
    def cheese_rush(self, game_state):
        spawn_options = [[13,0],[14,0]]
        best_loc = self.best_path_spawn(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_loc, 1000)

    # Emergency turrets and interceptors
    def emergency_defense(self, game_state):
        turrets = [[12,10],[13,10],[14,10],[15,10]]
        for loc in turrets:
            game_state.attempt_spawn(TURRET, loc)
            game_state.attempt_upgrade(loc)
        if game_state.get_resource(MP) >= 3:
            game_state.attempt_spawn(INTERCEPTOR, [13,0], 2)

    # Continuous Scout waves if enemy is weak
    def continuous_scout_pressure(self, game_state):
        spawn_options = [[13,0],[14,0]]
        best_loc = self.best_path_spawn(game_state, spawn_options)
        game_state.attempt_spawn(SCOUT, best_loc, 3)

    # Demolisher attack if enemy has heavy defense
    def demolisher_push_with_funnel(self, game_state):
        funnel = [[6,11],[9,11],[18,11],[21,11]]
        game_state.attempt_spawn(WALL, funnel)
        game_state.attempt_upgrade(funnel)
        game_state.attempt_spawn(DEMOLISHER, [13,0], 1000)

    # Finds safest spawn point based on path damage
    def best_path_spawn(self, game_state, spawn_options):
        damages = []
        for loc in spawn_options:
            path = game_state.find_path_to_edge(loc)
            dmg = 0
            for step in path:
                attackers = game_state.get_attackers(step, 0)
                for u in attackers:
                    dmg += u.damage_i
            damages.append(dmg)
        return spawn_options[damages.index(min(damages))]

    # Utility to detect enemy stationary units
    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total = 0
        for loc in game_state.game_map:
            if game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type):
                        if (valid_x is None or loc[0] in valid_x) and (valid_y is None or loc[1] in valid_y):
                            total += 1
        return total

    # Utility to detect enemy moving units
    def detect_enemy_mobile_units(self, game_state, unit_type):
        count = 0
        for loc in game_state.game_map:
            if not game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    if unit.player_index == 1 and unit.unit_type == unit_type:
                        count += 1
        return count

    # Records where enemy scored during action frame
    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        breaches = state["events"]["breach"]
        for breach in breaches:
            location = breach[0]
            unit_self = True if breach[4] == 1 else False
            if not unit_self:
                gamelib.debug_write(f"Got scored on at: {location}")
                self.scored_on_locations.append(location)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
