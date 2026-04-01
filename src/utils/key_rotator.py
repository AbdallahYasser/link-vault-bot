class KeyRotator:
    def __init__(self, keys: list[str], provider_name: str):
        self.keys = [k for k in keys if k]
        self.provider_name = provider_name
        self._index = 0

    def current(self) -> str:
        if not self.keys:
            raise RuntimeError(f"No API keys configured for {self.provider_name}")
        return self.keys[self._index]

    def rotate(self):
        self._index += 1
        if self._index >= len(self.keys):
            self._index = 0
            raise RuntimeError(f"All {self.provider_name} keys exhausted")

    def reset(self):
        self._index = 0

    def has_keys(self) -> bool:
        return len(self.keys) > 0
