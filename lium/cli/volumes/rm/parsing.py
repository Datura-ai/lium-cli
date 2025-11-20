"""Volumes rm parsing."""


def parse(indices: str, volumes_data: list) -> tuple[dict, str]:
    index_list = [idx.strip() for idx in indices.split(',')]
    volumes_to_remove = []

    for index_str in index_list:
        try:
            idx = int(index_str)
            if idx < 1 or idx > len(volumes_data):
                return {}, f"Index {index_str} out of range (1..{len(volumes_data)})"
            volumes_to_remove.append((idx, volumes_data[idx - 1]))
        except ValueError:
            return {}, f"Invalid index: {index_str}. Must be a number."

    return {"volumes_to_remove": volumes_to_remove}, ""
