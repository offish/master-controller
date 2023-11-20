from unittest import TestCase

from controller.moving import has_best_placement, has_ready_to_move

best_placement = {
    "1": {
        "2": False,  # there is no plant holder in place 1
        "3": False,
        "max_places": 3,
    },  # bool is if should change stage
    "2": {"1": False, "2": False, "3": False, "max_places": 3},
    "3": {"3": False, "max_places": 3},
}

not_best_placement = {
    "1": {
        "1": False,  # there is no plant holder in place 2
        "3": True,
        "max_places": 3,
    },  # bool is if should change stage
    "2": {"1": False, "2": True, "3": True, "max_places": 3},
    "3": {"2": True, "max_places": 3},
}


class TestMoving(TestCase):
    def test_ready_to_move(self):
        is_ready = has_ready_to_move(best_placement)
        not_ready = has_ready_to_move(not_best_placement)

        self.assertEqual(False, is_ready)
        self.assertEqual(True, not_ready)

    def test_not_best_placement(self):
        pass
