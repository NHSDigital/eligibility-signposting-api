import re

def validate_markdown(text: str) -> None:
    errors = []
    lines = text.split("\n")
    incorrect_link_pattern = re.compile(r"\(.*?\)\[.*?\]")
    for i, line in enumerate(lines):
        # Rule: Headers must have a space after the hash
        if re.compile(r"^#{1,6}(?![ #])").match(line) and line.strip().replace("#", "") != "":
            errors.append("Header missing space after hash (e.g., use '# Title' not '#Title').")

        # Rule: Lists must have a space after the bullet
        if re.compile(r"^(\s*)[*+-](?![ *+-])").match(line):
            errors.append("List item missing space after bullet.")

        # Rule: Headers must be surrounded by blank lines
        is_header = re.compile(r"^#{1,6} ").match(line) or re.compile(r"^#{1,6}(?![ #])").match(line)
        is_not_empty_line = i > 0 and lines[i - 1].strip() != ""
        if is_header and is_not_empty_line:
            errors.append("Header must be preceded by a blank line.")

        # Check for incorrect Markdown link format: (text)[url]
        if re.compile(r"\[.*?\]\s+\(.*?\)").search(line):
            errors.append("Link format invalid: use [text](url) with no spaces.")

    if errors:
        raise ValueError("\n".join(errors))
