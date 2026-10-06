import unittest
from app.main import score, generate_pitch

class RevenueHunterTests(unittest.TestCase):
    def test_score_rewards_budget_and_fit(self):
        value, reasons = score(
            "AI automation workflow",
            "Remote global buyer needs python automation this week",
            600,
            "Direct Prospect",
        )
        self.assertGreaterEqual(value, 70)
        self.assertIn("budget ≥ $500", reasons)
        self.assertIn("international-friendly", reasons)

    def test_pitch_has_trial_amount(self):
        pitch = generate_pitch({"title": "Analytics pilot", "budget": 400})
        self.assertIn("$400 fixed", pitch)

if __name__ == "__main__":
    unittest.main()
