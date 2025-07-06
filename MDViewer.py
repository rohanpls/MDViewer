import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import markdown2
import warnings
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinterweb import HtmlFrame
from PIL import Image, ImageDraw, ImageFont, ImageTk
import base64
from io import BytesIO
import tempfile

# Suppress the specific warning from mermaid.py
warnings.filterwarnings("ignore", message="IPython is not installed. Mermaidjs magic function is not available.")

import mermaid as mermaid_lib

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title("MD Viewer")
        self.geometry("1200x800")

        self.font_size = 12
        self.current_file_path = None

        # Set a larger default font for UI elements
        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 12), rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))
        
        self.photo = None
        self.set_app_icon()
        self.create_widgets()

    def set_app_icon(self):
        try:
            image = Image.new("RGB", (256, 256), "#4A7FF2")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("courbd.ttf", 160)
            except IOError:
                font = ImageFont.load_default()
            
            draw.text((128, 128), "MD", fill="white", font=font, anchor="mm")

            self.photo = ImageTk.PhotoImage(image)
            self.iconphoto(False, self.photo)
        except Exception as e:
            print(f"Error creating app icon: {e}")

    def create_widgets(self):
        # Menu
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Directory", command=self.open_directory)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        help_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Main container
        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(expand=True, fill="both")

        # Paned window for resizable panels
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(expand=True, fill="both")

        # Left panel for the directory tree
        tree_frame = ttk.Frame(paned_window, padding="5")
        self.tree = ttk.Treeview(tree_frame, bootstyle="info")
        self.tree.pack(expand=True, fill="both")
        self.tree.bind("<Double-1>", self.on_tree_select)
        paned_window.add(tree_frame, weight=1)

        # Right panel for the content
        content_frame = ttk.Frame(paned_window, padding="5")
        
        self.html_view = HtmlFrame(content_frame, messages_enabled=False)
        self.html_view.pack(expand=True, fill="both")

        paned_window.add(content_frame, weight=3)

        # Font size controls
        font_control_frame = ttk.Frame(content_frame)
        font_control_frame.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        plus_button = ttk.Button(font_control_frame, text="+", width=3, command=self.increase_font_size, bootstyle="secondary")
        plus_button.pack(side="left", padx=2)

        minus_button = ttk.Button(font_control_frame, text="-", width=3, command=self.decrease_font_size, bootstyle="secondary")
        minus_button.pack(side="left")

    def increase_font_size(self):
        self.font_size += 1
        self.refresh_html_view()

    def decrease_font_size(self):
        if self.font_size > 6:
            self.font_size -= 1
            self.refresh_html_view()

    def refresh_html_view(self):
        if self.current_file_path:
            self.show_file_content(self.current_file_path)

    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title("About MDViewer")
        about_win.geometry("300x200")
        about_win.resizable(False, False)
        if self.photo:
            about_win.iconphoto(False, self.photo)

        main_frame = ttk.Frame(about_win, padding=20)
        main_frame.pack(expand=True, fill="both")

        about_label = ttk.Label(main_frame, text="MDViewer", font=("Segoe UI", 16, "bold"))
        about_label.pack(pady=5)
        
        creator_label = ttk.Label(main_frame, text="Created by @rohanpls")
        creator_label.pack()

        link_label = ttk.Label(main_frame, text="https://github.com/rohanpls", foreground="blue", cursor="hand2")
        link_label.pack()
        import webbrowser
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/rohanpls"))

        ok_button = ttk.Button(main_frame, text="OK", command=about_win.destroy, bootstyle="primary")
        ok_button.pack(pady=20)
        
        about_win.transient(self)
        about_win.grab_set()
        self.wait_window(about_win)

    def open_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.populate_tree(path)

    def populate_tree(self, path):
        for i in self.tree.get_children():
            self.tree.delete(i)

        ignore_dirs = ['node_modules', '.git', '.venv', '__pycache__']

        def _has_md_files_recursive(dir_path):
            for p in os.listdir(dir_path):
                pt = os.path.join(dir_path, p)
                if os.path.isdir(pt) and p not in ignore_dirs and not p.startswith('.'):
                    if _has_md_files_recursive(pt):
                        return True
                elif p.endswith(".md"):
                    return True
            return False

        def _populate_tree(parent, dir_path):
            entries = sorted(os.listdir(dir_path), key=lambda x: (os.path.isfile(os.path.join(dir_path, x)), x))
            for p in entries:
                pt = os.path.join(dir_path, p)
                if os.path.isdir(pt) and p not in ignore_dirs and not p.startswith('.'):
                    if _has_md_files_recursive(pt):
                        node = self.tree.insert(parent, "end", text=p, open=False)
                        _populate_tree(node, pt)
                elif p.endswith(".md"):
                    self.tree.insert(parent, "end", text=p, values=[pt])

        root_node = self.tree.insert("", "end", text=os.path.basename(path), open=True, values=[path])
        _populate_tree(root_node, path)

    def on_tree_select(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        file_path_values = self.tree.item(selected_item[0], "values")
        if file_path_values and file_path_values[0].endswith(".md"):
            self.current_file_path = file_path_values[0]
            self.show_file_content(self.current_file_path)

    def show_file_content(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            # Process Mermaid diagrams first
            import re
            mermaid_images = {}
            def replace_mermaid_block(match):
                code = match.group(1)
                try:
                    m = mermaid_lib.Mermaid(code)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                        temp_path = temp_file.name
                    
                    m.to_png(temp_path)
                    
                    with open(temp_path, "rb") as f:
                        png_data = f.read()
                    
                    os.remove(temp_path)

                    img_base64 = base64.b64encode(png_data).decode('utf-8')
                    placeholder = f"<!-- mermaid-placeholder-{len(mermaid_images)} -->"
                    mermaid_images[placeholder] = f"data:image/png;base64,{img_base64}"
                    return f'<img src="{placeholder}">'
                except Exception as e:
                    return f"<pre>Mermaid Rendering Failed: {e}</pre>"

            md_content_with_placeholders = re.sub(r"```mermaid(.*?)```", replace_mermaid_block, md_content, flags=re.DOTALL)
            
            # Convert Markdown to HTML
            html_content = markdown2.markdown(
                md_content_with_placeholders, 
                extras=["fenced-code-blocks", "tables", "cuddled-lists", "strike", "code-friendly"]
            )

            # Replace placeholders with actual image data
            for placeholder, img_data in mermaid_images.items():
                html_content = html_content.replace(f'src="{placeholder}"', f'src="{img_data}"')

            # Add GitHub-like styling
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
                        font-size: {self.font_size}pt;
                        line-height: 1.6;
                        color: #24292e;
                        background-color: #ffffff;
                        word-wrap: break-word;
                    }}
                    .container {{
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        margin-top: 24px;
                        margin-bottom: 16px;
                        font-weight: 600;
                        line-height: 1.25;
                    }}
                    h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em;}}
                    h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em;}}
                    h3 {{ font-size: 1.25em; }}
                    a {{ color: #0366d6; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    pre {{ background-color: #f6f8fa; padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; border-radius: 6px; }}
                    code {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace; font-size: 85%; }}
                    pre > code {{ font-size: 100%; }}
                    table {{ border-collapse: collapse; width: 100%; display: block; overflow: auto;}}
                    th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; }}
                    th {{ font-weight: 600; background-color: #f6f8fa; }}
                    img {{ max-width: 100%; height: auto; background-color: #ffffff; }}
                    blockquote {{ color: #6a737d; border-left: .25em solid #dfe2e5; padding: 0 1em; margin-left: 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    {html_content}
                </div>
            </body>
            </html>
            """
            self.html_view.load_html(styled_html)

        except Exception as e:
            self.html_view.load_html(f"<h1>Error</h1><p>Failed to render file: {e}</p>")

if __name__ == "__main__":
    app = App()
    app.mainloop()
