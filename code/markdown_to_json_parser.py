# The code is importing necessary modules for the script to work:
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
import markdown2
from prettytable import PrettyTable
from github import Github, InputGitTreeElement, InputGitAuthor


class FileUpdate:
    def __init__(self, path, content):
        self.path = path
        self.content = content


def print_colored_status(status):
    color_codes = {"No table": 91, "Success": 92, "Error": 91}
    color_code = color_codes.get(status, 0)  # Default to red color if not found
    return f"\033[{color_code}m{status}\033[0m" if color_code else status


def print_colored_count(count, label):
    color_code = 91  # Default to red color for No table and Errors

    if label == "Success" and count > 0:
        color_code = 92  # Green color for Success
    elif label in ["No table", "Errors"] and count == 0:
        color_code = 92  # Green color for No table or Errors when count is 0

    return f"\033[{color_code}m{count}\033[0m"


def has_file_changed(repo, file_path, new_content, branch_name):
    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        existing_content = contents.decoded_content.decode("utf-8")
        return existing_content != new_content
    except Exception as e:
        print(f"Exception in has_file_changed: {e}")
        print(f"File Path: {file_path}")
        return True


def create_git_tree_elements(file_updates):
    return [
        InputGitTreeElement(
            path=update.path, mode="100644", type="blob", content=update.content
        )
        for update in file_updates
    ]


def update_repository_with_json(repo_owner, repo_name, file_updates):
    github_token = os.getenv("INPUT_PAPER_TOKEN") or os.getenv("PAPER_TOKEN")

    if not github_token:
        print("GitHub token not available. Exiting.")
        return

    g = Github(github_token)
    repo = g.get_user(repo_owner).get_repo(repo_name)

    try:
        if not file_updates:
            print("No changes detected. Exiting.")
            return

        # Check if each file has changed
        updated_files = [
            file_update
            for file_update in file_updates
            if has_file_changed(
                repo, file_update.path, file_update.content, repo.default_branch
            )
        ]

        print("All files:", file_updates)

        if not updated_files:
            print("No changes detected. Exiting.")
            return

        print("Updated files:", updated_files)

        # Get the latest commit
        latest_commit = repo.get_branch(repo.default_branch).commit

        # Create a tree with the updates
        tree_elements = create_git_tree_elements(updated_files)
        tree = repo.create_git_tree(tree_elements, base_tree=latest_commit.commit.tree)

        # Create a commit with the new tree
        commit_message = "Update files"
        commit_description = "Changes include the following files:\n"

        for update in updated_files:
            commit_description += f"- {update.path}\n"

        print(f"Latest Commit SHA: {latest_commit.sha}")
        print(f"New Tree SHA: {tree.sha}")

        committer = InputGitAuthor(
            name=g.get_user().name,
            email=g.get_user().email,
        )

        print(type(tree))
        print(type(latest_commit))
        print(type(committer))

        commit = repo.create_git_commit(
            message=commit_message,
            tree=tree,
            parents=[latest_commit],
            committer=committer,
            author=committer,
        )

        # Update the branch reference to the new commit
        print(f"Old Branch SHA: {repo.get_branch(repo.default_branch).commit.sha}")
        print(
            f"Current Branch Protection: {repo.get_branch(repo.default_branch).protected}"
        )
        # repo.get_branch(repo.default_branch).edit(commit.sha)
        repo.get_git_ref(f"heads/{repo.default_branch}").edit(commit.sha)
        print(f"New Branch SHA: {repo.get_branch(repo.default_branch).commit.sha}")

        print("Files updated successfully.")
    except Exception as e:
        print(f"Error updating files: {e}")


