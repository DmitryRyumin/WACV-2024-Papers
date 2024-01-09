# The code is importing necessary modules for the script to work:
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
import markdown2
from prettytable import PrettyTable


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


def process_markdown_file(
    markdown_file,
    output_directory,
    counter,
    table,
    success_count,
    no_table_count,
    error_count,
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

    return table, success_count, no_table_count, error_count


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
        output_directory = Path("/Users/dl/GitHub/WACV-2024-Papers/json_data")

    # Add this line at the end to print the paths for verification
    print(f"Markdown Directory: {markdown_directory}")
    print(f"Output Directory: {output_directory}")

    if not output_directory.is_dir():
        output_directory.mkdir(parents=True)

    # Add these lines to print the contents of the directories
    print(f"Contents of Markdown Directory: {list(markdown_directory.glob('*'))}")
    print(f"Contents of Output Directory: {list(output_directory.glob('*'))}")

    # Create a PrettyTable
    table = PrettyTable(["#", "File", "Status"])
    table.align["File"] = "l"  # Align "File" column to the left

    # Create counters as lists to enable modification within functions
    success_count = [0]
    no_table_count = [0]
    error_count = [0]

    markdown_files = [f for f in markdown_directory.glob("*.md")]

    for counter, markdown_file in enumerate(markdown_files, start=1):
        table, success_count, no_table_count, error_count = process_markdown_file(
            markdown_file,
            output_directory,
            counter,
            table,
            success_count,
            no_table_count,
            error_count,
        )

    # Calculate column lengths dynamically
    # column_lengths = [
    #     max(len(str(item)) for item in column) for column in zip(*table._rows)
    # ]

    # Add a separator row with dashes
    # separator_row = ["-" * length for length in column_lengths]
    # table.add_row(separator_row)

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
