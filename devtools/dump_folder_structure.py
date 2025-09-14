import os


def get_gitignore_dirs(base_path="."):
    ignored = set()
    gitignore = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore):
        with open(gitignore, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments, wildcards, and negations
                if not line or line.startswith("#") or "*" in line or line.startswith("!"):
                    continue
                # Only directories or file names, not paths
                if line.endswith("/"):
                    ignored.add(line.rstrip("/"))
                else:
                    # Optionally, add files, but we focus on dirs here
                    ignored.add(line)
    # Add some built-in ignores for typical Python/Javascript cruft
    ignored.update({".git", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"})
    return ignored


def get_dir_comment(directory):
    candidates = ["README.md", "readme.md", "__init__.py"]
    for fname in candidates:
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    comment = line.strip()
                    if comment:
                        # If __init__.py, strip Python comment/quote chars
                        if fname == "__init__.py":
                            comment = comment.strip("\"'# ")
                        # if *.md, just take the first line, remove starting spaces and # if present
                        if fname.lower().endswith(".md"):
                            comment = comment.lstrip("# ").strip()
                        return comment
    return ""


def print_tree(root, prefix="", ignored_dirs=None):
    files = sorted(os.listdir(root))
    dirs = [f for f in files if os.path.isdir(os.path.join(root, f)) and (ignored_dirs is None or f not in ignored_dirs)]
    for idx, d in enumerate(dirs):
        path = os.path.join(root, d)
        branch = "├── " if idx < len(dirs) - 1 else "└── "
        comment = get_dir_comment(path)
        cmt_str = f"\t\t\t\t# {comment}" if comment else ""
        print(f"{prefix}{branch}{d}/" + cmt_str)
        extra = "│   " if idx < len(dirs) - 1 else "    "
        print_tree(path, prefix + extra, ignored_dirs)


if __name__ == "__main__":
    ignored_dirs = get_gitignore_dirs()
    print("Repository structure:\n")
    print_tree(".", ignored_dirs=ignored_dirs)