def process_markdown_file(
    markdown_file,
    output_directory,
    counter,
    table,
    success_count,
    no_table_count,
    error_count,
    file_updates,
):
    base_filename = markdown_file.stem
    json_filename = os.path.join(output_directory, f"{base_filename}.json")

    try:
        with open(markdown_file, "r", encoding="utf-8") as file:
            markdown_content = file.read()

        html_content = markdown2.markdown(
            text=markdown_content, html4tags=True, extras=["tables"]
        )
        soup = BeautifulSoup(html_content, "html.parser")
        table_in_file = soup.find("table")

        if table_in_file:
            papers = []

            for row in table_in_file.find_all("tr")[1:]:
                columns = row.find_all("td")

                title_column = columns[0]
                title = title_column.get_text(strip=True)
                title_link = title_column.find("a")
                title_page = title_link["href"] if title_link else None

                if title and any(column.find("a") for column in columns[1:]):
                    web_page_link = next(
                        (
                            a
                            for a in columns[1].find_all("a")
                            if "page" in a.img.get("alt", "").lower()
                        ),
                        None,
                    )

                    web_page = (
                        web_page_link["href"]
                        if web_page_link
                        and "web" in web_page_link.img.get("alt", "").lower()
                        else None
                    )
                    github_page = (
                        web_page_link["href"]
                        if web_page_link
                        and "github" in web_page_link.img.get("alt", "").lower()
                        else None
                    )

                    repo_link = next(
                        (
                            a
                            for a in columns[1].find_all("a")
                            if a.img.get("alt", "").lower() == "github"
                        ),
                        None,
                    )
                    repo = (
                        repo_link["href"]
                        if repo_link
                        and "github" in repo_link.img.get("alt", "").lower()
                        else None
                    )

                    demo_link = next(
                        (
                            a
                            for a in columns[1].find_all("a")
                            if "hugging face" in a.img.get("alt", "").lower()
                        ),
                        None,
                    )
                    demo_page = demo_link["href"] if demo_link else None

                    paper_thecvf_link = columns[2].find("a")
                    paper_thecvf = (
                        paper_thecvf_link["href"] if paper_thecvf_link else None
                    )

                    paper_arxiv_link = columns[2].find_all("a")
                    paper_arxiv = (
                        paper_arxiv_link[1]["href"]
                        if len(paper_arxiv_link) > 1
                        else None
                    )

                    video_link = columns[3].find("a")
                    video = video_link["href"] if video_link else None

                    paper_data = {
                        "title": title,
                        "title_page": title_page,
                        "repo": repo,
                        "web_page": web_page,
                        "github_page": github_page,
                        "demo_page": demo_page,
                        "paper_thecvf": paper_thecvf,
                        "paper_arxiv": paper_arxiv,
                        "video": video,
                    }

                    papers.append(paper_data)

            with open(json_filename, "w", encoding="utf-8") as file:
                json.dump(papers, file, ensure_ascii=False, indent=2)

            table.add_row(
                [
                    counter,
                    os.path.basename(json_filename),
                    print_colored_status("Success"),
                ],
            )

            json_content = json.dumps(papers, ensure_ascii=False, indent=2)
            file_updates.append(
                FileUpdate(path=f"json_data/{base_filename}.json", content=json_content)
            )

            success_count[0] += 1
        else:
            table.add_row(
                [counter, markdown_file.name, print_colored_status("No table")]
            )
            no_table_count[0] += 1
    except Exception as e:
        table.add_row(
            [
                counter,
                os.path.basename(json_filename),
                print_colored_status(f"Error: {e}"),
            ],
        )
        error_count[0] += 1

    return table, file_updates, success_count, no_table_count, error_count


def main():
    # Check if running in GitHub Actions
    in_actions = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("CI") == "true"

    # Define the paths based on the environment
    if in_actions:
        # Get the path to the GitHub workspace from environment variable
        github_workspace = os.getenv("GITHUB_WORKSPACE", "/github/workspace")

        # Define the paths using the GitHub workspace
        markdown_directory = Path(github_workspace) / "sections"
        output_directory = Path(github_workspace) / "json_data"
    else:
        # Define local paths
        markdown_directory = Path("/Users/dl/GitHub/WACV-2024-Papers/sections")
        output_directory = Path("/Users/dl/GitHub/WACV-2024-Papers/local_json_data")

    # Add this line at the end to print the paths for verification
    print(f"Markdown Directory: {markdown_directory}")
    print(f"Output Directory: {output_directory}")

    if not output_directory.is_dir():
        output_directory.mkdir(parents=True)

    # Create a PrettyTable
    table = PrettyTable(["#", "File", "Status"])
    table.align["File"] = "l"  # Align "File" column to the left

    # Create counters as lists to enable modification within functions
    success_count = [0]
    no_table_count = [0]
    error_count = [0]

    markdown_files = [f for f in markdown_directory.glob("*.md")]

    file_updates = []

    for counter, markdown_file in enumerate(markdown_files, start=1):
        (
            table,
            file_updates,
            success_count,
            no_table_count,
            error_count,
        ) = process_markdown_file(
            markdown_file,
            output_directory,
            counter,
            table,
            success_count,
            no_table_count,
            error_count,
            file_updates,
        )

    update_repository_with_json("DmitryRyumin", "WACV-2024-Papers", file_updates)

    # Print the PrettyTable
    print(table)

    summary_table = PrettyTable(["Category", "Count"])
    summary_table.align["Category"] = "l"  # Align "Category" column to the left

    # Add rows to the summary table
    summary_table.add_row(["Success", print_colored_count(success_count[0], "Success")])
    summary_table.add_row(
        ["No table", print_colored_count(no_table_count[0], "No table")]
    )
    summary_table.add_row(["Errors", print_colored_count(error_count[0], "Errors")])

    # Print the summary table
    print(summary_table)


if __name__ == "__main__":
    main()
