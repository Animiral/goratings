import argparse
from math import exp, log, sqrt
from typing import Callable, Dict, Union, List

from .CLI import cli, defaults

__all__ = [
    "rank_to_rating",
    "rating_to_rank",
    "get_handicap_adjustment",
    "rating_config",
    "set_optimizer_rating_points",
    "set_exhaustive_log_parameters",
]


cli.add_argument(
    "--ranks",
    type=str,
    dest="ranks",
    choices=("log", "logp", "linear", "optimizer", "gor", "sig", "auto"),
    default="auto",
    help="Use logarithmic, linear, or GoR ranking",
)

#A = 850
#C = 32.25
#A = 478
#C = 21.9
A = 525
C = 23.15
D = 0
P = 1
HALF_STONE_HANDICAP = False
HALF_STONE_HANDICAP_FOR_ALL_RANKS = False

cli.add_argument(
    "--half-stone-handicap", dest="half_stone_handicap", const=1, default=False, action="store_const", help="Use a 0.5 rank adjustment for hc1",
)
cli.add_argument(
    "--half-stone-handicap-for-all-ranks", dest="half_stone_handicap_for_all_ranks", const=1, default=False, action="store_const", help="use rankdiff -0.5 for handicap",
)

logarithmic = cli.add_argument_group(
    "logarithmic ranking variables", "rating to ranks converted with `(log(rating / a) ** p) * c + d`",
)
logarithmic.add_argument("-a", dest="a", type=float, default=525.0, help="a")
logarithmic.add_argument("-c", dest="c", type=float, default=23.15, help="c")
logarithmic.add_argument("-d", dest="d", type=float, default=0.0, help="d")
logarithmic.add_argument("-p", dest="p", type=float, default=1.0, help="p")

linear = cli.add_argument_group("linear ranking variables", "rating to ranks converted with `rating / m + b`")
linear.add_argument("-m", dest="m", type=float, default=100.0, help="m")
linear.add_argument("-b", dest="b", type=float, default=9.0, help="b")


_rank_to_rating: Callable[[float], float]
_rating_to_rank: Callable[[float], float]
rating_config: Dict[str, Union[str, float]] = {}
optimizer_rating_control_points: List[float]


def rank_to_rating(rank: float) -> float:
    return _rank_to_rating(rank)


def rating_to_rank(rating: float) -> float:
    return _rating_to_rank(rating)

def set_exhaustive_log_parameters(a: float, c:float, d:float, p:float = 1.0) -> None:
    global A
    global C
    global D
    global P
    A = a
    C = c
    D = d
    P = p

def get_handicap_adjustment(rating: float, handicap: int) -> float:
    global HALF_STONE_HANDICAP
    global HALF_STONE_HANDICAP_FOR_ALL_RANKS
    if HALF_STONE_HANDICAP_FOR_ALL_RANKS:
        return rank_to_rating(rating_to_rank(rating) + (handicap - 0.5 if handicap > 0 else 0)) - rating
    if HALF_STONE_HANDICAP:
        return rank_to_rating(rating_to_rank(rating) + (0.5 if handicap == 1 else handicap)) - rating
    return rank_to_rating(rating_to_rank(rating) + handicap) - rating

def set_optimizer_rating_points(points: List[float]) -> None:
    global optimizer_rating_control_points
    optimizer_rating_control_points = points

def configure_rating_to_rank(args: argparse.Namespace) -> None:
    global _rank_to_rating
    global _rating_to_rank
    global optimizer_rating_control_points
    global A
    global C
    global D
    global HALF_STONE_HANDICAP
    global HALF_STONE_HANDICAP_FOR_ALL_RANKS

    HALF_STONE_HANDICAP = args.half_stone_handicap
    HALF_STONE_HANDICAP_FOR_ALL_RANKS = args.half_stone_handicap_for_all_ranks
    system: str = args.ranks
    a: float = args.a
    c: float = args.c
    d: float = args.d
    m: float = args.m
    b: float = args.b
    p: float = args.p

    if system == "auto":
        system = defaults["ranking"]

    rating_config["system"] = system


    if system == "linear":

        def __rank_to_rating(rank: float) -> float:
            return (rank - b) * m

        def __rating_to_rank(rating: float) -> float:
            return (rating / m) + b

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["b"] = b
        rating_config["m"] = m
    elif system == "optimizer":

        def __rank_to_rating(rank: float) -> float:
            base = min(37, max(0, int(rank)))
            a = rank - base

            return lerp(
                optimizer_rating_control_points[base],
                optimizer_rating_control_points[base + 1],
                a
            )

        def __rating_to_rank(rating: float) -> float:
            if rating < optimizer_rating_control_points[0]:
                return 0
            for rank in range(1, 38):
                if rating < optimizer_rating_control_points[rank]:
                    return lerp(
                        rank-1,
                        rank,
                        (rating - optimizer_rating_control_points[rank - 1]) /
                        (optimizer_rating_control_points[rank] - optimizer_rating_control_points[rank - 1])
                    )

            return 39

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank

    elif system == "gor":

        def __rank_to_rating(rank: float) -> float:
            return (rank - 9) * 100

        def __rating_to_rank(rating: float) -> float:
            return (rating / 100.0) + 9

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["b"] = 9
        rating_config["m"] = 100
    elif system == "exhaustivelog":

        def __rank_to_rating(rank: float) -> float:
            return A * exp((rank - D) / C)

        def __rating_to_rank(rating: float) -> float:
            return log(rating / A) * C + D

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["d"] = D
        rating_config["c"] = C
        rating_config["a"] = A

    elif system == "exhaustivelogp":

        def __rank_to_rating(rank: float) -> float:
            if rank < 0:
                rank = 0
            return A * exp(((rank) / C) ** (1/P))

        def __rating_to_rank(rating: float) -> float:
            if rating < A:
                rating = A
            return (log(rating / A) ** P) * C

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["p"] = P
        rating_config["c"] = C
        rating_config["a"] = A

    elif system == "log":

        def __rank_to_rating(rank: float) -> float:
            return a * exp((rank - d) / c)

        def __rating_to_rank(rating: float) -> float:
            return log(rating / a) * c + d

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["d"] = d
        rating_config["c"] = c
        rating_config["a"] = a

    elif system == "logp":

        def __rank_to_rating(rank: float) -> float:
            if rank < 0:
                rank = 0
            return a * exp(((rank) / c) ** (1/p))

        def __rating_to_rank(rating: float) -> float:
            if rating < a:
                rating = a
            return (log(rating / a) ** p) * c

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["p"] = p
        rating_config["c"] = c
        rating_config["a"] = a

    elif system == "sig":
        inflection = 1500
        def f(rating):
            return log(rating / a) * c
        def i(rank):
            return a * exp(rank / c)

        def __rank_to_rating(rank: float) -> float:
            if rank >= f(inflection):
                return i(rank)
            base = f(inflection)
            d = base - rank
            return i(base) * 2 - i(base + d)

        def __rating_to_rank(rating: float) -> float:
            if rating >= inflection:
                return f(rating)
            d = inflection - rating
            return f(inflection) * 2 - f(inflection + d)

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
        rating_config["c"] = c
        rating_config["a"] = a
    else:
        raise NotImplementedError

    assert round(get_handicap_adjustment(1000.0, 0), 8) == 0


def lerp(x:float, y:float, a:float):
    return (x * (1.0 - a)) + (y * (a))
