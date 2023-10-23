import os
import sys
from time import time
import re
from sgfmill import sgf
from typing import Iterator

from goratings.interfaces import GameRecord

__all__ = ["SGFGameData"]

canadian_pattern = re.compile(r'(\d+)/(\d+) Canadian')
fischer_pattern = re.compile(r'(\d+) fischer')
byoyomi_pattern = re.compile(r'(\d+)x(\d+) byo-yomi')
simple_pattern = re.compile(r'(\d+) simple')
valid_result_pattern = re.compile(r'[wWbB]\+[TR\d]')

def sec_per_move(overtime):
    """Determine seconds per move from the overtime specification."""

    match = canadian_pattern.search(overtime)
    if match:
        stones, time = map(int, match.groups())
        return time/stones

    match = fischer_pattern.search(overtime)
    if match:
        time_increment = int(match.group(1))
        return time_increment

    match = byoyomi_pattern.search(overtime)
    if match:
        periods, period_time = map(int, match.groups())
        return period_time

    match = simple_pattern.search(overtime)
    if match:
        time = int(match.group(1))
        return time

    return None

class SGFGameData:
    """Read games from SGF files"""
    quiet: bool  # print diagnostic or not
    size: int    # filter by board size
    speed: int   # filter by sec per move
    data: list[GameRecord]  # SGF metadata
    players: dict[str, int]  # players mapped to IDs as we encounter them

    def __init__(self, quiet: bool = False, size: int = 0, speed: int = 0) -> None:
        self.quiet = quiet
        self.size = size
        self.speed = speed
        self.data = []
        self.players = {}

    def add_file(self, file, result="") -> None:
        with open(file, "rb") as f:
            game = sgf.Sgf_game.from_bytes(f.read())

        def get_or_default(sgf_node, identifier, default):
            if sgf_node.has_property(identifier):
                return sgf_node.get(identifier)
            else:
                return default

        root_node = game.get_root()
        player_white = root_node.get('PW')
        player_black = root_node.get('PB')
        if "" == result:
            result = get_or_default(root_node, 'RE', '')
        size = root_node.get('SZ')
        handicap = int(get_or_default(root_node, 'HA', 0))
        komi = root_node.get('KM')
        time = root_node.get('TM')
        overtime = get_or_default(root_node, 'OT', None)
        time_per_move = sec_per_move(overtime)

        # filters
        if self.size and size != self.size:
            return
        if self.speed:
            if self.speed >= 3:
                if time_per_move > 0 and time_per_move <= 3600:
                    return
            else:
                if time_per_move == 0 or time_per_move >= 3600:
                    return

        game_id = len(self.data)  # sequential, also use as ending timestamp
        if player_black in self.players:
            black_id = self.players[player_black]
        else:
            black_id = len(self.players)
            self.players[player_black] = black_id
        if player_white in self.players:
            white_id = self.players[player_white]
        else:
            white_id = len(self.players)
            self.players[player_white] = white_id

        if 'B' in result:
            winner_id = black_id
        elif 'W' in result:
            winner_id = white_id
        else:
            winner_id = -1

        record = GameRecord(
            # id, size, handicap, komi, black_id, white_id, time_per_move, timeout, winner_id, ended
            game_id, size, handicap, komi, black_id, white_id, time_per_move, 'T' in result, winner_id, game_id
        )
        self.data.append(record)

    def add_list_or_dir(self, path):
        """
        Given the path (from command line args), read the specified SGF files.
        If path points to a text file, read each line as the path to an SGF.
        If the file is in CSV format,
            - skip the first line (title row) and
            - use the last column as result string instead of the SGF RE[].
        If path points to a directory, traverse it recursively and add all SGF files found.
        """
        if os.path.isfile(path):
            with open(path, "r") as f:
                firstline = True
                while True:
                    line = f.readline()
                    if "" == line:
                        break
                    comma = line.find(',')
                    if -1 == comma:
                        self.add_file(line)
                    else:
                        if firstline:
                            firstline = False
                            continue
                        lastcomma = line.rfind(',')
                        self.add_file(line[:comma], line[lastcomma+1:])  # override game result
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(directory):
                files.sort() # naming convention must establish order in time

                for filename in files:
                    if filename.endswith('.sgf'):
                        path = os.path.join(root, filename)
                        self.add_file(path)


    def __iter__(self) -> Iterator[GameRecord]:
        return self.data.__iter__()
