# master inspection on water-node


def has_ready_to_move(places: dict) -> bool:
    for stage in places:
        del places[stage]["max_places"]

        for place in places[stage]:
            if places[stage][place]:
                return True

    return False


def has_best_placement(places: dict) -> bool:
    #

    for stage in places:
        p = places[stage]
        max_places = places[stage]["max_places"]

        # 1, 2, 3
        expected_places = [i + 1 for i in range(0, max_places)]

        del p["max_places"]

        # optimal

        for place_num in p:
            ready = p[place_num]


def move_to_best_placeent(places: dict) -> list:
    """Returns a list of jobs in correct order"""
    pass


# print(has_best_placement(not_best_placement))
# print(has_best_placement(best_placement))
