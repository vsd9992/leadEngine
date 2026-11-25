import unittest

from lead_coohom import SCORES, assess, passages

PAGE = "https://prospect.example/"
TEXT = ("Book a design consultation at one of our showrooms. "
        "Our company is permanently closed. "
        "We only perform OEM production. "
        "We have no showroom or design services.")


class CoohomRubricTests(unittest.TestCase):
    def evaluate(self, scores, front, operating=("unknown", "")):
        result = {
            "criteria": {key: {"score": score, "ref": "1"} for key, score in zip(SCORES, scores)},
            "commercial_front": {"status": front[0], "ref": front[1]},
            "operating": {"status": operating[0], "ref": operating[1]},
            "profile": {},
        }
        state = assess(result, passages({PAGE: TEXT}))
        return state, result

    def test_outsourced_studio_can_be_strong(self):
        state, result = self.evaluate((15, 9, 10, 8, 0), ("present", "1"))
        self.assertEqual((state, result["fit_score"], result["fit_bucket"]), ("qualified", 42, "Strong Fit"))
        self.assertEqual(result["criteria"]["customer_design"]["page_url"], PAGE)

    def test_production_and_denial_cannot_qualify(self):
        for front in (("pure_production", "3"), ("present", "4"), ("present", "999")):
            with self.subTest(front=front):
                state, result = self.evaluate((15, 10, 10, 10, 5), front)
                self.assertEqual((state, result["fit_score"]), ("review", 23))

    def test_closed_business_is_out_of_scope(self):
        state, result = self.evaluate((15, 10, 10, 10, 5), ("present", "1"), ("dormant", "2"))
        self.assertEqual((state, result["fit_score"]), ("out_of_scope", 14))

    def test_manufacturing_does_not_make_a_low_design_score_strong(self):
        _, result = self.evaluate((6, 10, 10, 10, 5), ("present", "1"))
        self.assertEqual(result["fit_bucket"], "Good Fit")


if __name__ == "__main__":
    unittest.main()
