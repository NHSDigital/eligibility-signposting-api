import os
import re
import subprocess
import sys
import requests

def run_command(command, check=True):
    """Runs a shell command and returns its stripped standard output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

def set_github_output(name, value):
    """Writes an output to the GITHUB_OUTPUT file."""
    github_output_file = os.environ.get("GITHUB_OUTPUT")
    if github_output_file:
        try:
            with open(github_output_file, "a") as f:
                f.write(f"{name}={value}\n")
        except IOError as e:
            print(f"Error writing to GITHUB_OUTPUT file: {e}", file=sys.stderr)
            sys.exit(1)

def create_github_release(tag_name, prerelease, token):
    """Creates a GitHub release using the GitHub API."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        print("Error: GITHUB_REPOSITORY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    release_name = f"Pre-release {tag_name}" if prerelease else f"Release {tag_name}"
    body = "Auto pre-release created during preprod deployment." if prerelease else "Auto-release created during production deployment."

    data = {
        "tag_name": tag_name,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": prerelease,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        print(f"Successfully created GitHub release for tag {tag_name}.")
    else:
        print(f"Error creating GitHub release: {response.status_code} {response.text}", file=sys.stderr)
        sys.exit(1)

def handle_preprod():
    """Handles the pre-production release logic."""
    run_command("git fetch --tags")

    latest_final_cmd = "git tag -l 'v[0-9]*.[0-9]*.[0-9]*' | grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+$' | sort -V | tail -n1"
    latest_final = run_command(latest_final_cmd, check=False)

    latest_any_rc_cmd = "git tag -l 'v[0-9]*.[0-9]*.[0-9]*-rc.*' | sort -V | tail -n1"
    latest_any_rc = run_command(latest_any_rc_cmd, check=False)

    release_type = os.environ.get("INPUT_RELEASE_TYPE", "patch")

    if release_type == "rc" and latest_any_rc:
        base = latest_any_rc.split('-rc.')[0]
    else:
        if not latest_final:
            base_major, base_minor, base_patch = 0, 0, 0
        else:
            version_part = latest_final.lstrip('v')
            base_major, base_minor, base_patch = map(int, version_part.split('.'))

        if release_type == "major":
            base_major += 1
            base_minor, base_patch = 0, 0
        elif release_type == "minor":
            base_minor += 1
            base_patch = 0
        else:
            base_patch += 1

        base = f"v{base_major}.{base_minor}.{base_patch}"

    last_rc_for_base_cmd = f"git tag -l '{base}-rc.*' | sort -V | tail -n1"
    last_rc_for_base = run_command(last_rc_for_base_cmd, check=False)

    if not last_rc_for_base:
        next_rc = f"{base}-rc.1"
    else:
        n = int(last_rc_for_base.split('-rc.')[-1])
        next_rc = f"{base}-rc.{n + 1}"

    sha = run_command("git rev-parse HEAD")
    print(f"Tagging {sha} as {next_rc}")
    run_command(f"git tag -a '{next_rc}' '{sha}' -m 'Release candidate {next_rc}'")
    run_command(f"git push origin '{next_rc}'")

    set_github_output("rc", next_rc)
    create_github_release(next_rc, prerelease=True, token=os.environ["GITHUB_TOKEN"])

def handle_prod():
    """Handles the production release logic."""
    ref = os.environ["REF"]

    if not re.match(r"^v[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$", ref):
        print(f"ERROR: For prod, 'ref' must be an RC tag like v1.4.0-rc.2 (got: {ref})", file=sys.stderr)
        sys.exit(1)

    run_command("git fetch --tags --quiet")

    if run_command(f"git rev-parse -q --verify 'refs/tags/{ref}'", check=False) == "":
        print(f"ERROR: Tag '{ref}' does not exist on origin.", file=sys.stderr)
        sys.exit(1)

    final_tag = ref.split("-rc.")[0]
    sha = run_command(f"git rev-list -n 1 '{ref}'")

    if run_command(f"git rev-parse -q --verify 'refs/tags/{final_tag}'", check=False) != "":
        print(f"ERROR: Final tag {final_tag} already exists.", file=sys.stderr)
        sys.exit(1)

    print(f"Promoting {ref} ({sha}) to final {final_tag}")
    run_command(f"git tag -a '{final_tag}' '{sha}' -m 'Release {final_tag}'")
    run_command(f"git push origin '{final_tag}'")

    set_github_output("final", final_tag)
    create_github_release(final_tag, prerelease=False, token=os.environ["GITHUB_TOKEN"])

def main():
    """Main function to run release management based on environment."""
    run_command('git config user.name "github-actions" && git config user.email "github-actions@github.com"')

    environment = os.environ.get("ENVIRONMENT")
    if environment == "preprod":
        handle_preprod()
    elif environment == "prod":
        handle_prod()
    else:
        print(f"Warning: No release management action for environment '{environment}'. Skipping.", file=sys.stderr)

if __name__ == "__main__":
    main()
