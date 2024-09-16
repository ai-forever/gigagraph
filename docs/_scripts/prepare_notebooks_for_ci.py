"""Preprocess notebooks for CI. Currently adds VCR cassettes and optionally removes pip install cells."""

import logging
import os

import click
import nbformat

logger = logging.getLogger(__name__)
NOTEBOOK_DIRS = ("docs/docs/how-tos",)
DOCS_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASSETTES_PATH = os.path.join(DOCS_PATH, "cassettes")

NOTEBOOKS_NO_CASSETTES = (
    "docs/docs/how-tos/visualization.ipynb",
    "docs/docs/how-tos/many-tools.ipynb"
)


def comment_install_cells(notebook: nbformat.NotebookNode) -> nbformat.NotebookNode:
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue

        if "pip install" in cell.source:
            # Comment out the lines in cells containing "pip install"
            cell.source = "\n".join(
                f"# {line}" if line.strip() else line
                for line in cell.source.splitlines()
            )

    return notebook


def is_magic_command(code: str) -> bool:
    return code.strip().startswith("%") or code.strip().startswith("!")


def is_comment(code: str) -> bool:
    return code.strip().startswith("#")


def add_vcr_to_notebook(
    notebook: nbformat.NotebookNode, cassette_prefix: str
) -> nbformat.NotebookNode:
    """Inject `with vcr.cassette` into each code cell of the notebook."""

    # Inject VCR context manager into each code cell
    for idx, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue

        lines = cell.source.splitlines()
        # skip if empty cell
        if not lines:
            continue

        are_magic_lines = [is_magic_command(line) for line in lines]

        # skip if all magic
        if all(are_magic_lines):
            continue

        if any(are_magic_lines):
            raise ValueError(
                "Cannot process code cells with mixed magic and non-magic code."
            )

        # skip if just comments
        if all(is_comment(line) or not line.strip() for line in lines):
            continue

        cell_id = cell.get("id", idx)
        cassette_name = f"{cassette_prefix}_{cell_id}.yaml"
        cell.source = f"with vcr.use_cassette('{cassette_name}', filter_headers=['x-api-key', 'authorization'], record_mode='once'):\n" + "\n".join(
            f"    {line}" for line in lines
        )

    # Add import statement
    vcr_import_lines = [
        "import vcr",
        # this is needed for ChatAnthropic
        "import nest_asyncio",
        "nest_asyncio.apply()",
    ]
    import_cell = nbformat.v4.new_code_cell(source="\n".join(vcr_import_lines))
    import_cell.pop("id", None)
    notebook.cells.insert(0, import_cell)
    return notebook


def process_notebooks(should_comment_install_cells: bool) -> None:
    for directory in NOTEBOOK_DIRS:
        for root, _, files in os.walk(directory):
            for file in files:
                if not file.endswith(".ipynb") or "ipynb_checkpoints" in root:
                    continue

                notebook_path = os.path.join(root, file)
                try:
                    notebook = nbformat.read(notebook_path, as_version=4)

                    if should_comment_install_cells:
                        notebook = comment_install_cells(notebook)

                    base_filename = os.path.splitext(os.path.basename(file))[0]
                    cassette_prefix = os.path.join(CASSETTES_PATH, base_filename)
                    if notebook_path not in NOTEBOOKS_NO_CASSETTES:
                        notebook = add_vcr_to_notebook(
                            notebook, cassette_prefix=cassette_prefix
                        )

                    nbformat.write(notebook, notebook_path)
                    logger.info(f"Processed: {notebook_path}")
                except Exception as e:
                    logger.error(f"Error processing {notebook_path}: {e}")


@click.command()
@click.option(
    "--comment-install-cells",
    is_flag=True,
    default=False,
    help="Whether to comment out install cells",
)
def main(comment_install_cells):
    process_notebooks(should_comment_install_cells=comment_install_cells)
    logger.info("All notebooks processed successfully.")


if __name__ == "__main__":
    main()
