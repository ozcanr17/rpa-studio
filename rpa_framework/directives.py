import re

IMAGE_PATTERN = re.compile(r"^(\s*)IMAGE\s*:\s*(\S.*?)\s*$")


def image_target(text):
    match = IMAGE_PATTERN.match(text)
    return match.group(2) if match else None


def strip_directives(source):
    lines = source.split("\n")
    for index, line in enumerate(lines):
        match = IMAGE_PATTERN.match(line)
        if match:
            lines[index] = match.group(1) + "pass"
    return "\n".join(lines)
