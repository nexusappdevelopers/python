# Trichome analysis snippet (extracted)

This folder is an extracted, reusable snippet from the main repo:

- `trichome_ai.py`: trichome prompt + OpenAI call
- `response_utils.py`: DRF `create_response()` helper

## Requirements

- `OPENAI_API` environment variable must be set (same name used in the repo).
- Python deps already used by the repo: `openai`, `python-decouple`, and (for `response_utils.py`) `djangorestframework`.

## Minimal usage

```python
from snippets.trichome_analysis.trichome_ai import generate_prompt, analyze_with_openai

prompt = generate_prompt()

with open("some_trichome_photo.jpg", "rb") as f:
    result_json_text = analyze_with_openai(prompt, images=[f])

print(result_json_text)
```

