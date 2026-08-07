class FavoritesRequireAuthError(Exception):
    def __init__(self) -> None:
        super().__init__("You must be logged in to filter by favorites")
