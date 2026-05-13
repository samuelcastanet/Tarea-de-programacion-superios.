# Que el homnisalla nos agarre confesaods
import os
import json
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Thread
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import matplotlib
# NO tocar esto benja,Tipo, si tican esto los mato
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
@dataclass(slots=True)
class GraphData:
    chart_type: str
    title: str
    x_label: str
    y_label: str
    x_data: np.ndarray
    y_data: np.ndarray
    labels: list[str]

class FileService:

    @staticmethod
    def ensure_directory(directory: str | Path) -> Path:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def safe_filename(name: str) -> str:
        # estos caracteres truena en windows
        invalid = '<>:"/\\|?*'
        cleaned = "".join("_" if c in invalid else c for c in name.strip())
        cleaned = cleaned.replace(" ", "_").strip("._")
        return cleaned or "grafica"  # si queda vacio, ponemos algo por default

    @staticmethod
    def build_paths(directory: str | Path, base_name: str) -> tuple[Path, Path, str]:
        out_dir = FileService.ensure_directory(directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_base = FileService.safe_filename(base_name)

        image_path = out_dir / f"{safe_base}_{timestamp}.png"
        report_path = out_dir / f"{safe_base}_{timestamp}.txt"

        return image_path, report_path, timestamp

    @staticmethod
    def save_text_report(report_path: str | Path, graph_data: GraphData, image_path: Path) -> Path:
        # TODO: algun dia hacer esto en PDF pero por ahora txt esta bien
        report_path = Path(report_path)
        with report_path.open("w", encoding="utf-8") as f:
            f.write("REPORTE DE GRÁFICA\n")
            f.write("=" * 40 + "\n")
            f.write(f"Tipo: {graph_data.chart_type}\n")
            f.write(f"Título: {graph_data.title}\n")
            f.write(f"Eje X: {graph_data.x_label}\n")
            f.write(f"Eje Y: {graph_data.y_label}\n")
            f.write(f"Datos X: {graph_data.x_data.tolist()}\n")
            f.write(f"Datos Y: {graph_data.y_data.tolist()}\n")
            f.write(f"Etiquetas: {graph_data.labels}\n")
            f.write(f"Imagen: {image_path}\n")
            f.write(f"Fecha: {datetime.now().isoformat(timespec='seconds')}\n")
        return report_path

class PlotService:

    @staticmethod
    def draw_graph(ax, graph_data: GraphData):
        chart = graph_data.chart_type.strip().lower()
        x = graph_data.x_data
        y = graph_data.y_data
        labels = graph_data.labels

        accent = "#d4af37"
        text_color = "#f2f2f2"
        grid_color = "#3a4668"

        ax.set_facecolor("#111831")
#non stop https://www.youtube.com/watch?v=JXvRD32Tkhw&list=RDJXvRD32Tkhw&start_radio=1

        if chart == "barras":
            xticks = labels if labels else [str(i + 1) for i in range(len(y))]
            ax.bar(xticks, y, color=accent, edgecolor=text_color, linewidth=0.8)
            ax.tick_params(axis="x", rotation=35)  # rotar pa que no se encimen

        elif chart in ("línea", "linea", "tradicional"):
            ax.plot(x, y, marker="o", linewidth=2.0, color=accent)

        elif chart == "pie":
            pie_labels = labels if labels else [f"Parte {i + 1}" for i in range(len(y))]
            ax.pie(
                y,
                labels=pie_labels,
                autopct="%1.1f%%",
                startangle=90,
                textprops={"color": text_color},
                wedgeprops={"edgecolor": "#0b1020", "linewidth": 1.0},
            )
            ax.axis("equal")

        elif chart in ("dispersión", "disersion", "scatter"):
            ax.scatter(x, y, s=55, color=accent, edgecolors=text_color, linewidths=0.6)

        elif chart == "histograma":
            bins = min(12, max(1, len(y)))  
            ax.hist(y, bins=bins, color=accent, edgecolor=text_color, alpha=0.95)

        else:
            raise ValueError("Tipo de gráfica no soportado.")

        ax.set_title(graph_data.title, fontsize=14, fontweight="bold", color=text_color, pad=12)
        ax.set_xlabel(graph_data.x_label, color=text_color)
        ax.set_ylabel(graph_data.y_label, color=text_color)
        ax.tick_params(colors=text_color)
        ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35, color=grid_color)

        for spine in ax.spines.values():
            spine.set_color("#6b7280")
            spine.set_linewidth(0.8)

    @staticmethod
    def build_figure(graph_data: GraphData) -> Figure:
        fig = Figure(figsize=(7.5, 5.0), dpi=110, facecolor="#0b1020")
        ax = fig.add_subplot(111)
        PlotService.draw_graph(ax, graph_data)
        fig.tight_layout()
        return fig


