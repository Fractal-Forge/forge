# Forge

Minimal Jinja2 template rendering engine for [Fractal Forge](https://github.com/Fractal-Forge)
generator templates. It replaces the Cookiecutter fork previously used by
fractal-studio, keeping only the feature set the generator actually uses.

The caller supplies the full context — there is no context file
(`cookiecutter.json` is gone), no prompting, no user config, no VCS cloning
and no replay. The top-level Jinja variable name is a parameter, so templates
can use `{{ forge.project_id }}`, `{{ fractal.project_id }}` or (during
migration) `{{ cookiecutter.project_id }}`.

## Install

```bash
uv add "fractal-forge @ git+ssh://git@github.com/Fractal-Forge/forge.git"
```

## Usage

```python
from forge import forge

project_dir = forge(
    template="path/to/v1/templates/project",  # contains the {{ ... }} dir
    context=project_context,                   # plain dict, passed verbatim
    output_dir="/tmp/out",
    context_key="forge",                       # {{ forge.* }} in templates
    extensions=[StringOperationsExtension],    # classes or import-path strings
    remove_file_extension=".jinja2",           # default; also accepts a tuple, e.g. (".jinja2", ".j2")
    overwrite_if_exists=True,
)
```

A template directory looks like:

```
project/
├── hooks/                     # optional
│   └── post_gen_project.py    # Jinja-rendered, then run with cwd=output
└── {{forge.project_id}}/      # the templated project dir (any context_key)
    ├── README.md.jinja2
    └── src/{{forge.name_snake}}/...
```

## Behavior

- **Strict rendering**: undefined variables raise
  `UndefinedVariableInTemplateError` (with the offending file in the message)
  instead of rendering empty.
- **Binary files** are detected and copied verbatim; file permissions are
  copied from the template file (`shutil.copymode`).
- **Newlines** of each template file are preserved; pass `newline="\n"` to
  force a style.
- **Hooks**: `pre_gen_project` / `post_gen_project` scripts in `hooks/` are
  rendered through Jinja with the same context, then executed with the
  generated project directory as working directory. A failing hook removes
  the generated directory (unless it pre-existed or
  `keep_project_on_failure=True`).
- **`copy_without_render`**: fnmatch patterns (relative to the template dir)
  copied verbatim, Jinja syntax left intact.
- Not thread-safe (the render walk uses `os.chdir`); use separate processes
  for parallel generation, as fractal-studio already does.

## Migrating from the Cookiecutter fork

| Cookiecutter fork | Forge |
|---|---|
| `cookiecutter(template=...)` | `forge(template=...)` |
| `extra_context=` + `force_overwrite_context=True` | `context=` (passed verbatim) |
| `cookiecutter.json` (empty) | removed entirely |
| `{{ cookiecutter.* }}` hardcoded | `context_key=` parameter |
| `_extensions` context key | `extensions=` parameter |
| `remove_template_extension=` | `remove_file_extension=` (now defaults to `.jinja2`; also accepts a tuple) |
| `_copy_without_render` context key | `copy_without_render=` parameter |
| `_new_lines` context key | `newline=` parameter |
| `_jinja2_env_vars` context key | `env_options=` parameter |
| `no_input`, `replay`, `checkout`, `directory`, `config_file`, ... | removed |

Template dir discovery no longer requires the folder name to contain the word
`cookiecutter` — any directory whose name contains `{{ ... }}` is the template.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## License

BSD 3-Clause. Contains code derived from
[Cookiecutter](https://github.com/cookiecutter/cookiecutter) (BSD 3-Clause);
see `LICENSE`.
