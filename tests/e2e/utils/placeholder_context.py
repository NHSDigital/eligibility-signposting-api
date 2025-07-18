class ResolvedPlaceholderContext:
    def __init__(self):
        self.values = {}

    def add(self, placeholder: str, resolved_value: str):
        self.values[placeholder] = resolved_value  # Drop file_name key nesting

    def get(self, placeholder: str) -> str:
        return self.values.get(placeholder)

    def all(self):
        return self.values


class PlaceholderDTO:
    def __init__(self):
        self.placeholders = {}  # key: filename, value: dict of placeholders per file

    def add(self, key: str, value: str, file_name: str):
        if file_name not in self.placeholders:
            self.placeholders[file_name] = {}
        self.placeholders[file_name][key] = value

    def get(self, key: str, file_name: str):
        return self.placeholders.get(file_name, {}).get(key)

    def get_all_for_file(self, file_name: str):
        return self.placeholders.get(file_name, {}).copy()

    def all(self):
        return self.placeholders.copy()
