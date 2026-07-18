import json
from datetime import date

DATA_FILE = "data.json"


class DataManager:

    def __init__(self):
        self.data = self.load()

    def load(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception:
            return {
                "current_user": 0,
                "users": [
                    {
                        "name": "良治",
                        "start_date": "2026-07-12",
                        "cigarettes_per_day": 10,
                        "price_per_pack": 600,
                    },
                    {
                        "name": "胡花",
                        "start_date": "2026-07-01",
                        "cigarettes_per_day": 10,
                        "price_per_pack": 600,
                    },
                ],
                "workout": [],
            }

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                self.data,
                f,
                ensure_ascii=False,
                indent=4,
            )

    @property
    def current_user(self):
        return self.data["current_user"]

    @current_user.setter
    def current_user(self, value):
        self.data["current_user"] = value
        self.save()

    def get_user(self):
        return self.data["users"][self.current_user]

    def change_user(self, index):
        self.current_user = index

    # -------------------------
    # 筋トレ
    # -------------------------

    def get_workouts(self):
        return self.data.get("workout", [])

    def add_workout(self, workout):

        self.data.setdefault("workout", [])

        today = str(date.today())

        for record in self.data["workout"]:

            if record["date"] == today:

                for part in workout["parts"]:

                    if part not in record["parts"]:
                        record["parts"].append(part)

                self.save()
                return

        self.data["workout"].append(workout)

        self.save()


data = DataManager()