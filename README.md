# MD Viewer

A simple, elegant desktop application to let user select a directory and then render the tree of subdirectories and list the MD files in them, with a nice little preview on the right panel.
Author: @rohanpls

## Features

-   **File Explorer**: Browse directories and view all your `.md` files in a clean tree structure.
-   **Markdown Rendering**: Renders Markdown to HTML with a GitHub-like style.
-   **Mermaid Support**: Automatically renders Mermaid diagrams embedded in your Markdown.
-   **Syntax Highlighting**: Displays fenced code blocks with styling.
-   **Adjustable Font Size**: Easily increase or decrease the text size for comfortable reading.

## How to Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Application**:
    ```bash
    python MDViewer.py
    ```

## Dependencies

-   markdown2
-   mermaid.py
-   Pillow
-   tkhtmlview
-   ttkbootstrap
