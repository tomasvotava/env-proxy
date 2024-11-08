class Sentinel:
    _instance: "Sentinel | None" = None

    def __new__(cls) -> "Sentinel":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False


UNSET = Sentinel()
