# -*- coding: utf-8 -*-

# python imports
import random
from enum import Enum
import queue
# chillin imports
from chillin_client import RealtimeAI

# project imports
from ks.models import (World, Police, Terrorist, Bomb, Position, Constants,
                       ESoundIntensity, ECell, EAgentStatus)
from ks.commands import DefuseBomb, PlantBomb, Move, ECommandDirection


class PoliceRegion:
    def __init__(self, _bombsites=[], _police=None):
        self.bombSites = _bombsites
        self.police = _police
        self.police_current_target_index = None if _bombsites == [] else random.randint(0,len(_bombsites) - 1)


class TerroristRegion:
    def __init__(self, _bombsites=[], _terrorist=None):
        self.bombSites = _bombsites
        self.terrorist = _terrorist
        self.terrorist_current_target_index = None if _bombsites == [] else random.randint(0, len(_bombsites) - 1)


class EPoliceState(Enum):
    PatrolInRegion = 0
    DefusingBomb = 1
    EscapingBomb = 2


class AI(RealtimeAI):

    def __init__(self, world):
        super(AI, self).__init__(world)
        self.done = False
        self.police_regions = []
        self.terrorist_regions = []
        self.polices_assigned_bombs = dict()
        self.planting_terrorist_ids = []
        self.targeted_bombs = set()
        self.DIRECTION = [[0, -1], [0, +1], [-1, 0], [+1, 0]]


    def initialize(self):
        print('initialize')

        self.DIRECTIONS = [
            ECommandDirection.Up,
            ECommandDirection.Right,
            ECommandDirection.Down,
            ECommandDirection.Left,
        ]

        self.DIR_TO_POS = {
            ECommandDirection.Up:    (+0, -1),
            ECommandDirection.Right: (+1, +0),
            ECommandDirection.Down:  (+0, +1),
            ECommandDirection.Left:  (-1, +0),
        }

        self.BOMBSITES_ECELL = [
            ECell.SmallBombSite,
            ECell.MediumBombSite,
            ECell.LargeBombSite,
            ECell.VastBombSite,
        ]

    def decide(self):
        print('decide')
        if self.my_side == 'Police':
            self.police_action()
        else:
            self.terrorist_action()


    def police_action(self):
        if not self.police_regions or self.current_cycle % 30 == 0:
            self.make_regions()

        self.police_defuse_process()
        self.police_process_move()


    def terrorist_action(self):
        if not self.terrorist_regions or self.current_cycle % 30 == 0:
            self.make_regions()

        self.terrorist_plant_process()
        self.terrorist_process_move()


    def police_process_move(self):
        for police_region in self.police_regions:
            if police_region.police is None:
                continue
            if police_region.police.id in self.polices_assigned_bombs:
                continue
            police = self.police_with_id(police_region.police.id)
            doing_bomb_operation = police.defusion_remaining_time != -1
            if doing_bomb_operation:
                print("police : {} is doing bomb op".format(police.id))
                continue
            target = self.choose_current_target(police_region)  # sets target position
            police = police_region.police
            self.agents_move(police, target)


    def police_with_id(self, id_):
        for p in self.world.polices:
            if p.id == id_:
                return p


    def terrorist_process_move(self):
        for terrorist_region in self.terrorist_regions:
            if terrorist_region.terrorist is None:
                continue
            if terrorist_region.terrorist.id in self.planting_terrorist_ids:
                continue
            terrorist = self.terrorist_with_id(terrorist_region.terrorist.id)
            doing_bomb_operation = terrorist.planting_remaining_time != -1
            if doing_bomb_operation:
                print("terrorist : {} is doing bomb op".format(terrorist.id))
                continue
            target = self.choose_current_target(terrorist_region)  # sets target position
            terrorist = terrorist_region.terrorist
            self.agents_move(terrorist, target)


    def terrorist_with_id(self, id_):
        for t in self.world.terrorists:
            if t.id == id_:
                return t


    def choose_current_target(self, region):  # keep or change current target according to self.police_current_target
        if self.my_side == 'Police':
            region.police = self.police_with_id(region.police.id)

            if self.find_dist(region.police.position, region.bombSites[region.police_current_target_index]) < 2:
                region.police_current_target_index += 1
                region.police_current_target_index %= len(region.bombSites)
            return region.bombSites[region.police_current_target_index]
        else:
            region.terrorist = self.terrorist_with_id(region.terrorist.id)

            if self.find_dist(region.terrorist.position, region.bombSites[region.terrorist_current_target_index]) < 2:
                region.terrorist_current_target_index += 1
                region.terrorist_current_target_index %= len(region.bombSites)
            return region.bombSites[region.terrorist_current_target_index]


    def find_dist(self, agent_pos, bomb_pos):

        position_queue = queue.Queue()
        position_queue.put(agent_pos)
        dist_queue = queue.Queue()
        dist_queue.put(0)
        checked = set()

        adjacency = [[0, -1], [0, +1], [-1, 0], [+1, 0]]

        if self.my_side == 'Police':
            agents_pos = [(police.position.x, police.position.y) for police in self.world.polices]
        else:
            agents_pos = [(terrorist.position.x, terrorist.position.y) for terrorist in self.world.terrorists]

        while not position_queue.empty():
            node = position_queue.get()
            dist = dist_queue.get()

            if (node.x, node.y) in checked:
                continue
            if (node.x, node.y) in agents_pos and (node.x, node.y) != (agent_pos.x, agent_pos.y):
                continue

            checked.add((node.x, node.y))

            for adj in adjacency:
                new_node = Position(x=node.x + adj[0], y=node.y + adj[1])

                if (new_node.x, new_node.y) == (bomb_pos.x, bomb_pos.y):
                    return dist + 1

                elif self.check_empty_node(new_node) and not self.is_bomb(new_node):
                    position_queue.put(new_node)
                    dist_queue.put(dist + 1)

        return 100000


    def make_regions(self):

        if self.my_side == 'Police':
            rand_police = self.world.polices[random.randint(0, len(self.world.polices) - 1)]
            sorted_bombs_list = self.get_sorted_bombs_list(self.world.polices[0].position, 120)
        else:
            rand_terrorist = self.world.terrorists[random.randint(0, len(self.world.terrorists) - 1)]
            sorted_bombs_list = self.get_sorted_bombs_list(self.world.terrorists[0].position, 120)
        random.shuffle(sorted_bombs_list)
        sorted_bombs_list.reverse()
        all_bombs_num = len(sorted_bombs_list)
        checked = set()
        if self.my_side == 'Police':
            polices_queue = self.alive_polices_queue()
            for bomb in sorted_bombs_list:
                if (bomb.x, bomb.y) in checked:
                    continue

                ratio = all_bombs_num // polices_queue.qsize()
                if (all_bombs_num / polices_queue.qsize()) % 1 != 0:
                    ratio += 1

                region_bombs = self.get_sorted_bombs_list(bomb, ratio, checked=checked.copy(), verified_bombs=sorted_bombs_list)
                police_region = PoliceRegion(region_bombs)
                if not polices_queue.empty():
                    police_region.police = polices_queue.get()
                    all_bombs_num -= len(region_bombs)
                for applied_bomb in region_bombs:
                    checked.add((applied_bomb.x, applied_bomb.y))
                self.police_regions.append(police_region)

        else:
            terrorists_queue = self.alive_terrorists_queue()
            for bomb in sorted_bombs_list:
                if (bomb.x, bomb.y) in checked:
                    continue

                ratio = all_bombs_num // terrorists_queue.qsize()
                if (all_bombs_num / terrorists_queue.qsize()) % 1 != 0:
                    ratio += 1

                region_bombs = self.get_sorted_bombs_list(bomb, ratio, checked=checked.copy(),
                                                          verified_bombs=sorted_bombs_list)
                terrorist_region = TerroristRegion(region_bombs)
                if not terrorists_queue.empty():
                    terrorist_region.terrorist = terrorists_queue.get()
                    all_bombs_num -= len(region_bombs)
                for applied_bomb in region_bombs:
                    checked.add((applied_bomb.x, applied_bomb.y))
                self.terrorist_regions.append(terrorist_region)


    def alive_polices_queue(self):
        q = queue.Queue()
        for police in self.world.polices:
            if police.status == EAgentStatus.Alive:
               q.put(police)
        return q


    def alive_terrorists_queue(self):
        terrorists_queue = queue.Queue()
        for terrorist in self.world.terrorists:
            if terrorist.status == EAgentStatus.Alive:
               terrorists_queue.put(terrorist)

        return terrorists_queue


    def get_nearest_unassigned_agent(self, source):
        checked = set()
        adjacency = [[0, -1], [0, +1], [-1, 0], [+1, 0]]
        if self.my_side == 'Police':
            agents_pos = {(police.position.x, police.position.y): police.id for police in self.world.polices}
        else:
            agents_pos = {(terrorist.position.x, terrorist.position.y): terrorist.id for terrorist in self.world.terrorists}
        q = queue.Queue()
        q.put(source)

        while not q.empty():
            node = q.get()
            if (node.x, node.y) in checked:
                continue
            checked.add((node.x, node.y))

            if (node.x, node.y) in agents_pos:
                if self.my_side == 'Police':
                    if agents_pos[(node.x, node.y)] not in self.polices_assigned_bombs:
                        return agents_pos[(node.x, node.y)]
                    continue
                else:
                    if agents_pos[(node.x, node.y)] not in self.terrorists_assigned_bombs:
                        return agents_pos[(node.x, node.y)]
                    continue

            for adj in adjacency:
                new_node = Position(x=node.x + adj[0], y=node.y + adj[1])

                if self.check_empty_node(new_node) and not self.is_bomb(new_node):
                    q.put(new_node)


    def get_sorted_bombs_list(self, source, number, checked=None, verified_bombs=None):
        if checked is None:
            checked = set()
        bombs_list = []  # [position]
        if verified_bombs is not None:
            verified_bombs = {(b.x, b.y) for b in verified_bombs}
        q = queue.Queue()
        q.put(source)
        adjs = [[0, -1],
                [0, +1],
                [-1, 0],
                [+1, 0]]

        while not q.empty() and len(bombs_list) < number:

            node = q.get()  # bfs is checking for bombs from the source to board edges ...

            if (node.x, node.y) in checked:
                continue

            checked.add((node.x, node.y))

            if verified_bombs is not None:
                if (node.x, node.y) in verified_bombs:
                    bombs_list.append(node)
                    if (node.x, node.y) != (source.x, source.y):
                        continue

            elif self.is_bomb(node):
                bombs_list.append(node)
                if (node.x, node.y) != (source.x, source.y):
                    continue   # cause we cant see pass the bomb so we do not see its adjacent

            for adj in adjs:
                new_node = Position(x=node.x + adj[0], y=node.y + adj[1])
                if self.check_empty_node(new_node):
                    q.put(new_node)

        return bombs_list


    def cover_bombsite(self, sorted_bombs_list, ratio):  # defines each bomb is covered by each police
        pass


    def agents_move(self, agent, target):

        if self.my_side == 'Police':
            agent = self.police_with_id(agent.id)
        else:
            agent = self.terrorist_with_id(agent.id)

        pos = agent.position
        dist = self.find_dist(pos, target)
        if self.my_side == 'Police':
            agents_pos = [(p.position.x, p.position.y) for p in self.world.polices]
        else:
            agents_pos = [(t.position.x, t.position.y) for t in self.world.terrorists]

        node = Position(pos.x, pos.y + 1)
        node_tuple = (node.x, node.y)

        if self.check_empty_node(node) and not self.is_bomb(node) and node_tuple not in agents_pos and self.find_dist(node, target) + 1 == dist:
            self.move(agent.id, ECommandDirection.Down)
            return

        node = Position(pos.x + 1, pos.y)
        node_tuple = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and node_tuple not in agents_pos and self.find_dist(node, target) + 1 == dist:
            self.move(agent.id, ECommandDirection.Right)
            return

        node = Position(pos.x, pos.y - 1)
        node_tuple = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and node_tuple not in agents_pos and self.find_dist(node, target) + 1 == dist:
            self.move(agent.id, ECommandDirection.Up)
            return

        node = Position(pos.x - 1, pos.y)
        node_tuple = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and node_tuple not in agents_pos and self.find_dist(node, target) + 1 == dist:
            self.move(agent.id, ECommandDirection.Left)
            return


    def assign_bombs(self):
        for bomb in self.world.bombs:
            print("bomb founded")
            bomb_node = (bomb.position.x, bomb.position.y)
            if bomb_node in self.targeted_bombs:
                continue

            agent_id = self.get_nearest_unassigned_agent(bomb.position)
            if agent_id is None:
                continue
            print("bomb in ({},{}) assigned to agent : {}".format(bomb.position.x, bomb.position.y, agent_id))

            self.polices_assigned_bombs[agent_id] = bomb
            self.targeted_bombs.add(bomb_node)


    def police_defuse_process(self):

        self.assign_bombs()

        removing_bombs = []
        removing_ids = []

        for police_id, bomb in self.polices_assigned_bombs.items():
            police = self.police_with_id(police_id)
            bombsite_direction = self._find_bombsite_direction(police)

            can_defuse = self.can_defuse(police, bomb)

            if not can_defuse:
                removing_bombs.append((bomb.position.x, bomb.position.y))
                removing_ids.append(police_id)
                continue

            if self.find_dist(police.position, bomb.position) > 1:  # still move to bomb
                self.agents_move(police, bomb.position)

            elif bombsite_direction is not None:

                doing_bomb_operation = police.defusion_remaining_time != -1
                if doing_bomb_operation:
                    if police_id in self.polices_assigned_bombs:
                        removing_bombs.append((bomb.position.x, bomb.position.y))
                        removing_ids.append(police_id)
                    continue

                self._agent_print(police, 'Start Bomb Operation')
                self.defuse(police.id, bombsite_direction)

        for id_ in removing_ids:
            del self.polices_assigned_bombs[id_]

        for bomb_ in removing_bombs:
            self.targeted_bombs.remove(bomb_)


    def can_defuse(self, police, bomb):  # should assess if poice can defuse bomb or not
        arriving_time = self.find_dist(police.position, bomb.position) * self.cycle_duration + 0.2

        return arriving_time + self.world.constants.bomb_defusion_time < bomb.explosion_remaining_time


    def terrorist_plant_process(self):
        for terrorist in self.world.terrorists:
            if terrorist.id in self.planting_terrorist_ids:
                if terrorist.planting_remaining_time == -1:
                    self.planting_terrorist_ids.remove(terrorist.id)
                continue
            bombsite_direction = self._find_bombsite_direction(terrorist)

            if self._find_bombsite_direction(terrorist) is not None:
                self._agent_print(terrorist, 'Start Bomb Operation')
                self.planting_terrorist_ids.append(terrorist.id)
                self.plant(terrorist.id, bombsite_direction)


    def check_empty_node(self, node):  # check existance of this node and emptyness

        # check for existance
        if node.x < 0 or node.x >= self.world.width:
            return False
        if node.y < 0 or node.y >= self.world.height:
            return False

        # check for emptyness
        node_content = self.world.board[node.y][node.x]
        if node_content != ECell.Wall:
            return True

        return False


    def is_bomb(self, node):
        node_content = self.world.board[node.y][node.x]
        if node_content != ECell.Wall and node_content != ECell.Empty:
            return True
        return False


    def plant(self, agent_id, bombsite_direction):
        self.send_command(PlantBomb(id=agent_id, direction=bombsite_direction))


    def defuse(self, agent_id, bombsite_direction):
        self.send_command(DefuseBomb(id=agent_id, direction=bombsite_direction))


    def move(self, agent_id, move_direction):
        self.send_command(Move(id=agent_id, direction=move_direction))


    def _empty_directions(self, position):
        empty_directions = []

        for direction in self.DIRECTIONS:
            pos = self._sum_pos_tuples((position.x, position.y), self.DIR_TO_POS[direction])
            if self.world.board[pos[1]][pos[0]] == ECell.Empty:
                empty_directions.append(direction)
        return empty_directions


    def _find_bombsite_direction(self, agent):
        for direction in self.DIRECTIONS:
            pos = self._sum_pos_tuples((agent.position.x, agent.position.y), self.DIR_TO_POS[direction])
            if self.world.board[pos[1]][pos[0]] in self.BOMBSITES_ECELL:
                has_bomb = self._has_bomb(pos)
                if (self.my_side == 'Police' and has_bomb) or (self.my_side == 'Terrorist' and not has_bomb):
                    return direction
        return None


    def _has_bomb(self, position):
        for bomb in self.world.bombs:
            if position[0] == bomb.position.x and position[1] == bomb.position.y:
                return True
        return False


    def _sum_pos_tuples(self, t1, t2):
        return (t1[0] + t2[0], t1[1] + t2[1])


    def _agent_print(self, agent_id, text):
        print('Agent[{}]: {}'.format(agent_id, text))
