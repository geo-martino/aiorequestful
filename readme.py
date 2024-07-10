"""
Fills in the variable fields of the README template and generates README.md file.
"""
from aiorequestful import PROGRAM_OWNER_USER, PROGRAM_NAME
from aiorequestful.auth.basic import BASIC_CLASSES
from aiorequestful.auth.oauth2 import OAUTH2_CLASSES
from aiorequestful.cache.backend import CACHE_CLASSES

SRC_FILENAME = "README.template.md"
TRG_FILENAME = SRC_FILENAME.replace(".template", "")


def format_readme():
    """Format the readme template and save the formatted readme"""
    format_map_standard = {
        "program_name": PROGRAM_NAME,
        "program_name_lower": PROGRAM_NAME.lower(),
        "program_owner_user": PROGRAM_OWNER_USER,
    }
    format_map_code = {
        "cache_backends": sorted(cls.__name__ for cls in CACHE_CLASSES),
        "basic_auth": sorted(cls.__name__ for cls in BASIC_CLASSES),
        "oauth2": sorted(cls.__name__ for cls in OAUTH2_CLASSES),
    }
    format_map_code = {k: "`" + "` `".join(v) + "`" for k, v in format_map_code.items()}
    format_map = format_map_standard | format_map_code

    with open(SRC_FILENAME, 'r') as file:
        template = file.read()

    formatted = template.format_map(format_map)
    with open(TRG_FILENAME, 'w') as file:
        file.write(formatted)


if __name__ == "__main__":
    format_readme()
    print(f"Formatted {TRG_FILENAME} file using template: {SRC_FILENAME}")
