import os
import unittest

try:
    import nbformat
    from nbclient import NotebookClient
except ImportError:  # butuh: pip install notebook
    nbformat = None

HERE = os.path.dirname(os.path.abspath(__file__))


@unittest.skipIf(nbformat is None, "nbformat/nbclient tidak terpasang")
class NotebookTest(unittest.TestCase):
    def test_notebook_berjalan_tanpa_error(self):
        path = os.path.join(HERE, "word_frequency.ipynb")
        notebook = nbformat.read(path, as_version=4)
        # Dieksekusi di memori; berkas .ipynb tidak diubah oleh tes ini.
        NotebookClient(notebook, timeout=120, kernel_name="python3", resources={"metadata": {"path": HERE}}).execute()
        figures = sum(1 for cell in notebook.cells if cell.cell_type == "code"
                      for output in cell.outputs if output.output_type == "display_data")
        self.assertGreaterEqual(figures, 4)


if __name__ == "__main__":
    unittest.main()