#clase principal, aqui vive todo el infierno de la UI
class GraphGeneratorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hamilton Graph Studio")
        self.root.geometry("1280x760")
        self.root.minsize(1120, 680)
        self.root.configure(bg="#080d1a")

        self.output_dir = Path.cwd() / "graficas_guardadas"

        self.current_figure = None
        self.current_canvas = None  
        self.last_data: GraphData | None = None

        self._setup_style()
        self._build_ui()
        self._crear_canvas_vista()
        self._update_preview()

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass  

        bg = "#080d1a"
        panel = "#10182c"
        panel2 = "#131d34"
        text = "#f4f4f4"
        accent = "#d4af37"  # dorado

        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("Card.TFrame", background=panel2)
        style.configure("TLabel", background=bg, foreground=text, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=accent, font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=bg, foreground="#c7cbd6", font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=panel, foreground=accent, font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("TButton", background=[("active", "#1d2c52")], foreground=[("active", text)])

        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#0b1020",
            font=("Segoe UI", 10, "bold"),
            padding=9,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#e0bf52")],
            foreground=[("active", "#0b1020")],
        )

        style.configure(
            "TEntry",
            fieldbackground="#0d1427",
            background="#0d1427",
            foreground=text,
            insertcolor=text,
            bordercolor="#2a3555",
            lightcolor="#2a3555",
            darkcolor="#2a3555",
            padding=5,
        )
        style.configure(
            "TCombobox",
            fieldbackground="#0d1427",
            background="#0d1427",
            foreground=text,
            arrowcolor=text,
            padding=5,
        )
        style.map("TCombobox", fieldbackground=[("readonly", "#0d1427")], foreground=[("readonly", text)])

        self.bg = bg
        self.panel = panel
        self.panel2 = panel2
        self.text = text
        self.accent = accent

    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=18, pady=(14, 10))

        ttk.Label(top, text="Hamilton Graph Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            top,
            text="Interfaz oscura, rápida y pensada para crear, previsualizar y guardar gráficas sin pasos extra.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        self.left_panel = ttk.Frame(main, style="Panel.TFrame", padding=16)
        self.left_panel.pack(side="left", fill="y", padx=(0, 14))

        self.right_panel = ttk.Frame(main, style="Panel.TFrame", padding=14)
        self.right_panel.pack(side="right", fill="both", expand=True)

        # la lista de bariables quiero mimir
        self.tipoo_var = tk.StringVar(value="Barras")
        self.tituloo_var = tk.StringVar(value="Mi Gráfica")
        self.ejee_x_var = tk.StringVar(value="Eje X")
        self.ejee_y_var = tk.StringVar(value="Eje Y")
        self.datos_x_var = tk.StringVar(value="1,2,3,4")
        self.datos_y_var = tk.StringVar(value="4,7,1,9")
        self.etiquetass_var = tk.StringVar(value="A,B,C,D")
        self.nombree_var = tk.StringVar(value="grafica_guardada")

        self._add_header(self.left_panel, "Configuración")
        self._add_field(self.left_panel, "Tipo de gráfica", combobox=True)
        self._add_field(self.left_panel, "Título", self.tituloo_var)
        self._add_field(self.left_panel, "Etiqueta X", self.ejee_x_var)
        self._add_field(self.left_panel, "Etiqueta Y", self.ejee_y_var)
        self._add_field(self.left_panel, "Datos X (coma)", self.datos_x_var)
        self._add_field(self.left_panel, "Datos Y (coma)", self.datos_y_var)
        self._add_field(self.left_panel, "Etiquetas (coma)", self.etiquetass_var)
        self._add_field(self.left_panel, "Nombre base archivo", self.nombree_var)

        btns = ttk.Frame(self.left_panel, style="Panel.TFrame")
        btns.pack(fill="x", pady=(14, 8))

        ttk.Button(btns, text="Actualizar vista previa", style="Accent.TButton", command=self._update_preview).pack(
            fill="x", pady=(0, 8)
        )
        ttk.Button(btns, text="Generar y guardar", command=self.generate_graph).pack(fill="x", pady=(0, 8))
        ttk.Button(btns, text="Elegir carpeta", command=self.choose_folder).pack(fill="x", pady=(0, 8))
        ttk.Button(btns, text="Limpiar", command=self.clear_fields).pack(fill="x")

        info_box = ttk.Frame(self.left_panel, style="Card.TFrame", padding=12)
        info_box.pack(fill="x", pady=(14, 0))
        ttk.Label(info_box, text="Salida", style="Section.TLabel").pack(anchor="w")
        self.estado_var = tk.StringVar(value=f"Carpeta: {self.output_dir}")
        ttk.Label(info_box, textvariable=self.estado_var, background=self.panel2, wraplength=300).pack(
            anchor="w", pady=(6, 0)
        )

        log_box = ttk.Frame(self.left_panel, style="Card.TFrame", padding=10)
        log_box.pack(fill="both", expand=True, pady=(14, 0))
        ttk.Label(log_box, text="Registro", style="Section.TLabel").pack(anchor="w")

        self.text_log = tk.Text(
            log_box,
            height=11,
            bg="#0b1020",
            fg=self.text,
            insertbackground=self.text,
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
        )
        self.text_log.pack(fill="both", expand=True, pady=(8, 0))

        preview_box = ttk.Frame(self.right_panel, style="Card.TFrame", padding=10)
        preview_box.pack(fill="both", expand=True)
        ttk.Label(preview_box, text="Vista previa", style="Section.TLabel").pack(anchor="w")

        self.preview_area = ttk.Frame(preview_box, style="Card.TFrame")
        self.preview_area.pack(fill="both", expand=True, pady=(8, 0))

        self.log("Programa listo.")

    def _add_header(self, parent, texto: str):
        header = ttk.Frame(parent, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=texto, style="Section.TLabel").pack(anchor="w")

    def _add_field(self, parent, etiqueta: str, variable=None, combobox: bool = False):
        cont = ttk.Frame(parent, style="Panel.TFrame")
        cont.pack(fill="x", pady=(0, 8))
        ttk.Label(cont, text=etiqueta, background=self.panel).pack(anchor="w", pady=(0, 4))

        if combobox:
            self.chart_combo = ttk.Combobox(
                cont,
                textvariable=self.tipoo_var,
                values=["Barras", "Línea", "Pie", "Dispersión", "Histograma"],
                state="readonly",
            )
            self.chart_combo.pack(fill="x")
            self.chart_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())
        else:
            entry = ttk.Entry(cont, textvariable=variable)
            entry.pack(fill="x")
            entry.bind("<Return>", lambda e: self._update_preview()) 

    def _crear_canvas_vista(self):
        self.preview_fig = Figure(figsize=(7.3, 5.2), dpi=110, facecolor="#0b1020")
        self.preview_ax = self.preview_fig.add_subplot(111)
        self.graficaa_canvas = FigureCanvasTkAgg(self.preview_fig, master=self.preview_area)
        self.graficaa_canvas.get_tk_widget().pack(fill="both", expand=True)

    def log(self, msg: str):
        self.text_log.insert("end", msg + "\n")
        self.text_log.see("end")

    def _ui_log(self, msg: str):
        self.root.after(0, self.log, msg)

    def choose_folder(self):
        try:
            selected = filedialog.askdirectory(title="Selecciona carpeta de salida")
            if selected:
                self.output_dir = Path(selected)
                FileService.ensure_directory(self.output_dir)
                self.estado_var.set(f"Carpeta: {self.output_dir}")
                self.log(f"Carpeta seleccionada: {self.output_dir}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_fields(self):
        self.tipoo_var.set("Barras")
        self.tituloo_var.set("Mi Gráfica")
        self.ejee_x_var.set("Eje X")
        self.ejee_y_var.set("Eje Y")
        self.datos_x_var.set("1,2,3,4")
        self.datos_y_var.set("4,7,1,9")
        self.etiquetass_var.set("A,B,C,D")
        self.nombree_var.set("grafica_guardada")
        self._update_preview()
        self.log("Campos restablecidos.")

    def _parse_numbers(self, raw: str) -> np.ndarray:
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if not items:
            return np.array([], dtype=float)
        try:
            return np.asarray([float(x.replace(" ", "")) for x in items], dtype=float)
        except ValueError as exc:
            raise ValueError("Los datos numéricos deben estar separados por comas y ser válidos.") from exc

    def _parse_labels(self, raw: str) -> list[str]:
        return [x.strip() for x in raw.split(",") if x.strip()]

    def collect_data(self) -> GraphData:
        chart_type = self.tipoo_var.get().strip()
        title = self.tituloo_var.get().strip() or "Mi Gráfica"
        x_label = self.ejee_x_var.get().strip() or "Eje X"
        y_label = self.ejee_y_var.get().strip() or "Eje Y"

        x_data = self._parse_numbers(self.datos_x_var.get())
        y_data = self._parse_numbers(self.datos_y_var.get())
        labels = self._parse_labels(self.etiquetass_var.get())

        if y_data.size == 0:
            raise ValueError("Debes ingresar al menos un dato en Y.")

        chart = chart_type.lower()

        if chart == "pie":
            if y_data.size < 2:
                raise ValueError("La gráfica de pastel necesita al menos 2 valores.")
            x_data = np.arange(1, y_data.size + 1, dtype=float)

        elif chart == "histograma":
            # el histo no necesita x realmente
            x_data = np.arange(1, y_data.size + 1, dtype=float)

        else:
            if x_data.size == 0:
                x_data = np.arange(1, y_data.size + 1, dtype=float)

            longeitudd = min(len(x_data), len(y_data))  # longitud, la escribi mal desde el inicio y ya me acostumbre
            x_data = x_data[:longeitudd]
            y_data = y_data[:longeitudd]

        if labels:
            labels = labels[: len(y_data)]

        return GraphData(
            chart_type=chart_type,
            title=title,
            x_label=x_label,
            y_label=y_label,
            x_data=x_data,
            y_data=y_data,
            labels=labels,
        )

    def _draw_preview(self, data: GraphData):
        self.preview_fig.clf()
        self.preview_ax = self.preview_fig.add_subplot(111)
        PlotService.draw_graph(self.preview_ax, data)
        self.preview_fig.tight_layout()
        self.graficaa_canvas.draw_idle()

    def _show_empty_preview(self):
        self.preview_ax.clear()
        self.preview_ax.set_facecolor("#111831")
        self.preview_ax.text(
            0.5, 0.5,
            "No hay vista previa disponible",
            ha="center", va="center",
            color="#f2f2f2",
            fontsize=12,
            transform=self.preview_ax.transAxes,
        )
        self.preview_ax.set_xticks([])
        self.preview_ax.set_yticks([])
        self.preview_fig.tight_layout()
        self.graficaa_canvas.draw_idle()

    def _update_preview(self):
        try:
            data = self.collect_data()
            self.last_data = data
            self._draw_preview(data)
            self.log(f"Vista previa actualizada ({data.chart_type}).")
        except Exception as e:
            self.log(f"No se pudo actualizar la vista previa: {e}")
            self._show_empty_preview()

    def _save_worker(self, payload: dict):
        try:
            data = GraphData(
                chart_type=payload["chart_type"],
                title=payload["title"],
                x_label=payload["x_label"],
                y_label=payload["y_label"],
                x_data=np.asarray(payload["x_data"], dtype=float),
                y_data=np.asarray(payload["y_data"], dtype=float),
                labels=list(payload["labels"]),
            )

            out_dir = FileService.ensure_directory(payload["output_dir"])
            image_path, report_path, _ = FileService.build_paths(out_dir, payload["base_name"])

            fig = PlotService.build_figure(data)
            fig.savefig(image_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
            report_path = FileService.save_text_report(report_path, data, image_path)

            self._ui_log(f"Guardado: {image_path.name}")
            self._ui_log(f"Reporte: {report_path.name}")

            self.root.after(
                0,
                lambda: messagebox.showinfo("Éxito", "La gráfica se generó y guardó correctamente."),
            )
        except Exception:
            err = traceback.format_exc()
            self._ui_log("ERROR EN GUARDADO:\n" + err)
            self.root.after(0, lambda: messagebox.showerror("Error", "No se pudo guardar la gráfica."))

# quiero dormir pero esta dificil https://www.youtube.com/watch?v=hFpjyBPclAY&list=RDhFpjyBPclAY&start_radio=1
    def generate_graph(self):
        try:
            data = self.collect_data()
            self.last_data = data

            FileService.ensure_directory(self.output_dir)
            payload = {
                "chart_type": data.chart_type,
                "title": data.title,
                "x_label": data.x_label,
                "y_label": data.y_label,
                "x_data": data.x_data.tolist(),
                "y_data": data.y_data.tolist(),
                "labels": data.labels,
                "output_dir": str(self.output_dir),
                "base_name": self.nombree_var.get().strip() or data.title,
            }

            hilo = Thread(target=self._save_worker, args=(payload,), daemon=True)
            hilo.start()
            self.log("Guardado iniciado en segundo plano...")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"ERROR: {e}")

def main():
    try:
        root = tk.Tk()
        app = GraphGeneratorApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error fatal: {e}")

if __name__ == "__main__":
    main()
