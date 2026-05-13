#el omnisalla nos agarre confesados si el codigofalla
import os
import json
import traceback
import tempfile
import subprocess
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Process
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# MODELO de datos para la grafica
@dataclass
class GraphData:
    chart_type: str
    title: str
    x_label: str
    y_label: str
    x_data: np.ndarray
    y_data: np.ndarray
    labels: list

# SERVICIOS para manejo de archivos
class FileService:
    @staticmethod
    def ensure_directory(directory: str) -> str:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            else:
                print("Carpeta existente")
            return directory
        except Exception as e:
            raise RuntimeError(f"No se pudo crear/verificar el directorio: {e}")

    @staticmethod
    def safe_filename(name: str) -> str:
        invalid = '<>:"/\\|?*'
        clean = "".join("_" if c in invalid else c for c in name.strip())
        return clean if clean else "grafica"

    @staticmethod
    def save_text_report(directory: str, graph_data: GraphData, image_path: str) -> str:
        try:
            FileService.ensure_directory(directory)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = FileService.safe_filename(graph_data.title)
            txt_path = os.path.join(directory, f"{base}_{timestamp}.txt")

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("REPORTE DE GRÁFICA\n")
                f.write("=" * 30 + "\n")
                f.write(f"Tipo: {graph_data.chart_type}\n")
                f.write(f"Título: {graph_data.title}\n")
                f.write(f"Etiqueta X: {graph_data.x_label}\n")
                f.write(f"Etiqueta Y: {graph_data.y_label}\n")
                f.write(f"Datos X: {graph_data.x_data.tolist()}\n")
                f.write(f"Datos Y: {graph_data.y_data.tolist()}\n")
                f.write(f"Labels: {graph_data.labels}\n")
                f.write(f"Imagen guardada en: {image_path}\n")
                f.write(f"Fecha: {datetime.now().isoformat()}\n")

            return txt_path
        except Exception as e:
            raise RuntimeError(f"No se pudo guardar el reporte: {e}")


class PlotService:
    @staticmethod
    def build_figure(graph_data: GraphData) -> Figure:
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        chart = graph_data.chart_type.lower()
        x = graph_data.x_data
        y = graph_data.y_data
        labels = graph_data.labels

        if chart == "barras":
            ax.bar(labels if labels else range(len(y)), y)
            ax.set_xticks(range(len(y)))
            ax.set_xticklabels(labels if labels else [str(i) for i in range(len(y))], rotation=45, ha="right")

        elif chart == "tradicional":
            ax.plot(x, y, marker="o")

        elif chart == "pie":
            # En pie, solo usamos los valores Y; las etiquetas son los labels
            pie_labels = labels if labels else [f"Parte {i+1}" for i in range(len(y))]
            ax.pie(y, labels=pie_labels, autopct="%1.1f%%")
            ax.axis("equal")

        elif chart == "dispersión":
            ax.scatter(x, y)

        elif chart == "histograma":
            ax.hist(y, bins=min(10, max(1, len(y))))

        else:
            raise ValueError("Tipo de gráfica no soportado")

        ax.set_title(graph_data.title)
        ax.set_xlabel(graph_data.x_label)
        ax.set_ylabel(graph_data.y_label)
        fig.tight_layout()
        return fig

