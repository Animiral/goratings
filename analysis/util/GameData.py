import sys
from typing import Dict, Iterator

from goratings.interfaces import GameRecord

from .CLI import cli, defaults
from .Config import config
from .EGFGameData import EGFGameData
from .AGAGameData import AGAGameData
from .OGSGameData import OGSGameData
from .SGFGameData import SGFGameData

__all__ = ["GameData", "datasets_used"]

cli.add_argument(
    "--egf", dest="use_egf_data", const=1, default=False, action="store_const", help="Use EGF dataset",
)

cli.add_argument(
    "--ogs", dest="use_ogs_data", const=1, default=False, action="store_const", help="Use OGS dataset",
)

cli.add_argument(
    "--aga", dest="use_aga_data", const=1, default=False, action="store_const", help="Use AGA dataset",
)

cli.add_argument(
    "--all", dest="use_all_data", const=1, default=False, action="store_const", help="Use all datasets",
)

cli.add_argument(
    "--sgf", dest="use_sgf_data", type=str, default=None, help="Directory or list file of custom SGF dataset",
)

cli.add_argument(
    "--games", dest="num_games", type=int, default=0, help="Number of games to process from each dataset, 0 for all",
)

cli.add_argument(
    "--corr", dest="corr", const=1, default=False, action="store_const", help="Only use correspondence games",
)

cli.add_argument(
    "--live", dest="live", const=1, default=False, action="store_const", help="Only use live games",
)

cli.add_argument(
    "--size", dest="size", type=int, default=0, help="Board size to analyze, 0 for all",
)

class GameData:
    quiet: bool
    ogsdata: OGSGameData

    def __init__(self, quiet: bool = False):
        self.quiet = quiet

        size = config.args.size
        speed = 3 if config.args.corr else 2 if config.args.live else 0

        self.ogsdata = OGSGameData(quiet=quiet, size=size, speed=speed)
        self.egfdata = EGFGameData(quiet=quiet)
        self.agadata = AGAGameData(quiet=quiet)
        self.sgfdata = SGFGameData(quiet=quiet, size=size, speed=speed)
        if config.args.use_sgf_data:
            self.sgfdata.add_list_or_dir(config.args.use_sgf_data)

    def __iter__(self) -> Iterator[GameRecord]:
        data_to_use = datasets_used()

        if data_to_use["ogs"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing OGS data\n")
            for entry in self.ogsdata:
                yield entry

        if data_to_use["egf"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing EGF data\n")
            for entry in self.egfdata:
                yield entry

        if data_to_use["aga"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing AGA data\n")
            for entry in self.agadata:
                yield entry

        if data_to_use["sgf"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing SGF data\n")
            for entry in self.sgfdata:
                yield entry


def datasets_used() -> Dict[str, bool]:
    ret = {
        "egf": config.args.use_all_data or config.args.use_egf_data,
        "ogs": config.args.use_all_data or config.args.use_ogs_data,
        "aga": config.args.use_all_data or config.args.use_aga_data,
        "sgf": bool(config.args.use_sgf_data),
    }
    if not ret["egf"] and not ret["ogs"] and not ret['aga'] and not ret['sgf']:
        ret[defaults["data"]] = True

    if config.args.size and config.args.size != 19:
        ret['egf'] = False
        ret['aga'] = False

    return ret
