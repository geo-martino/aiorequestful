from pathlib import Path

path_tests = Path(__file__).parent
path_root = path_tests.parent
path_resources = path_tests.joinpath("__resources")

path_token = path_resources.joinpath("token").with_suffix(".json")