# TRABAJADOR EN PROCESO DAEMON un programa informático diseñado para ejecutarse continuamente en segundo plano Benja y random tomen nota
def worker_generate_and_save(payload: dict):
    """Proceso hijo daemon: genera y guarda imagen + texto."""
    try:
        data = GraphData(
            chart_type=payload["chart_type"],
            title=payload["title"],
            x_label=payload["x_label"],
            y_label=payload["y_label"],
            x_data=np.array(payload["x_data"], dtype=float),
            y_data=np.array(payload["y_data"], dtype=float),
            labels=payload["labels"],
        )

        out_dir = payload["output_dir"]
        FileService.ensure_directory(out_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = FileService.safe_filename(data.title)
        image_path = os.path.join(out_dir, f"{base}_{timestamp}.png")

        fig = PlotService.build_figure(data)
        fig.savefig(image_path)

        report_path = FileService.save_text_report(out_dir, data, image_path)

        print(f"GRÁFICA GUARDADA: {image_path}")
        print(f"REPORTE GUARDADO: {report_path}")
    except Exception:
        print("ERROR EN PROCESO HIJO:")
        traceback.print_exc()


class ProcessService:
    @staticmethod
    def run_daemon_task(payload: dict):
        try:
            p = Process(target=worker_generate_and_save, args=(payload,), daemon=True)
            p.start()
            return p
        except Exception as e:
            raise RuntimeError(f"No se pudo iniciar el proceso daemon: {e}")

    @staticmethod
    def run_subprocess_helper(payload: dict):
        """
        Extra: usa subprocess para lanzar un script temporal.
        El proceso 'daemon' real se hace con multiprocessing.Process.
        subprocess no tiene atributo daemon, por eso se usa aquí solo como proceso externo.
        """
        try:
            script = f"""
import json
import numpy as np
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure

payload = json.loads(r'''{json.dumps(payload)}''')

output_dir = Path(payload['output_dir'])
output_dir.mkdir(parents=True, exist_ok=True)

def safe(name):
    invalid = '<>:"/\\|?*'
    return ''.join('_' if c in invalid else c for c in name.strip()) or 'grafica'

chart_type = payload['chart_type'].lower()
title = payload['title']
x_label = payload['x_label']
y_label = payload['y_label']
x = np.array(payload['x_data'], dtype=float)
y = np.array(payload['y_data'], dtype=float)
labels = payload['labels']

fig = Figure(figsize=(6,4), dpi=100)
ax = fig.add_subplot(111)

if chart_type == 'barras':
    ax.bar(labels if labels else range(len(y)), y)
    ax.set_xticks(range(len(y)))
    ax.set_xticklabels(labels if labels else [str(i) for i in range(len(y))], rotation=45, ha='right')
elif chart_type == 'tradicional':
    ax.plot(x, y, marker='o')
elif chart_type == 'pie':
    ax.pie(y, labels=labels if labels else [f'Parte {{i+1}}' for i in range(len(y))], autopct='%1.1f%%')
    ax.axis('equal')
elif chart_type == 'dispersión':
    ax.scatter(x, y)
elif chart_type == 'histograma':
    ax.hist(y, bins=min(10, max(1, len(y))))
else:
    raise ValueError('Tipo no soportado')

ax.set_title(title)
ax.set_xlabel(x_label)
ax.set_ylabel(y_label)
fig.tight_layout()

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
base = safe(title)
img = output_dir / f'{{base}}_{{ts}}.png'
fig.savefig(img)

report = output_dir / f'{{base}}_{{ts}}.txt'
with open(report, 'w', encoding='utf-8') as f:
    f.write(f'Tipo: {{chart_type}}\nTitulo: {{title}}\nImagen: {{img}}\n')
print(img)
print(report)
"""
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write(script)
                temp_path = tmp.name

            result = subprocess.run(["python", temp_path], capture_output=True, text=True)
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return result
        except Exception as e:
            raise RuntimeError(f"Error usando subprocess: {e}")


# Esta parte se encarga de los graficos

class GraphGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Gráficas")
        self.root.geometry("1100x700")

        self.output_dir = os.path.join(os.getcwd(), "graficas_guardadas")
        self.current_figure = None
        self.current_canvas = None
        self.last_data = None

        self._build_ui()
        self._update_preview()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # Variables
        self.chart_type = tk.StringVar(value="Barras")
        self.title_var = tk.StringVar(value="Mi Gráfica")
        self.x_label_var = tk.StringVar(value="Eje X")
        self.y_label_var = tk.StringVar(value="Eje Y")
        self.x_data_var = tk.StringVar(value="1,2,3,4")
        self.y_data_var = tk.StringVar(value="4,7,1,9")
        self.labels_var = tk.StringVar(value="A,B,C,D")
        self.filename_var = tk.StringVar(value="grafica_guardada")

        # Controles
        ttk.Label(left, text="Tipo de gráfica").pack(anchor="w")
        self.chart_combo = ttk.Combobox(
            left,
            textvariable=self.chart_type,
            values=["Barras", "Tradicional", "Pie", "Dispersión", "Histograma"],
            state="readonly",
            width=22,
        )
        self.chart_combo.pack(fill="x", pady=(0, 8))
        self.chart_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        self._add_entry(left, "Título", self.title_var)
        self._add_entry(left, "Etiqueta X", self.x_label_var)
        self._add_entry(left, "Etiqueta Y", self.y_label_var)
        self._add_entry(left, "Datos X (separados por coma)", self.x_data_var)
        self._add_entry(left, "Datos Y (separados por coma)", self.y_data_var)
        self._add_entry(left, "Labels (separados por coma)", self.labels_var)
        self._add_entry(left, "Nombre base archivo", self.filename_var)

        ttk.Button(left, text="Actualizar vista previa", command=self._update_preview).pack(fill="x", pady=(10, 4))
        ttk.Button(left, text="Generar y guardar", command=self.generate_graph).pack(fill="x", pady=4)
        ttk.Button(left, text="Elegir carpeta", command=self.choose_folder).pack(fill="x", pady=4)
        ttk.Button(left, text="Limpiar", command=self.clear_fields).pack(fill="x", pady=4)

        self.status = tk.StringVar(value=f"Carpeta de salida: {self.output_dir}")
        ttk.Label(left, textvariable=self.status, wraplength=260).pack(anchor="w", pady=(12, 0))

        # Vista previa
        preview_frame = ttk.LabelFrame(right, text="Vista previa", padding=10)
        preview_frame.pack(fill="both", expand=True)
        self.preview_container = preview_frame

        self.text_log = tk.Text(right, height=8)
        self.text_log.pack(fill="x", pady=(10, 0))
        self.log("Programa listo.")

    def _add_entry(self, parent, label, variable):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=variable, width=32).pack(fill="x")

    def log(self, msg: str):
        self.text_log.insert("end", msg + "\n")
        self.text_log.see("end")

    def choose_folder(self):
        try:
            selected = filedialog.askdirectory(title="Selecciona carpeta de salida")
            if selected:
                self.output_dir = selected
                FileService.ensure_directory(self.output_dir)
                self.status.set(f"Carpeta de salida: {self.output_dir}")
                self.log(f"Carpeta seleccionada: {self.output_dir}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_fields(self):
        try:
            self.title_var.set("Mi Gráfica")
            self.x_label_var.set("Eje X")
            self.y_label_var.set("Eje Y")
            self.x_data_var.set("1,2,3,4")
            self.y_data_var.set("4,7,1,9")
            self.labels_var.set("A,B,C,D")
            self.filename_var.set("grafica_guardada")
            self.chart_type.set("Barras")
            self._update_preview()
            self.log("Campos restablecidos.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _parse_list(self, raw: str, force_float: bool = True):
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if force_float:
            return np.array([float(x) for x in items], dtype=float)
        return items

    def collect_data(self) -> GraphData:
        try:
            x_data = self._parse_list(self.x_data_var.get(), force_float=True)
            y_data = self._parse_list(self.y_data_var.get(), force_float=True)
            labels = self._parse_list(self.labels_var.get(), force_float=False)

            if len(x_data) == 0 or len(y_data) == 0:
                raise ValueError("Debes ingresar al menos un dato en X y Y.")

            # Ajuste simple para que no fallen las gráficas con longitudes distintas
            min_len = min(len(x_data), len(y_data))
            x_data = x_data[:min_len]
            y_data = y_data[:min_len]
            labels = labels[:min_len] if labels else []

            if self.chart_type.get() == "Pie" and len(y_data) < 2:
                raise ValueError("La gráfica de pastel requiere al menos 2 valores.")

            return GraphData(
                chart_type=self.chart_type.get(),
                title=self.title_var.get().strip(),
                x_label=self.x_label_var.get().strip(),
                y_label=self.y_label_var.get().strip(),
                x_data=x_data,
                y_data=y_data,
                labels=labels,
            )
        except ValueError as e:
            raise ValueError(f"Error en los datos: {e}")
        except Exception as e:
            raise RuntimeError(f"No se pudieron leer los datos: {e}")

    def _update_preview(self):
        try:
            data = self.collect_data()
            self.last_data = data
            fig = PlotService.build_figure(data)
            self._show_figure(fig)
            self.log(f"Vista previa actualizada ({data.chart_type}).")
        except Exception as e:
            self.log(f"No se pudo actualizar la vista previa: {e}")
            self._show_empty_preview()

    def _show_empty_preview(self):
        for widget in self.preview_container.winfo_children():
            widget.destroy()
        label = ttk.Label(self.preview_container, text="No hay vista previa disponible.")
        label.pack(expand=True)

    def _show_figure(self, fig: Figure):
        for widget in self.preview_container.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.preview_container)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)
        self.current_figure = fig
        self.current_canvas = canvas

    def generate_graph(self):
        try:
            data = self.collect_data()
            self.last_data = data

            # Asegurar carpeta
            FileService.ensure_directory(self.output_dir)

            # Guardado por proceso daemon
            payload = {
                "chart_type": data.chart_type,
                "title": self.filename_var.get().strip() or data.title,
                "x_label": data.x_label,
                "y_label": data.y_label,
                "x_data": data.x_data.tolist(),
                "y_data": data.y_data.tolist(),
                "labels": data.labels,
                "output_dir": self.output_dir,
            }

            # esta parte se encarga de crear y guardar la grafica
            process = ProcessService.run_daemon_task(payload)
            self.log(f"Proceso daemon iniciado con PID: {process.pid}")
            # POR EL MNISALLA QUIERO DORMIR

            messagebox.showinfo("Éxito", "La generación se inició en segundo plano.")
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
