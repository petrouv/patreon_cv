# Patreon Post Converter

This Python script converts raw Patreon API post data, saved using [patrickkfkan/patreon-dl](https://github.com/patrickkfkan/patreon-dl), into standalone HTML files.

While designed for the directory structure created by `patreon-dl`, it can be easily adapted to work with similar raw data from the private Patreon API stored in a different file structure with minimal modifications.

## Usage

### 1. Setup

Create and activate a Python virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required dependency:
```bash
pip install Jinja2
```

### 2. Run the Script

The script takes a single argument: the path to the directory you want to process.

**To convert a single post:**

Provide the path to the specific post's directory.
```bash
python main.py "path/to/your/posts/post_name-12345"
```

**To convert all posts in a directory:**

Provide the path to the parent directory containing all post folders.
```bash
python main.py "path/to/your/posts/"
```

The generated `post.html` file will be saved in the `post_info` subdirectory alongside the original `post-api.json`.
