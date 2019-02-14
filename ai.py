# -*- coding: utf-8 -*-

# python imports
import random

# chillin imports
from chillin_client import RealtimeAI

# project imports
from ks.models import (World, Police, Terrorist, Bomb, Position, Constants,
                       ESoundIntensity, ECell, EAgentStatus)
from ks.commands import DefuseBomb, PlantBomb, Move, ECommandDirection


class AI(RealtimeAI):

    def __init__(self, world):
        super(AI, self).__init__(world)
        self.done = False


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
        sorted_bombs_list = self.get_sorted_bombs_list(self, self.world.polices[0].position, -1)

    def get_sorted_bombs_list(self, source, number):  # finds nearest bombs from the source position
        import queue
        bombs_list = [] # [position]
        checked = []
        Q = queue.Queue()
        Q.put(source)
        adjs = [[-1,-1],
                [+1,-1],
                [-1,+1],
                [+1,+1]]

        while not Q.empty() and (len(bombs_list) < number or number == -1):
            node = Q.get() # bfs is checking for bombs from the source to board edges ...
            checked.append(node)
            if self.is_bomb(node):
                bombs_list.append(node)
            for adj in adjs:
                newNode = Position(x=node.x + adj[0], y=node.y + adj[1])
                if newNode not in checked and self.check_empty_node(newNode):
                    Q.put(newNode)

        return bombs_list


    def cover_bombsite(self, sorted_bombs_list, ratio):  # defines each bomb is covered by each police
        pass

    def police_move(self):
        pass

    def police_defuse(self):
        pass

    def police_escape(self):
        pass

    def police_patrol(self):
        pass

    def check_empty_node(self, node): #check existance of this node and emptyness

        #check for existance
        if node.x < 0 or node.x >= self.world.width:
            return False
        if node.y < 0 or node.y >= self.world.height:
            return False

        #check for emptyness
        node_content = self.world.board[node.y][node.x]
        if node_content == ECell.Empty:
            return True

        return False


    def is_bomb(self, node):
        node_content = self.world.board[node.y][node.x]
        if node_content != ECell.Empty and node_content != ECell.Wall:
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


