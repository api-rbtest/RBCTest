def find_key_val_path(d, target_key, target_val):
    if target_key in d and target_val in d[target_key]:
        return [target_key]
    for key, value in d.items():
        if isinstance(value, dict):
            path = find_key_val_path(value, target_key, target_val)
            if path:
                return [key] + path
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    path = find_key_val_path(item, target_key, target_val)
                    if path:
                        return [key, index] + path
    return None

def find_key_path(d, target_key):
    if target_key in d:
        return [target_key]
    for key, value in d.items():
        if isinstance(value, dict):
            path = find_key_path(value, target_key)
            if path:
                return [key] + path
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    path = find_key_path(item, target_key)
                    if path:
                        return [key, index] + path
    return None


def filter_dict(d, path):
    if not path:
        return None
    current_key = path[0]
    if current_key in d:
        if len(path) == 1:
            return {current_key: d[current_key]}
        elif isinstance(d[current_key], dict):
            nested_filtered = filter_dict(d[current_key], path[1:])
            if nested_filtered:
                return {current_key: nested_filtered}
        elif isinstance(d[current_key], list):
            index = path[1]
            nested_filtered = filter_dict(d[current_key][index], path[2:])
            if nested_filtered:
                return {current_key: [nested_filtered]}
    return None


def filter_dict_by_key_val(d, target_key, target_val):
    path = find_key_path(d, target_key, target_val)
    if not path:
        return {}
    return filter_dict(d, path)

def filter_dict_by_key(d, target_key):
    path = find_key_path(d, target_key)
    if not path:
        return {}
    return filter_dict(d, path)