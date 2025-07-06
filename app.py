import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import markdown2
import mermaid as mermaid_lib
from io import BytesIO
from PIL import Image, ImageTk
import base64

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MD Viewer")
        self.geometry("1024x768")

        # Create the main layout
        self.create_widgets()

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

    def show_about(self):
        about_message = "MDViewer\n\nCreated by @rohanpls\nhttps://github.com/rohanpls"
        tk.messagebox.showinfo("About MDViewer", about_message)

        # Main container
        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(expand=True, fill="both")

        # Paned window for resizable panels
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(expand=True, fill="both")

        # Left panel for the directory tree
        self.tree_frame = ttk.Frame(paned_window, padding="5")
        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.pack(expand=True, fill="both")
        self.tree.bind("<Double-1>", self.on_tree_select)
        paned_window.add(self.tree_frame, weight=1)

        # Right panel for the content
        self.content_frame = ttk.Frame(paned_window, padding="5")
        self.content_text = tk.Text(self.content_frame, wrap="word", state="disabled", padx=10, pady=10)
        self.content_text.pack(expand=True, fill="both")
        paned_window.add(self.content_frame, weight=3)

    def open_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.populate_tree(path)

    def populate_tree(self, path):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        self.path = path
        
        def _populate_tree(parent, path):
            for p in os.listdir(path):
                pt = os.path.join(path, p)
                if os.path.isdir(pt):
                    node = self.tree.insert(parent, "end", text=p, open=False)
                    _populate_tree(node, pt)
                elif p.endswith(".md"):
                    self.tree.insert(parent, "end", text=p, values=[pt])

        root_node = self.tree.insert("", "end", text=os.path.basename(path), open=True, values=[path])
        _populate_tree(root_node, path)

    def on_tree_select(self, event):
        selected_item = self.tree.selection()[0]
        file_path = self.tree.item(selected_item, "values")
        if file_path and file_path[0].endswith(".md"):
            self.show_file_content(file_path[0])

    def show_file_content(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            
            self.content_text.config(state="normal")
            self.content_text.delete(1.0, tk.END)

            # Find and render Mermaid diagrams
            import re
            mermaid_blocks = re.findall(r"```mermaid(.*?)```", md_content, re.DOTALL)
            
            if mermaid_blocks:
                parts = re.split(r"```mermaid.*?```", md_content, flags=re.DOTALL)
                for i, part in enumerate(parts):
                    html_part = markdown2.markdown(part, extras=["fenced-code-blocks", "tables"])
                    self.insert_html(html_part)
                    
                    if i < len(mermaid_blocks):
                        self.insert_mermaid_diagram(mermaid_blocks[i])
            else:
                html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables"])
                self.insert_html(html_content)

            self.content_text.config(state="disabled")

        except Exception as e:
            self.content_text.config(state="normal")
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, f"Error: {e}")
            self.content_text.config(state="disabled")

    def insert_html(self, html):
        # This is still a simplified rendering. A proper HTML widget would be better.
        self.content_text.insert(tk.END, html)


    def insert_mermaid_diagram(self, code):
        try:
            m = mermaid_lib.Mermaid(code)
            # The library uses mermaid.ink to render, which returns PNG data
            png_data = m.to_png()
            
            image = Image.open(BytesIO(png_data))
            photo = ImageTk.PhotoImage(image)
            
            # Keep a reference to the image to prevent garbage collection
            self.content_text.image_create(tk.END, image=photo)
            self.content_text.insert(tk.END, '\n') # Add a newline after the image
            self.content_text.image = photo

        except Exception as e:
            self.content_text.insert(tk.END, f"\n[Mermaid Rendering Failed: {e}]\n")

if __name__ == "__main__":
    app = App()
    app.mainloop()
