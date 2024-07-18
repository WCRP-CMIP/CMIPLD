class DotAccessibleDict:
    def __init__(self, entries):
        self.entries = dict(entries)
        for key in self.entries.keys():
            self.__dict__[key] = self.entries[key]

    # def __getattr__(self, name):
    #     if name in self.entries:
    #         return self.entries[name]
    #     else:
    #         raise AttributeError(f"'DotAccessibleDict' object has no attribute '{name}'")

    def __str__(self):
        return str(self.entries.keys())