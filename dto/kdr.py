class KDR:
    kills = 0
    deaths = 0

    def get_kdr(self):
        try:
            return round(self.kills / self.deaths, 2)
        except ZeroDivisionError:
            return 0.0

    def combine(self, to_add: "KDR"):
        self.kills += to_add.kills
        self.deaths += to_add.deaths
