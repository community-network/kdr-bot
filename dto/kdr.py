class KDR:
    kills = 0
    deaths = 0

    def get_kdr(self):
        try:
            return round(self.kills / self.deaths, 2)
        except ZeroDivisionError:
            return 0.0
