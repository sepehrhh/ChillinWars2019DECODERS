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
    def __init__(self,_bombsites = [],_police = None):
        self.bombSites = _bombsites
        self.police = _police
        self.police_current_target_index = None if _bombsites == [] else random.randint(0,len(_bombsites) - 1)

class EPoliceState(Enum):
    PatrolInRegion = 0
    DefusingBomb = 1
    EscapingBomb = 2


class AI(RealtimeAI):

    def __init__(self, world):
        super(AI, self).__init__(world)
        self.done = False
        self.police_regions = []



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
            pass
        # my_agents = self.world.polices if self.my_side == 'Police' else self.world.terrorists
        # for agent in my_agents:
        #     if agent.status == EAgentStatus.Dead:
        #         continue
        #
        #     doing_bomb_operation = agent.defusion_remaining_time != -1 if self.my_side == 'Police' else agent.planting_remaining_time != -1
        #
        #     if doing_bomb_operation:
        #         self._agent_print(agent.id, 'Continue Bomb Operation')
        #         continue
        #
        #     bombsite_direction = self._find_bombsite_direction(agent)
        #     if bombsite_direction == None:
        #         self._agent_print(agent.id, 'Random Move')
        #         self.move(agent.id, random.choice(self._empty_directions(agent.position)))
        #     else:
        #         self._agent_print(agent.id, 'Start Bomb Operation')
        #         if self.my_side == 'Police':
        #             self.defuse(agent.id, bombsite_direction)
        #         else:
        #             self.plant(agent.id, bombsite_direction)

    def police_action(self):
        if self.police_regions == [] or self.current_cycle % 30 == 0:
            self.make_regions()

            #for region in self.police_regions:
                # print(region.police,len(region.bombSites),region.police_current_target_index)

        # print("\n------regions totally made-----\n")
        self.police_proccess_regions()


    def police_proccess_regions(self):
        for region in self.police_regions:
            if region.police == None:
                continue
            target = self.choose_current_target(region) # position
            police = region.police
            self.police_move(police, target)


    def choose_current_target(self, region): #keep or change current target according to self.police_current_target

        for p in self.world.polices:
            if p.id == region.police.id:
                region.police = p

        if self.find_dist(region.police.position, region.bombSites[region.police_current_target_index]) < 2 :
            region.police_current_target_index += 1
            region.police_current_target_index %= len(region.bombSites)
        return region.bombSites[region.police_current_target_index]


    def find_dist(self, policePos, bombPos):

        posQ = queue.Queue()
        posQ.put(policePos)
        distQ = queue.Queue()
        distQ.put(0)
        checked = set()
        adjs = [[ 0,-1],
                [ 0,+1],
                [-1, 0],
                [+1, 0]]

        policesPos = [(police.position.x, police.position.y) for police in self.world.polices]

        while not posQ.empty():
            node = posQ.get()
            dist = distQ.get()

            if (node.x, node.y) in checked:
                continue
            if (node.x, node.y) in policesPos and (node.x, node.y) != (policePos.x, policePos.y) :
                continue

            checked.add((node.x, node.y))

            for adj in adjs:
                new_node = Position(x=node.x + adj[0], y=node.y + adj[1])

                if (new_node.x, new_node.y) == (bombPos.x, bombPos.y):
                    return dist + 1

                elif self.check_empty_node(new_node) and not self.is_bomb(new_node):
                    posQ.put(new_node)
                    distQ.put(dist + 1)

        # print("could find a way ...100000")
        return 100000

    def make_regions(self):

        sorted_bombs_list = self.get_sorted_bombs_list(self.world.polices[0].position, 120)

        sorted_bombs_list.reverse()
        # print("\n\n\n\n print below \n")
        # for i in sorted_bombs_list:
        #     print(len(sorted_bombs_list),i.x,i.y)
        # print("\n\n\n\n\n")

        all_bombs = len(sorted_bombs_list)

        #i so goshad to check the state that ratio is 0 so i add 1
        checked = set()
        polices_queue = self.alive_polices_queue()

        for bomb in sorted_bombs_list:
            if (bomb.x, bomb.y) in checked :
                continue

            ratio = all_bombs // polices_queue.qsize()
            if (all_bombs / polices_queue.qsize()) % 1 != 0:
                ratio += 1

            region_bombs = self.get_sorted_bombs_list(bomb, ratio , checked = checked.copy(), verifiedBobms = sorted_bombs_list)
            region = PoliceRegion(region_bombs)
            if not polices_queue.empty():
                region.police = polices_queue.get()
                all_bombs -= len(region_bombs)
            for applied_bomb in region_bombs:
                checked.add((applied_bomb.x, applied_bomb.y))
            self.police_regions.append(region)



    def alive_polices_queue(self):
        q = queue.Queue()
        for police in self.world.polices:
            if police.status == EAgentStatus.Alive:
               q.put(police)
        return q


    def get_sorted_bombs_list(self, source, number, checked = set() , verifiedBobms = None):  # finds nearest bombs from the source position
        bombs_list = []  # [position]
        if verifiedBobms is not None:
            verifiedBobms = {(b.x,b.y) for b in verifiedBobms}
        Q = queue.Queue()
        Q.put(source)
        adjs = [[0, -1],
                [0, +1],
                [-1, 0],
                [+1, 0]]

        while not Q.empty() and len(bombs_list) < number:

            node = Q.get()  # bfs is checking for bombs from the source to board edges ...

            if (node.x, node.y) in checked:
                continue

            checked.add((node.x, node.y))

            if verifiedBobms is not None:
                if (node.x, node.y) in verifiedBobms:
                    bombs_list.append(node)
                    if (node.x, node.y) != (source.x, source.y):
                        continue


            elif self.is_bomb(node):
                bombs_list.append(node)
                if (node.x, node.y) != (source.x, source.y):
                    continue   # cause we cant see pass the bomb so we dont see its adjs

            for adj in adjs:
                new_node = Position(x=node.x + adj[0], y=node.y + adj[1])
                if self.check_empty_node(new_node):
                    Q.put(new_node)

        return bombs_list

    def cover_bombsite(self, sorted_bombs_list, ratio):  # defines each bomb is covered by each police
        pass

    def police_move(self, police, target):

        id = police.id

        for p in self.world.polices:
            if p.id == id:
                police = p

        pos = police.position

        # print("police {} from ({} , {}) is going to ({} , {})".format(police.id, pos.x, pos.y, target.x, target.y))

        dist = self.find_dist(pos, target)

        polices_pos = [(p.position.x, p.position.y) for p in self.world.polices]


        node = Position(pos.x, pos.y + 1)
        nodetup = (node.x,node.y)

        if self.check_empty_node(node) and not self.is_bomb(node) and nodetup not in polices_pos and self.find_dist(node, target) + 1 == dist:
            # print(police.id, "Down" ,self.find_dist(node, target) , "<" ,dist , self.check_empty_node(node) , (node.x , node.y))
            self.move(police.id,  ECommandDirection.Down)
            return


        node = Position(pos.x + 1, pos.y)
        nodetup = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and nodetup not in polices_pos and self.find_dist(node, target) + 1 == dist:
            # print(police.id, "Right" ,self.find_dist(node, target) , "<" ,dist , self.check_empty_node(node) , (node.x , node.y))
            self.move(police.id, ECommandDirection.Right)
            return

        node = Position(pos.x, pos.y - 1)
        nodetup = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and nodetup not in polices_pos and self.find_dist(node, target) + 1 == dist:
            # print(police.id, "Up" ,self.find_dist(node, target) , "<" ,dist , self.check_empty_node(node) , (node.x , node.y))
            self.move(police.id, ECommandDirection.Up)
            return


        node = Position(pos.x - 1, pos.y)
        nodetup = (node.x, node.y)
        if self.check_empty_node(node) and not self.is_bomb(node) and nodetup not in polices_pos and self.find_dist(node, target) + 1 == dist:
            # print(police.id, "Left" ,self.find_dist(node, target) , "<" ,dist , self.check_empty_node(node) , (node.x , node.y))
            self.move(police.id, ECommandDirection.Left)
            return

        # print("couldnt find a way")





    def police_defuse(self):
        pass

    def police_escape(self):
        pass

    def police_patrol(self):
        pass

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
