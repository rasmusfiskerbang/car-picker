---
name: markitdown
description: Convert documents, office files, PDFs, images, HTML, and structured text to Markdown with MarkItDown. Use when a user asks to extract or convert supported files into Markdown for analysis.
---

# MarkItDown

## Setup

1. Check whether the CLI is available:

   ```sh
   command -v markitdown && markitdown --version
   ```

2. If unavailable, install the complete converter as an isolated uv tool:

   ```sh
   uv tool install 'markitdown[all]'
   ```

   For a smaller installation, install only the required format extras, for example:

   ```sh
   uv tool install 'markitdown[pdf,docx,pptx]'
   ```

3. Confirm the command is ready with `markitdown --help`.

## Convert

1. Choose an output path outside the source file and keep the source unchanged. MarkItDown supports common document formats including PDF, Word, PowerPoint, Excel, images, HTML, CSV, JSON, XML, EPUB, and ZIP archives.

2. Convert with quoted paths:

   ```sh
   markitdown "input.pdf" -o "output.md"
   ```

   Use standard output when the Markdown is needed in a pipeline:

   ```sh
   markitdown "input.docx" > "output.md"
   ```

3. Check that the output exists, is non-empty, and begins with plausible document content before relying on it:

   ```sh
   test -s "output.md" && sed -n '1,40p' "output.md"
   ```

## Input boundary

Convert files from sources and paths that are authorized for the current process. For untrusted or hosted inputs, validate and restrict paths and network destinations before conversion; MarkItDown runs with the invoking process's access.
