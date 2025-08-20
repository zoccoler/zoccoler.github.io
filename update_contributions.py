import os
import requests
import re
import time

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME", "zoccoler")
README_PATH = "README.md"

def fetch_merged_prs(username):
    prs = []
    page = 1
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    while True:
        url = (
            f"https://api.github.com/search/issues"
            f"?q=author:{username}+is:pr+is:merged"
            f"&per_page=100&page={page}"
        )
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            break
        prs.extend(items)
        page += 1
        # API rate limit: 10 requests per minute for search API
        if page % 9 == 0:
            time.sleep(7)
    return prs

def is_public_repo(repo_url):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(repo_url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return not data.get("private", True)  # True if repo is public

def group_latest_by_repo(prs, skip_repo):
    latest = {}
    for pr in prs:
        repo_full_name = pr["repository_url"].replace("https://api.github.com/repos/", "")
        if repo_full_name == skip_repo:
            continue
        if not is_public_repo(pr["repository_url"]):
            continue
        if repo_full_name not in latest or pr["closed_at"] > latest[repo_full_name]["closed_at"]:
            latest[repo_full_name] = pr
    return latest

def make_markdown_section(latest_by_repo):
    # Sort entries by PR 'closed_at' (which is the merged date), most recent first
    items = sorted(
        latest_by_repo.items(),
        key=lambda x: x[1]['closed_at'],
        reverse=True
    )
    lines = []
    for repo, pr in items:
        line = f"- **[{repo}](https://github.com/{repo})**: [#{pr['number']} {pr['title']}]({pr['html_url']}) (merged {pr['closed_at'][:10]})"
        lines.append(line)
    return "\n".join(lines)


from datetime import datetime

def update_readme(new_section):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Update contributions section as before
    section_re = re.compile(
        r"(<!--contrib-start-->)(.*?)(<!--contrib-end-->)",
        re.DOTALL,
    )
    replacement = f"<!--contrib-start-->\n{new_section}\n<!--contrib-end-->"
    if section_re.search(content):
        content = section_re.sub(replacement, content)
    else:
        content += f"\n## Latest Contributions\n{replacement}\n"

    # Update or insert last updated date
    today_str = datetime.now().strftime("%B %Y")
    last_updated_re = re.compile(r"_Last updated:.*?_")
    new_last_updated = f"_Last updated: {today_str}_"

    if last_updated_re.search(content):
        content = last_updated_re.sub(new_last_updated, content)
    else:
        # Add at the very end, separated by a blank line
        content = content.rstrip() + "\n\n" + new_last_updated + "\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    prs = fetch_merged_prs(USERNAME)
    skip_repo = f"{USERNAME}/{USERNAME}"
    latest = group_latest_by_repo(prs, skip_repo)
    md_section = make_markdown_section(latest)
    update_readme(md_section)

if __name__ == "__main__":
    main()
