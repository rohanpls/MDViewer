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
import re

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
        self.ignore_dirs = ['node_modules', '.git', '.venv', '__pycache__']
        self.open_files = {} # To store {file_path: {"tab_id": str, "tab_frame": ttk.Frame}}
        self.html_cache = {} # To cache rendered HTML

        # Set a larger default font for UI elements
        self.style.configure("Treeview", font=("Segoe UI", 12), rowheight=30)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))
        
        self.photo = None
        self.set_app_icon()
        self.create_widgets()

    def set_app_icon(self):
        try:
            image = Image.new("RGB", (256, 256), "#4A7FF2")
            draw = ImageDraw.Draw(image)
            font_path = None
            for f_name in ["courbd.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf", "FreeMonoBold.ttf"]:
                try:
                    font = ImageFont.truetype(f_name, 160)
                    font_path = f_name
                    break
                except IOError:
                    continue
            if not font_path:
                font = ImageFont.load_default()
            
            draw.text((128, 128), "MD", fill="white", font=font, anchor="mm")

            self.photo = ImageTk.PhotoImage(image)
            self.iconphoto(False, self.photo)
        except Exception as e:
            print(f"Error creating app icon: {e}")

    def create_widgets(self):
        self.close_icon = self.get_close_icon()
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

        # Theme toggle
        self.style.configure("TCheckbutton", font=("Segoe UI", 12))
        self.theme_var = tk.BooleanVar(value=False) # False for light, True for dark
        theme_toggle = ttk.Checkbutton(
            main_frame, 
            text="🌙", 
            variable=self.theme_var, 
            command=self.toggle_theme,
            bootstyle="round-toggle"
        )
        theme_toggle.place(relx=1.0, rely=0, x=-10, y=10, anchor="ne")

        # Left panel for the directory tree
        tree_frame = ttk.Frame(paned_window, padding="5")
        self.tree = ttk.Treeview(tree_frame, bootstyle="info", selectmode="extended")
        
        # Add a scrollbar to the treeview
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(expand=True, fill="both", side="left")
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        paned_window.add(tree_frame, weight=0)

        # Right panel for the content
        content_frame = ttk.Frame(paned_window, padding="5")
        
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(expand=True, fill="both")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.notebook.bind("<Button-3>", self.show_tab_context_menu)

        paned_window.add(content_frame, weight=1)

        # Font size controls
        font_control_frame = ttk.Frame(content_frame)
        font_control_frame.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        plus_button = ttk.Button(font_control_frame, text="+", width=3, command=self.increase_font_size, bootstyle="secondary")
        plus_button.pack(side="left", padx=2)

        minus_button = ttk.Button(font_control_frame, text="-", width=3, command=self.decrease_font_size, bootstyle="secondary")
        minus_button.pack(side="left")

    def get_close_icon(self):
        # Create a simple 'x' icon for closing tabs
        image = Image.new("RGBA", (16, 16), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.line((4, 4, 11, 11), fill="gray", width=2)
        draw.line((4, 11, 11, 4), fill="gray", width=2)
        return ImageTk.PhotoImage(image)

    def close_tab(self, file_to_close):
        if file_to_close in self.open_files:
            info = self.open_files.pop(file_to_close)
            
            # Gracefully destroy the HtmlFrame to stop background threads
            for widget in info["tab_frame"].winfo_children():
                if isinstance(widget, HtmlFrame):
                    widget.destroy()
            
            self.notebook.forget(info["tab_frame"])
            info["tab_frame"].destroy()

            # Clear the cache for the closed file
            if file_to_close in self.html_cache:
                del self.html_cache[file_to_close]

            if not self.notebook.tabs():
                self.current_file_path = None
            elif self.current_file_path == file_to_close:
                new_tab_id = self.notebook.tabs()[0]
                self.notebook.select(new_tab_id)
            
            if not self.open_files:
                self.show_single_view()

    def show_tab_context_menu(self, event):
        try:
            tab_id = self.notebook.identify(event.x, event.y)
            if not tab_id:
                return

            self.notebook.select(tab_id)
            
            file_path_to_close = None
            for path, info in self.open_files.items():
                if info["tab_id"] == tab_id:
                    file_path_to_close = path
                    break
            
            if file_path_to_close:
                context_menu = tk.Menu(self, tearoff=0)
                context_menu.add_command(label="Close Tab", command=lambda f=file_path_to_close: self.close_tab(f))
                context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error showing tab context menu: {e}")

    def toggle_theme(self):
        self.html_cache.clear() # Clear cache on theme change
        if self.theme_var.get():
            self.style.theme_use("darkly")
        else:
            self.style.theme_use("litera")
        self.refresh_html_view()

    def increase_font_size(self):
        self.font_size += 1
        self.refresh_html_view()

    def decrease_font_size(self):
        if self.font_size > 6:
            self.font_size -= 1
            self.refresh_html_view()

    def refresh_html_view(self):
        # For split view
        if isinstance(self.current_file_path, list) and len(self.current_file_path) == 2:
            self._load_content_into_frame(self.current_file_path[0], self.html_frame_left)
            self._load_content_into_frame(self.current_file_path[1], self.html_frame_right)
            return

        # For single tab view
        if self.current_file_path and self.current_file_path in self.open_files:
            try:
                info = self.open_files[self.current_file_path]
                tab_frame = info["tab_frame"]
                
                # Destroy existing HtmlFrame if it exists
                for widget in tab_frame.winfo_children():
                    if isinstance(widget, HtmlFrame):
                        widget.destroy()

                # Create a new one
                html_frame = HtmlFrame(tab_frame, messages_enabled=False)
                html_frame.pack(expand=True, fill="both", side="bottom")
                
                self._load_content_into_frame(self.current_file_path, html_frame)

            except (KeyError, tk.TclError) as e:
                print(f"Error refreshing view: {e}")

    def on_tab_change(self, event):
        try:
            selected_tab_id = self.notebook.select()
            if not selected_tab_id:
                self.current_file_path = None
                return

            new_file_path = None
            for path, info in self.open_files.items():
                if info["tab_id"] == selected_tab_id:
                    new_file_path = path
                    break
            
            if new_file_path:
                self.current_file_path = new_file_path
                self.refresh_html_view()

        except tk.TclError:
            self.current_file_path = None

    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title("About MDViewer")
        about_win.geometry("300x200")
        about_win.resizable(False, False)
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

    def _has_md_files_recursive(self, dir_path):
        for p in os.listdir(dir_path):
            pt = os.path.join(dir_path, p)
            if os.path.isdir(pt) and p not in self.ignore_dirs and not p.startswith('.'):
                if self._has_md_files_recursive(pt):
                    return True
            elif p.endswith(".md"):
                return True
        return False

    def _populate_tree_recursive(self, parent, dir_path):
        entries = sorted(os.listdir(dir_path), key=lambda x: (os.path.isfile(os.path.join(dir_path, x)), x))
        for p in entries:
            pt = os.path.join(dir_path, p)
            if os.path.isdir(pt) and p not in self.ignore_dirs and not p.startswith('.'):
                if self._has_md_files_recursive(pt):
                    node = self.tree.insert(parent, "end", text=p, open=False)
                    self._populate_tree_recursive(node, pt)
            elif p.endswith(".md"):
                self.tree.insert(parent, "end", text=p, values=[pt])

    def populate_tree(self, path):
        for i in self.tree.get_children():
            self.tree.delete(i)

        root_node = self.tree.insert("", "end", text=os.path.basename(path), open=True, values=[path])
        self._populate_tree_recursive(root_node, path)

    def on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        file_path_values = self.tree.item(item_id, "values")
        if file_path_values and file_path_values[0].endswith(".md"):
            self.show_single_view()
            self.show_file_content(file_path_values[0])

    def on_tree_right_click(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        md_files = []
        for item in selected_items:
            file_path_values = self.tree.item(item, "values")
            if file_path_values and file_path_values[0].endswith(".md"):
                md_files.append(file_path_values[0])

        if not md_files:
            return

        context_menu = tk.Menu(self, tearoff=0)
        if len(md_files) >= 1:
            context_menu.add_command(label="Open", command=lambda: self.open_selected_files(md_files))
        if len(md_files) == 2:
            context_menu.add_command(label="Compare", command=lambda: self.show_split_view(md_files[0], md_files[1]))
        
        context_menu.post(event.x_root, event.y_root)

    def open_selected_files(self, md_files):
        self.show_single_view()
        for file_path in md_files:
            self.show_file_content(file_path)

    def show_split_view(self, file_path1, file_path2):
        # Hide the notebook
        self.notebook.pack_forget()

        # Create a new PanedWindow for split view if it doesn't exist
        if not hasattr(self, 'split_paned_window'):
            self.split_paned_window = ttk.PanedWindow(self.notebook.master, orient="horizontal")
            self.split_paned_window.pack(expand=True, fill="both")

            self.html_frame_left = HtmlFrame(self.split_paned_window, messages_enabled=False)
            self.html_frame_right = HtmlFrame(self.split_paned_window, messages_enabled=False)
            
            self.split_paned_window.add(self.html_frame_left, weight=1)
            self.split_paned_window.add(self.html_frame_right, weight=1)
        else:
            self.split_paned_window.pack(expand=True, fill="both")


        self.current_file_path = [file_path1, file_path2] # Store both paths for split view
        self._load_content_into_frame(file_path1, self.html_frame_left)
        self._load_content_into_frame(file_path2, self.html_frame_right)

    def show_single_view(self):
        if hasattr(self, 'split_paned_window') and self.split_paned_window.winfo_ismapped():
            self.split_paned_window.pack_forget()
        self.notebook.pack(expand=True, fill="both")
        self.current_file_path = None # Reset for single view

    def _get_file_content(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return f"<h1>Error</h1><p>Failed to read file: {e}</p>"

    def _render_mermaid_diagram(self, code):
        try:
            m = mermaid_lib.Mermaid(code)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name
            m.to_png(temp_path)
            with open(temp_path, "rb") as f:
                png_data = f.read()
            os.remove(temp_path)
            img_base64 = base64.b64encode(png_data).decode('utf-8')
            return f'<img src="data:image/png;base64,{img_base64}">'
        except Exception as e:
            print(f"Mermaid rendering failed: {e}")
            return f"<pre>Error rendering Mermaid diagram. Please check the diagram syntax.<br>Details: {e}</pre>"

    def _process_mermaid_blocks(self, md_content):
        mermaid_images = {}
        def replace_block(match):
            code = match.group(1)
            placeholder = f"<!-- mermaid-placeholder-{len(mermaid_images)} -->"
            mermaid_images[placeholder] = self._render_mermaid_diagram(code)
            return placeholder
        
        content_with_placeholders = re.sub(r"```mermaid(.*?)```", replace_block, md_content, flags=re.DOTALL)
        
        for placeholder, img_html in mermaid_images.items():
            content_with_placeholders = content_with_placeholders.replace(placeholder, img_html)
            
        return content_with_placeholders

    def _convert_markdown_to_html(self, md_content):
        return markdown2.markdown(
            md_content,
            extras=["fenced-code-blocks", "tables", "cuddled-lists", "strike", "code-friendly"]
        )

    def _style_html_content(self, html_content):
        bg_color = "#303030" if self.theme_var.get() else "#ffffff"
        text_color = "#f0f0f0" if self.theme_var.get() else "#24292e"
        border_color = "#505050" if self.theme_var.get() else "#eaecef"
        pre_bg_color = "#202020" if self.theme_var.get() else "#f6f8fa"
        blockquote_color = "#909090" if self.theme_var.get() else "#6a737d"
        blockquote_border_color = "#505050" if self.theme_var.get() else "#dfe2e5"

        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
                    font-size: {self.font_size}pt;
                    line-height: 1.6;
                    color: {text_color};
                    background-color: {bg_color};
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
                h1 {{ font-size: 2em; border-bottom: 1px solid {border_color}; padding-bottom: .3em;}}
                h2 {{ font-size: 1.5em; border-bottom: 1px solid {border_color}; padding-bottom: .3em;}}
                h3 {{ font-size: 1.25em; }}
                a {{ color: #0366d6; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                pre {{ background-color: {pre_bg_color}; padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; border-radius: 6px; }}
                code {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace; font-size: 85%; }}
                pre > code {{ font-size: 100%; }}
                table {{ border-collapse: collapse; width: 100%; display: block; overflow: auto;}}
                th, td {{ border: 1px solid {border_color}; padding: 6px 13px; }}
                th {{ font-weight: 600; background-color: {pre_bg_color}; }}
                img {{ max-width: 100%; height: auto; background-color: {bg_color}; }}
                blockquote {{ color: {blockquote_color}; border-left: .25em solid {blockquote_border_color}; padding: 0 1em; margin-left: 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                {html_content}
            </div>
        </body>
        </html>
        """

    def _load_content_into_frame(self, file_path, target_html_frame):
        if file_path in self.html_cache:
            styled_html = self.html_cache[file_path]
        else:
            md_content = self._get_file_content(file_path)
            md_with_mermaid = self._process_mermaid_blocks(md_content)
            html_content = self._convert_markdown_to_html(md_with_mermaid)
            styled_html = self._style_html_content(html_content)
            self.html_cache[file_path] = styled_html
        
        target_html_frame.load_html(styled_html)

    def show_file_content(self, file_path, switch_to_tab=True):
        if file_path in self.open_files:
            if switch_to_tab:
                self.notebook.select(self.open_files[file_path]["tab_id"])
            return

        tab_frame = ttk.Frame(self.notebook)
        
        # Custom frame for tab title and close button
        title_frame = ttk.Frame(tab_frame)
        title_frame.pack(fill="x", expand=True, side="top")
        
        tab_label = ttk.Label(title_frame, text=os.path.basename(file_path))
        tab_label.pack(side="left", fill="x", expand=True)
        
        close_button = ttk.Button(title_frame, text='X', bootstyle="danger-link",
                                  command=lambda f=file_path: self.close_tab(f))
        close_button.pack(side="right")

        self.notebook.add(tab_frame, text=os.path.basename(file_path))
        tab_id = self.notebook.tabs()[-1]

        self.open_files[file_path] = {
            "tab_id": tab_id,
            "tab_frame": tab_frame,
        }
        
        if switch_to_tab:
            self.notebook.select(tab_id)
        
        if self.current_file_path == file_path:
            self.refresh_html_view()

if __name__ == "__main__":
    app = App()
    app.mainloop()
