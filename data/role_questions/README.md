# Role PDF Question Folder

Add your role question PDFs here.

## Supported layouts

1. One PDF directly in this folder:
- `data/role_questions/Backend Engineer.pdf`
- Role name is taken from filename.

2. Subfolder per role (recommended):
- `data/role_questions/Backend Engineer/questions.pdf`
- `data/role_questions/Data Scientist/set-1.pdf`
- Role name is taken from subfolder name.

## Important formatting in PDF

Best extraction happens when questions are numbered like:
- `Question 1: ...`
- `Q2) ...`
- `3. ...`

## After adding PDFs

Run:

```bash
python -m vector_store.init_vector_store
```

This script now loads questions from this folder and also keeps built-in defaults.
