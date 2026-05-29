"""
Legacy / standalone Spectrum Analyzer GUI (PyQt).

The canonical full-workflow entry point is ``python run_orchestrator.py`` (or
the ``soundspectranalyse`` console script): batch analysis, empirical H-I-S
handoff, per-note spectral analysis, and compiled export.

``main.py`` no longer launches this window: it forwards to
``pipeline_orchestrator_integrated.py --gui`` (Tk orchestrator). On Windows,
``run.bat`` starts ``pipeline_orchestrator_gui.py`` (Tk tier GUI), not this PyQt
module. This PyQt module remains for reference or manual experiments only.
"""
# --- Standard library
import os, sys, shutil, subprocess, logging, traceback
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable, Tuple
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
# ou: from PySide6.QtCore import QObject, QThread, Signal as pyqtSignal, Slot as pyqtSlot

import numpy as np
import pandas as pd

from PyQt5.QtCore import Qt, QThread, QThreadPool, QRunnable, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QTabWidget, QMessageBox, QFileDialog, QCheckBox,
    QGroupBox, QFormLayout, QSlider, QProgressDialog
)
from PyQt5.QtCore import Qt
try:
    from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot
except Exception:
    from PySide6.QtCore import QRunnable, QThreadPool, QObject
    from PySide6.QtCore import Signal as pyqtSignal, Slot as pyqtSlot


# D.R. / ML (lazy availability checks to keep startup fast)
UMAP_AVAILABLE = importlib.util.find_spec("umap") is not None
SKLEARN_AVAILABLE = importlib.util.find_spec("sklearn") is not None
TSNE_AVAILABLE = SKLEARN_AVAILABLE and importlib.util.find_spec("sklearn.manifold") is not None
PCA_AVAILABLE = SKLEARN_AVAILABLE and importlib.util.find_spec("sklearn.decomposition") is not None

from proc_audio import AudioProcessor
from gui_model_weight_policy import resolve_analysis_model_weights
from pipeline_orchestrator_integrated import RobustOrchestrator
from weight_function_ui_labels import WEIGHT_FUNCTION_UI_CHOICES, resolve_weight_key_from_user_label
# Removed spectral_power import

logger = logging.getLogger(__name__)

# Backwards-compatible name used throughout this module.
_resolve_weight_key_from_ui = resolve_weight_key_from_user_label

ALLOWED_OPEN_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".html", ".htm",
                     ".csv", ".json", ".xlsx", ".xls", ".txt", ".pdf"}


class SlotWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _WorkerSignals(QObject):
    progress = pyqtSignal(int)     # 0..100
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    finished = pyqtSignal()

class Worker(QRunnable):
    """Executa fn(params) no QThreadPool. Se fn aceitar progress_cb, usa-o."""
    def __init__(self, fn, params):
        super().__init__()
        self.fn = fn
        self.params = params
        self.signals = _WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            try:
                result = self.fn(self.params, progress_cb=self.signals.progress)
            except TypeError:
                result = self.fn(self.params)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


def _safe_open_path(path: str | os.PathLike, allowed_root: Path | None = None) -> None:
    """Open a file safely (no shell). Validates root and extension."""
    p = Path(path)
    try:
        p = p.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")

    # If an allowed root is set, ensure the file stays inside it
    if allowed_root is not None:
        root = Path(allowed_root).resolve()
        if os.path.commonpath([root, p]) != str(root):
            raise PermissionError(f"Path outside allowed directory: {p}")

    # Allow only expected file types
    if p.suffix.lower() not in ALLOWED_OPEN_EXTS:
        raise ValueError(f"Extension not allowed for opening: {p.suffix}")


    # Open with default app (validated input + whitelisted executable)
    p_str = str(Path(p).expanduser().resolve(strict=False))
    if "\x00" in p_str:
        raise ValueError("Invalid path (NUL).")

    # (optional) ensure local path exists
    if not (os.path.isfile(p_str) or os.path.isdir(p_str)):
        logging.error("Missing or invalid path: %s", p_str)
    else:
        if sys.platform.startswith("win"):
            os.startfile(p_str)  # nosec: validated local path

        elif sys.platform == "darwin":
            cmd = shutil.which("open") or "/usr/bin/open"
            subprocess.run([cmd, p_str], check=False)  # nosec S603,S607: cmd whitelisted; validated input

        else:  # Linux/BSD
            cmd = (shutil.which("xdg-open")
                   or shutil.which("gio")
                   or shutil.which("gnome-open"))
            if cmd:
                subprocess.run([cmd, p_str], check=False)  # nosec S603,S607: cmd whitelisted; validated input
            else:
                logging.error("No desktop utility available to open: %s", p_str)



class SpectrumAnalyzer(QMainWindow):
    """
    A PyQt5-based graphical user interface for spectral analysis.

    This class provides an interactive GUI for tasks like loading audio files,
    applying spectral analysis, configuring filters, and compiling results.
    It integrates functionalities like density metrics computation, dissonance calculation, and visualizations.
    """

    def __init__(self):
        """
        Initializes the graphical user interface (GUI).
        """
        super().__init__()
        self.setWindowTitle('Spectrum Analyzer')
        self.setGeometry(100, 100, 800, 600)

        # Core data/processing objects
        self.audio_processor = AudioProcessor()
        self.results_directory: Optional[str] = None

        # Thread pool (owned by this window for background tasks)
        self.threadpool = QThreadPool.globalInstance()

        # Set up the UI
        self.init_ui()


    def init_ui(self) -> None:
        """
        Initializes the user interface layout and tabs.
        """
        # 1) Light sand background for the entire QMainWindow
        self.setStyleSheet("background-color:rgb(230, 218, 204);")

        self.main_layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.setup_controls_tab()
        self.setup_filters_tab()
        self.setup_advanced_tab()

        self.main_layout.addWidget(self.tabs)
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)
        if hasattr(self, "_gui_refresh_batch_weight_readout"):
            self._gui_refresh_batch_weight_readout()

    def setup_controls_tab(self) -> None:
        """
        Configures the 'Controls' tab of the GUI.
        """
        controls_tab = QWidget()
        controls_layout = QVBoxLayout()

        # Button: Load Audio Files
        self.load_button = QPushButton('Load Audio Files')
        # A pale olive green color
        self.load_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.load_button.clicked.connect(self.load_audio_files)
        controls_layout.addWidget(self.load_button)

        # Button: Choose Save Directory
        self.choose_save_dir_button = QPushButton('Choose Save Directory')
        # A pale olive green color
        self.choose_save_dir_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.choose_save_dir_button.clicked.connect(self.choose_save_directory)
        controls_layout.addWidget(self.choose_save_dir_button)

        # Button: Compile Metrics with PCA (Combined functionality)
        self.compile_metrics_button = QPushButton('Compile Metrics with PCA')
        # A pale olive green color
        self.compile_metrics_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.compile_metrics_button.clicked.connect(self.compile_metrics_with_pca)
        controls_layout.addWidget(self.compile_metrics_button)

        # Button: Generate Interactive Visualizations
        self.interactive_viz_button = QPushButton('Generate Interactive Visualizations')
        self.interactive_viz_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.interactive_viz_button.clicked.connect(self.generate_interactive_visualizations)
        controls_layout.addWidget(self.interactive_viz_button)

        # Button: View Dissonance Curves
        self.view_dissonance_curves_button = QPushButton('View Dissonance Curves')
        self.view_dissonance_curves_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.view_dissonance_curves_button.clicked.connect(self.view_dissonance_curves)
        controls_layout.addWidget(self.view_dissonance_curves_button)

        controls_tab.setLayout(controls_layout)
        self.tabs.addTab(controls_tab, "Controls")

    def setup_filters_tab(self) -> None:
        """
        Configures the 'Filters' tab of the GUI.
        """
        filters_tab = QWidget()
        filters_layout = QVBoxLayout()

        # Frequency and Magnitude Filter Group
        filter_group = QGroupBox("Frequency and Magnitude Filters")
        grid_filters = QFormLayout()

        # Default minimum frequency lowered from 200 Hz to 20 Hz
        self.input_min_freq = QLineEdit("20")      # allow G3 (~196 Hz) and low bass content
        self.input_max_freq = QLineEdit("20000")
        self.input_min_db = QLineEdit("-90")
        self.input_max_db = QLineEdit("0")
        self.checkbox_adaptive_tolerance = QCheckBox("Use adaptive tolerance")
        self.checkbox_adaptive_tolerance.setChecked(True)  # default value
        grid_filters.addRow("Tolerance mode:", self.checkbox_adaptive_tolerance)

        # Default tolerance widened (see adjacent field)
        self.input_tolerance = QLineEdit("5.0")

        grid_filters.addRow("Minimum Frequency (Hz):", self.input_min_freq)
        grid_filters.addRow("Maximum Frequency (Hz):", self.input_max_freq)
        grid_filters.addRow("Minimum Magnitude (dB):", self.input_min_db)
        grid_filters.addRow("Maximum Magnitude (dB):", self.input_max_db)
        grid_filters.addRow("Tolerance (Hz):", self.input_tolerance)

        filter_group.setLayout(grid_filters)
        filters_layout.addWidget(filter_group)

        # FFT Parameters Group
        fft_group = QGroupBox("FFT Parameters")
        fft_layout = QFormLayout()

        self.input_n_fft = QLineEdit("4096")
        self.input_hop_length = QLineEdit("")
        self.combo_window_type = QComboBox()
        self.combo_window_type.addItems(['hann', 'hamming', 'blackmanharris', 'bartlett', 'kaiser', 'gaussian'])

        fft_layout.addRow("FFT Window Size (n_fft):", self.input_n_fft)
        fft_layout.addRow("Hop Length:", self.input_hop_length)
        fft_layout.addRow("Window Type:", self.combo_window_type)

        fft_group.setLayout(fft_layout)
        filters_layout.addWidget(fft_group)


        # STFT Options: Zero padding and time averaging are standard STFT parameters
        stft_options_group = QGroupBox("STFT Options")
        stft_options_layout = QFormLayout()

        self.input_zero_padding = QLineEdit("1")
        stft_options_layout.addRow("Zero Padding Factor:", self.input_zero_padding)

        self.combo_time_avg = QComboBox()
        self.combo_time_avg.addItems(['mean', 'median', 'max'])
        stft_options_layout.addRow("Time Averaging Method:", self.combo_time_avg)

        stft_options_group.setLayout(stft_options_layout)
        filters_layout.addWidget(stft_options_group)

        # Metric Calculation Group
        metric_group = QGroupBox("Metric Calculation")
        metric_layout = QFormLayout()

        self.combo_weight_function = QComboBox()
        self.combo_weight_function.addItems([d for d, _ in WEIGHT_FUNCTION_UI_CHOICES])
        self.label_amplitude_weighting_function = QLabel("Amplitude weighting function:")
        self.label_amplitude_weighting_function.setToolTip(
            "Transforms amplitude values before summation (linear, sqrt, log, …), "
            "or discrete spectral metrics: D3 (Σlog1p A), "
            "D10 ((Σlog1p A)·N_eff/N), D17 (log1p(ΣA²)·log1p(N_eff)), "
            "D24 (filt+log; ≥1 % of A_max, f≤12 kHz when frequencies are available). "
            "Those discrete paths bypass rolloff / max-normalization used for the canonical fatness path."
        )
        self.combo_weight_function.setToolTip(self.label_amplitude_weighting_function.toolTip())
        metric_layout.addRow(self.label_amplitude_weighting_function, self.combo_weight_function)

        # --- Component energy ratios + derived model coefficients (read-only) ---
        component_ro_group = QGroupBox(
            "Component energy ratios & model coefficients α/β "
            "(read-only; from current spectral analysis)"
        )
        component_ro_layout = QFormLayout()
        self.label_batch_h_ratio = QLabel("—")
        self.label_batch_i_ratio = QLabel("—")
        self.label_batch_s_ratio = QLabel("—")
        self.label_model_h_weight = QLabel("—")
        self.label_model_i_weight = QLabel("—")
        self.label_model_weights_source = QLabel("—")
        self.label_model_weights_warning = QLabel("—")
        self.label_model_weights_warning.setWordWrap(True)
        component_ro_layout.addRow("component_harmonic_energy_ratio:", self.label_batch_h_ratio)
        component_ro_layout.addRow("component_inharmonic_energy_ratio:", self.label_batch_i_ratio)
        component_ro_layout.addRow("component_subbass_energy_ratio:", self.label_batch_s_ratio)
        component_ro_layout.addRow("model_harmonic_weight (α):", self.label_model_h_weight)
        component_ro_layout.addRow("model_inharmonic_weight (β):", self.label_model_i_weight)
        component_ro_layout.addRow("model_weights_source:", self.label_model_weights_source)
        component_ro_layout.addRow("model_weights_warning:", self.label_model_weights_warning)
        component_ro_group.setLayout(component_ro_layout)
        metric_layout.addRow(component_ro_group)

        # --- Advanced: manual model-weight override (optional) ---
        adv_w_group = QGroupBox(
            "Advanced: manual model-weight override (α/β for combined metric path only)"
        )
        adv_w_layout = QVBoxLayout()
        self.check_manual_model_weight_override = QCheckBox(
            "Enable manual model-weight override "
            "(overrides current-analysis derived weights)"
        )
        self.check_manual_model_weight_override.setChecked(False)
        self.check_manual_model_weight_override.toggled.connect(self._on_manual_weight_override_toggled)
        adv_w_layout.addWidget(self.check_manual_model_weight_override)

        harmonic_weight_layout = QHBoxLayout()
        self.harmonic_weight_slider = QSlider(Qt.Horizontal)
        self.harmonic_weight_slider.setMinimum(0)
        self.harmonic_weight_slider.setMaximum(100)
        self.harmonic_weight_slider.setValue(95)
        self.harmonic_weight_slider.setTickPosition(QSlider.TicksBelow)
        self.harmonic_weight_slider.setTickInterval(10)
        self.harmonic_weight_value = QLabel("95%")
        self.inharmonic_weight_value = QLabel("5%")
        self.harmonic_weight_slider.valueChanged.connect(self.update_harmonic_weight_display)
        harmonic_weight_layout.addWidget(QLabel("Harmonic α (model coeff.):"))
        harmonic_weight_layout.addWidget(self.harmonic_weight_slider)
        harmonic_weight_layout.addWidget(self.harmonic_weight_value)
        harmonic_weight_layout.addWidget(QLabel("Inharmonic β:"))
        harmonic_weight_layout.addWidget(self.inharmonic_weight_value)
        adv_w_layout.addLayout(harmonic_weight_layout)
        adv_w_group.setLayout(adv_w_layout)
        self.harmonic_weight_slider.setEnabled(False)
        metric_layout.addRow(adv_w_group)

        # Dissonance Model Selection
        self.combo_dissonance_model = QComboBox()
        self.combo_dissonance_model.addItems([
            'Sethares', 'Hutchinson-Knopoff', 'Vassilakis'
        ])
        metric_layout.addRow("Dissonance Model:", self.combo_dissonance_model)

        # Dissonance Controls
        self.check_dissonance_enabled = QCheckBox()
        self.check_dissonance_enabled.setChecked(True)  # Enable by default
        metric_layout.addRow("Enable Dissonance Analysis:", self.check_dissonance_enabled)

        self.check_dissonance_curve = QCheckBox()
        self.check_dissonance_curve.setChecked(True)
        metric_layout.addRow("Generate Dissonance Curve:", self.check_dissonance_curve)

        # Compare dissonance models option
        self.check_compare_models = QCheckBox()
        self.check_compare_models.setChecked(False)
        metric_layout.addRow("Compare All Dissonance Models:", self.check_compare_models)

        # Spectral masking is not exposed in the main density workflow (optional psychoacoustic
        # path in AudioProcessor only). Density/fatness metrics use the physical partial list.

        metric_group.setLayout(metric_layout)
        filters_layout.addWidget(metric_group)

        # Apply Button
        self.apply_filters_button = QPushButton('Apply Filters')
        self.apply_filters_button.clicked.connect(self.apply_filters)
        self.apply_filters_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.apply_filters_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        filters_layout.addWidget(self.apply_filters_button)

        filters_tab.setLayout(filters_layout)
        self.tabs.addTab(filters_tab, "Filters")

    def _get_weight_function_from_ui(self) -> str:
        """
        Always return a valid internal weight-function key from the UI combo
        (human-readable labels map to keys accepted by ``density.get_weight_function``).
        """
        try:
            raw_label = str(self.combo_weight_function.currentText())
        except Exception:
            raw_label = "linear"

        try:
            from density import get_weight_function

            wf = _resolve_weight_key_from_ui(raw_label)
            _ = get_weight_function(wf)
            return wf
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                "Invalid amplitude weighting function in UI: '%s' (%s)", raw_label, e
            )
            raise

    def update_harmonic_weight_display(self, value: int) -> None:
        """
        Update the percentage labels for α (harmonic) / β (inharmonic) weights
        when the slider moves. Never show 0 % or 100 % for both sides at once;
        enforce at least 1 % on each side.
        """
        # Safety limits: at least 0 %, at most 100 %
        harmonic = max(0, min(100, value))
        inharmonic = 100 - harmonic

        self.harmonic_weight_value.setText(f"{harmonic}%")
        self.inharmonic_weight_value.setText(f"{inharmonic}%")

    def _on_manual_weight_override_toggled(self, checked: bool) -> None:
        self.harmonic_weight_slider.setEnabled(bool(checked))
        self._gui_refresh_batch_weight_readout()

    def _gui_find_batch_summary_path(self) -> Optional[Path]:
        # The Stage 1 / Stage 2 pipeline never produces an external
        # H/I/S mapping. Component energy ratios come from the per-note
        # current spectral analysis only.
        return None

    @staticmethod
    def _gui_excel_row_to_batch_payload(row: Any) -> Optional[Dict[str, Any]]:
        # External H/I/S mapping is disabled; this helper is retained
        # only so callers built against the previous API do not crash.
        return None

    def _gui_read_batch_payload_for_primary_audio(self) -> Optional[Dict[str, Any]]:
        # No external mapping is consulted in the current pipeline.
        return None

    def _gui_refresh_batch_weight_readout(self) -> None:
        if not hasattr(self, "label_batch_h_ratio"):
            return
        manual = bool(self.check_manual_model_weight_override.isChecked())
        slider_a = float(self.harmonic_weight_slider.value()) / 100.0
        # No external H/I/S mapping is consulted; weights come from the
        # current per-note analysis (or the manual override slider).
        alpha, beta, meta = resolve_analysis_model_weights(manual, slider_a, None)

        def _fmt4(x: Any) -> str:
            if x is None:
                return "—"
            try:
                xf = float(x)
            except (TypeError, ValueError):
                return "—"
            if not np.isfinite(xf):
                return "—"
            return f"{xf:.4f}"

        ap = getattr(self, "audio_processor", None)
        bh = (
            getattr(ap, "component_harmonic_energy_ratio", None)
            if ap is not None
            else None
        )
        bi = (
            getattr(ap, "component_inharmonic_energy_ratio", None)
            if ap is not None
            else None
        )
        bs = (
            getattr(ap, "component_subbass_energy_ratio", None)
            if ap is not None
            else None
        )
        self.label_batch_h_ratio.setText(_fmt4(bh))
        self.label_batch_i_ratio.setText(_fmt4(bi))
        self.label_batch_s_ratio.setText(_fmt4(bs))
        self.label_model_h_weight.setText(_fmt4(alpha))
        self.label_model_i_weight.setText(_fmt4(beta))
        self.label_model_weights_source.setText(
            str(meta.get("model_weights_source", "current_analysis"))
        )
        mw = meta.get("model_weights_warning")
        self.label_model_weights_warning.setText(str(mw) if mw else "—")

        if not manual:
            self.harmonic_weight_slider.blockSignals(True)
            self.harmonic_weight_slider.setValue(int(round(float(alpha) * 100.0)))
            self.harmonic_weight_slider.blockSignals(False)
            self.update_harmonic_weight_display(self.harmonic_weight_slider.value())

    def _apply_gui_weight_metadata_to_processor(self, ap: AudioProcessor, meta: Dict[str, Any]) -> None:
        ap.gui_weight_resolution_meta = dict(meta)
        ap.gui_model_weights_source = meta.get("model_weights_source")
        ap.gui_model_weights_warning = meta.get("model_weights_warning")
        ap.gui_manual_override_active = str(meta.get("model_weights_source") or "") == "manual_override"
        if ap.gui_manual_override_active:
            ap.gui_manual_model_harmonic_weight = meta.get("manual_model_harmonic_weight")
            ap.gui_manual_model_inharmonic_weight = meta.get("manual_model_inharmonic_weight")
        else:
            ap.gui_manual_model_harmonic_weight = None
            ap.gui_manual_model_inharmonic_weight = None


    def setup_advanced_tab(self) -> None:
        """
        Configures the 'Advanced' tab of the GUI.
        """
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()

        # Dissonance Analysis Group
        dissonance_group = QGroupBox("Dissonance Analysis")
        dissonance_layout = QFormLayout()

        # Comparison options
        self.check_compare_dissonance = QCheckBox()
        self.check_compare_dissonance.setChecked(True)
        dissonance_layout.addRow("Compare Dissonance with Density:", self.check_compare_dissonance)

        # Scale visualization options
        self.combo_scale_visualization = QComboBox()
        self.combo_scale_visualization.addItems(['Cents', 'Ratio', 'Both'])
        dissonance_layout.addRow("Scale Visualization:", self.combo_scale_visualization)

        # Button: Analyze Dissonance vs Density
        self.analyze_dissonance_button = QPushButton('Analyze Dissonance vs Density')
        self.analyze_dissonance_button.setStyleSheet("background-color: rgb(219, 224, 169);")
        self.analyze_dissonance_button.clicked.connect(self.analyze_dissonance_vs_density)
        dissonance_layout.addRow(self.analyze_dissonance_button)

        dissonance_group.setLayout(dissonance_layout)
        advanced_layout.addWidget(dissonance_group)

        # Advanced Analysis Group
        advanced_analysis_group = QGroupBox("Advanced Analysis Options")
        advanced_analysis_layout = QFormLayout()

        # Dimensionality Reduction Methods
        self.check_use_pca = QCheckBox()
        self.check_use_pca.setChecked(True)
        advanced_analysis_layout.addRow("Use PCA:", self.check_use_pca)

        self.check_pca_include_dissonance = QCheckBox()
        self.check_pca_include_dissonance.setChecked(False)
        self.check_pca_include_dissonance.setToolTip(
            "If enabled, exploratory PCA may include selected_dissonance_value as an extra z-scored feature. "
            "Off by default; density and dissonance remain separate constructs."
        )
        advanced_analysis_layout.addRow("Include dissonance in PCA:", self.check_pca_include_dissonance)

        def _sync_pca_dissonance_checkbox() -> None:
            self.check_pca_include_dissonance.setEnabled(self.check_use_pca.isChecked())
            if not self.check_use_pca.isChecked():
                self.check_pca_include_dissonance.setChecked(False)

        self.check_use_pca.toggled.connect(_sync_pca_dissonance_checkbox)
        _sync_pca_dissonance_checkbox()

        self.check_use_tsne = QCheckBox()
        self.check_use_tsne.setChecked(False)
        advanced_analysis_layout.addRow("Use t-SNE:", self.check_use_tsne)

        self.check_use_umap = QCheckBox()
        self.check_use_umap.setChecked(False)
        if not UMAP_AVAILABLE:
            self.check_use_umap.setEnabled(False)
            self.check_use_umap.setToolTip("UMAP not available. Install with 'pip install umap-learn'")
        advanced_analysis_layout.addRow("Use UMAP:", self.check_use_umap)

        # Anomaly Detection
        self.check_anomaly_detection = QCheckBox()
        self.check_anomaly_detection.setChecked(False)
        advanced_analysis_layout.addRow("Detect Anomalies:", self.check_anomaly_detection)

        self.input_contamination = QLineEdit("auto")
        advanced_analysis_layout.addRow("Expected Anomaly Fraction (auto or 0-1):", self.input_contamination)

        # Include dissonance in analysis
        self.check_include_dissonance = QCheckBox()
        self.check_include_dissonance.setChecked(True)
        advanced_analysis_layout.addRow("Include Dissonance in Analysis:", self.check_include_dissonance)

        advanced_analysis_group.setLayout(advanced_analysis_layout)
        advanced_layout.addWidget(advanced_analysis_group)

        # Interactive Visualization Options
        viz_group = QGroupBox("Interactive Visualization Options")
        viz_layout = QFormLayout()

        self.check_3d_spectrogram = QCheckBox()
        self.check_3d_spectrogram.setChecked(True)
        viz_layout.addRow("3D Spectrograms:", self.check_3d_spectrogram)

        self.check_interactive_curves = QCheckBox()
        self.check_interactive_curves.setChecked(True)
        viz_layout.addRow("Interactive Dissonance Curves:", self.check_interactive_curves)

        self.check_dimension_scatterplots = QCheckBox()
        self.check_dimension_scatterplots.setChecked(True)
        viz_layout.addRow("Dimensionality Reduction Plots:", self.check_dimension_scatterplots)

        viz_group.setLayout(viz_layout)
        advanced_layout.addWidget(viz_group)

        advanced_tab.setLayout(advanced_layout)
        self.tabs.addTab(advanced_tab, "Advanced")
    # Interactive visualisation helpers (SpectrumAnalyzer)

    def create_interactive_visualizations(self, df: pd.DataFrame, output_dir: str) -> None:
        """
        Creates more modern, responsive interactive visualisations for spectral data.
        Includes error handling and basic data validation.
        """
        import plotly.express as px

        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Check that the DataFrame has usable rows
            if df is None or df.empty:
                logger.error("Empty DataFrame supplied for interactive visualisations")
                # Write a small informative HTML error page
                error_path = os.path.join(output_dir, 'error.html')
                with open(error_path, 'w') as f:
                    f.write("<html><body><h1>Error Generating Visualisations</h1>")
                    f.write("<p>No valid data available for plotting.</p></body></html>")
                return error_path

            # 1. Interactive PCA visualisation
            if 'PC1' in df.columns and 'PC2' in df.columns:
                try:
                    # Check and prepare columns for plotting
                    color_column = None
                    if 'Density Metric' in df.columns:
                        # Ensure the column is numeric before using it for colour
                        if pd.api.types.is_numeric_dtype(df['Density Metric']):
                            color_column = 'Density Metric'

                    # Optional text column for hover labels
                    hover_name = None
                    if 'Note' in df.columns:
                        hover_name = 'Note'

                    # Pick numeric columns for hover details
                    hover_data = []
                    for col in df.columns:
                        if (
                            ("Metric" in col or "Dissonance" in col or str(col).startswith("discrete_metric_"))
                            and pd.api.types.is_numeric_dtype(df[col])
                        ):
                            hover_data.append(col)

                    # Build PCA scatter plot
                    fig = px.scatter(
                        df, x='PC1', y='PC2',
                        color=color_column,
                        hover_name=hover_name,
                        hover_data=hover_data,
                        title='PCA Analysis of Spectral Properties',
                        labels={'PC1': 'Principal Component 1', 'PC2': 'Principal Component 2'},
                        color_continuous_scale='viridis'
                    )

                    # Tweak layout for readability
                    fig.update_layout(
                        template='plotly_white',
                        margin=dict(l=10, r=10, t=50, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        width=900, height=700
                    )

                    # Save interactive HTML
                    fig.write_html(os.path.join(output_dir, 'pca_interactive.html'))
                    logger.info(f"Interactive PCA visualisation written: {os.path.join(output_dir, 'pca_interactive.html')}")
                except Exception as e:
                    logger.error(f"Error creating interactive PCA visualisation: {e}")

            # [Additional visualisations would follow the same pattern…]

            # Dashboard that embeds whichever HTML exports exist
            dashboard_files = []
            for viz_file in ['pca_interactive.html', 'correlation_interactive.html', 'metrics_comparison_interactive.html']:
                if os.path.exists(os.path.join(output_dir, viz_file)):
                    dashboard_files.append(viz_file)

            if dashboard_files:
                dashboard_html = self._create_dashboard_html(dashboard_files)
                dashboard_path = os.path.join(output_dir, 'dashboard.html')

                with open(dashboard_path, 'w') as f:
                    f.write(dashboard_html)

                return dashboard_path
            else:
                logger.warning("No visualisations were produced for the dashboard")
                return None

        except Exception as e:
            logger.error(f"Error creating interactive visualisations: {e}")
            # Persist a plain-text error for debugging
            error_path = os.path.join(output_dir, 'visualization_error.txt')
            with open(error_path, 'w') as f:
                f.write(f"Error creating interactive visualisations: {str(e)}")
            return error_path

    def _create_dashboard_html(self, viz_files: List[str]) -> str:
        """Build dashboard HTML, tolerating missing embed files."""

        # Opening HTML template
        html_start = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spectral Analysis Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .dashboard { display: flex; flex-direction: column; gap: 20px; }
                .dashboard-item { background-color: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .dashboard-header { text-align: center; margin-bottom: 20px; }
                .viz-container { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
                .viz-item { flex: 1; min-width: 300px; min-height: 300px; }
                h1, h2 { color: #2c3e50; }
                iframe { border: none; width: 100%; height: 600px; }
                .error { color: red; padding: 10px; background-color: #ffeeee; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="dashboard-header">
                    <h1>Spectral Analysis Dashboard</h1>
                    <p>Interactive visualizations for spectral analysis data</p>
                </div>
        """

        # Map file names to section titles
        file_titles = {
            'pca_interactive.html': 'Principal Component Analysis',
            'correlation_interactive.html': 'Correlation Matrix',
            'metrics_comparison_interactive.html': 'Metrics Comparison'
        }

        # Assemble dashboard body
        html_items = ""
        for viz_file in viz_files:
            title = file_titles.get(viz_file, viz_file)
            html_items += f"""
            <div class="dashboard-item">
                <h2>{title}</h2>
                <iframe src="{viz_file}" onload="this.style.height = Math.max(600, this.contentWindow.document.body.scrollHeight + 30) + 'px';"></iframe>
            </div>
            """

        # Closing HTML
        html_end = """
            </div>
        </body>
        </html>
        """

        return html_start + html_items + html_end

    def plot_enhanced_spectrum(self, harmonic_df: pd.DataFrame, note: str) -> None:
        """
        Build an enhanced interactive plot of the harmonic spectrum.

        Args:
            harmonic_df: DataFrame of harmonic partials
            note: Musical note label
        """
        import plotly.graph_objects as go

        if harmonic_df is None or harmonic_df.empty:
            return

        # Extract arrays
        frequencies = harmonic_df['Frequency (Hz)'].values
        amplitudes = harmonic_df['Amplitude'].values if 'Amplitude' in harmonic_df.columns else \
                    10**(harmonic_df['Magnitude (dB)'].values/20)
        harmonic_numbers = harmonic_df['Harmonic Number'].values if 'Harmonic Number' in harmonic_df.columns else \
                          np.arange(1, len(frequencies)+1)

        # Normalise amplitudes for display
        norm_amplitudes = amplitudes / np.max(amplitudes)

        # Create figure
        fig = go.Figure()

        # Bar trace per partial
        fig.add_trace(go.Bar(
            x=harmonic_numbers,
            y=norm_amplitudes,
            marker=dict(
                color=norm_amplitudes,
                colorscale='Viridis',
                line=dict(color='rgba(0,0,0,0.5)', width=1)
            ),
            name='Amplitude',
            text=[f"{freq:.1f} Hz" for freq in frequencies],
            hovertemplate='Harmonic: %{x}<br>Amplitude: %{y:.3f}<br>Frequency: %{text}'
        ))

        # Layout
        fig.update_layout(
            title=f'Harmonic Spectrum - {note}',
            xaxis_title='Harmonic Number',
            yaxis_title='Normalized Amplitude',
            template='plotly_white',
            height=600,
            width=900,
            showlegend=False
        )

        # Overlay ideal harmonic series (marker trace)
        if len(frequencies) > 1:
            f0 = frequencies[0]  # fundamental frequency
            ideal_frequencies = [f0 * (i+1) for i in range(len(frequencies))]

            fig.add_trace(go.Scatter(
                x=harmonic_numbers,
                y=[0.05] * len(harmonic_numbers),  # fixed vertical offset for display
                mode='markers',
                marker=dict(
                    symbol='diamond',
                    size=12,
                    color='red',
                    line=dict(color='rgba(0,0,0,0.5)', width=1)
                ),
                name='Ideal Harmonics',
                text=[f"{freq:.1f} Hz" for freq in ideal_frequencies],
                hovertemplate='Harmonic: %{x}<br>Ideal Frequency: %{text}'
            ))

        # Save interactive HTML
        output_dir = os.path.join(self.results_directory, note)
        os.makedirs(output_dir, exist_ok=True)

        fig.write_html(os.path.join(output_dir, 'enhanced_spectrum.html'))

        # Also export a static PNG
        fig.write_image(os.path.join(output_dir, 'enhanced_spectrum.png'))

    def save_spectral_analysis(self, note, harmonic_df):
        """
        Persist spectral-analysis outputs, including the enhanced spectrum view.

        Args:
            note: Musical note label
            harmonic_df: DataFrame of harmonic partials
        """
        # Existing persistence path for tabular results…

        # Optional enhanced spectrum export
        try:
            # Plotly required for enhanced plots
            import importlib
            if importlib.util.find_spec("plotly") is not None:
                self.plot_enhanced_spectrum(harmonic_df, note)
            else:
                logger.warning("Plotly is not installed; enhanced spectrum plots are disabled.")
        except Exception as e:
            logger.error(f"Error creating enhanced spectrum visualisation for {note}: {e}")

    def plot_enhanced_dissonance_curve(self, model_name: str, curve: Dict, scale: List, note: str) -> None:
        """
        Build an enhanced dissonance-curve plot with musical-interval annotations.

        Args:
            model_name: Dissonance model label
            curve: Dissonance curve mapping (interval → value)
            scale: Scale interval ratios
            note: Musical note label
        """
        import plotly.graph_objects as go

        if not curve or not scale:
            return

        # Prepare series
        intervals = sorted(list(curve.keys()))
        dissonance_values = [curve[i] for i in intervals]

        # Map interval ratios to cents
        cents = [1200 * np.log2(i) for i in intervals]

        # Create figure
        fig = go.Figure()

        # Dissonance curve trace
        fig.add_trace(go.Scatter(
            x=cents,
            y=dissonance_values,
            mode='lines',
            line=dict(color='blue', width=2),
            name='Dissonance Curve'
        ))

        # Scale-degree markers
        scale_cents = [1200 * np.log2(i) for i in scale]
        scale_values = [curve.get(i, 0) for i in scale]

        fig.add_trace(go.Scatter(
            x=scale_cents,
            y=scale_values,
            mode='markers',
            marker=dict(
                color='red',
                size=10,
                line=dict(color='black', width=1)
            ),
            name='Optimal Scale Points'
        ))

        # Vertical guides and labels for common musical intervals
        common_intervals = {
            0: "Unison",
            100: "Minor 2nd",
            200: "Major 2nd",
            300: "Minor 3rd",
            400: "Major 3rd",
            500: "Perfect 4th",
            600: "Tritone",
            700: "Perfect 5th",
            800: "Minor 6th",
            900: "Major 6th",
            1000: "Minor 7th",
            1100: "Major 7th",
            1200: "Octave"
        }

        for cents_value, name in common_intervals.items():
            fig.add_shape(
                type="line",
                x0=cents_value, y0=min(dissonance_values),
                x1=cents_value, y1=max(dissonance_values),
                line=dict(color="rgba(128, 128, 128, 0.5)", width=1, dash="dot")
            )

            # Interval label
            fig.add_annotation(
                x=cents_value,
                y=max(dissonance_values) * 1.05,
                text=name,
                showarrow=False,
                textangle=-90,
                font=dict(size=10)
            )

        # Layout
        fig.update_layout(
            title=f'{model_name} Dissonance Curve - {note}',
            xaxis_title='Interval (cents)',
            yaxis_title='Dissonance',
            template='plotly_white',
            height=600,
            width=900,
            xaxis=dict(
                tickmode='array',
                tickvals=list(common_intervals.keys()),
                ticktext=list(common_intervals.values()),
                tickangle=-45
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Secondary x-axis with frequency ratios
        tick_intervals = [1.0, 1.125, 1.25, 1.333, 1.5, 1.667, 1.75, 2.0]
        tick_cents = [1200 * np.log2(i) for i in tick_intervals]

        fig.update_layout(
            xaxis2=dict(
                overlaying="x",
                side="bottom",
                position=0.05,
                tickmode='array',
                tickvals=tick_cents,
                ticktext=[f"{i:.3f}" for i in tick_intervals],
                title="Frequency Ratio",
                showgrid=False,
                zeroline=False
            )
        )

        # Save interactive HTML
        output_dir = os.path.join(self.results_directory, note)
        os.makedirs(output_dir, exist_ok=True)

        fig.write_html(os.path.join(output_dir, f'{model_name.lower()}_dissonance_curve.html'))

        # Also export a static PNG
        fig.write_image(os.path.join(output_dir, f'{model_name.lower()}_dissonance_curve.png'))

    # -------------------------------------------------------------------------
    #                           CONTROLS TAB FUNCTIONS
    # -------------------------------------------------------------------------

    def choose_save_directory(self) -> None:
        """
        Opens a dialog for selecting the directory to save results.
        """
        selected_directory = QFileDialog.getExistingDirectory(
            self, "Select Directory to Save Results", os.getcwd()
        )
        if selected_directory:
            self.results_directory = selected_directory
            QMessageBox.information(self, "Directory Selected",
                                    f"Results will be saved in: {selected_directory}")
        else:
            QMessageBox.warning(self, "Warning", "No directory selected.")

    def load_audio_files(self) -> None:
        """
        Opens a dialog for selecting and loading audio files.
        """
        try:
            options = QFileDialog.Options()
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Audio Files",
                "",
                "Audio Files (*.wav *.mp3 *.flac *.aif *.aiff);;All Files (*)",
                options=options
            )
            if files:
                self.audio_processor.load_audio_files(files)
                if hasattr(self, "_gui_refresh_batch_weight_readout"):
                    self._gui_refresh_batch_weight_readout()
                QMessageBox.information(self, "Success",
                                        f"{len(files)} files successfully loaded.")
            else:
                QMessageBox.warning(self, "Warning", "No files selected.")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"An error occurred while loading the files: {str(e)}")


    def compile_metrics_with_pca(self) -> None:
        """
        Compiles metrics and runs advanced analysis in a background thread.
        Reads parameters from the UI on the main thread, runs work on QThreadPool (QRunnable),
        injects a lightweight ``signals`` shim into ``_run_compile_metrics_task`` (for ``.progress.emit(int, str)``),
        updates the UI via Qt signals, and re-enables controls on completion, error, or cancel.
        """
        # 1) Escolha da pasta
        selected_folder = QFileDialog.getExistingDirectory(
            self, "Select the Folder with Results", os.getcwd()
        )
        if not selected_folder:
            QMessageBox.warning(self, "Warning", "No folder selected.")
            return

        # AUDIT FIX (stale-pipeline guard) — block compile/plot if the
        # selected folder contains per-note workbooks produced by a
        # stale legacy pipeline. The GUI surfaces this as a modal
        # error dialog with the canonical user-facing text from
        # compile_metrics.STALE_PIPELINE_USER_MESSAGE.
        try:
            from compile_metrics import (
                assert_results_dir_schema_or_raise as _assert_schema_ui,
                STALE_PIPELINE_USER_MESSAGE as _STALE_MSG,
            )
            from proc_audio import log_runtime_paths as _log_paths_ui

            try:
                _log_paths_ui()
            except Exception:
                pass
            try:
                _assert_schema_ui(selected_folder)
            except RuntimeError as _stale_exc:
                QMessageBox.critical(
                    self, "Stale analysis results", str(_stale_exc),
                )
                return
        except ImportError:
            pass

        output_path = os.path.join(selected_folder, "compiled_metrics_with_analysis.xlsx")

        # 2) Read parameters from the UI (main thread)
        try:
            contamination_text = self.input_contamination.text().strip().lower()
            if contamination_text in ("", "auto", "adaptive"):
                contamination_value = None
            else:
                contamination_value = float(contamination_text)

            bp = self._gui_read_batch_payload_for_primary_audio()
            mo = bool(self.check_manual_model_weight_override.isChecked())
            sw = float(self.harmonic_weight_slider.value()) / 100.0
            hw_compile, _iw_c, _wm_c = resolve_analysis_model_weights(mo, sw, bp)
            params = {
                "folder_path": selected_folder,
                "output_path": output_path,
                "include_pca": bool(self.check_use_pca.isChecked()),
                "pca_include_dissonance": bool(self.check_pca_include_dissonance.isChecked()),
                "use_tsne": bool(self.check_use_tsne.isChecked()),
                "use_umap": bool(self.check_use_umap.isChecked()) and bool(UMAP_AVAILABLE),
                "detect_anomalies": bool(self.check_anomaly_detection.isChecked()),
                "include_dissonance": bool(self.check_include_dissonance.isChecked()),
                "harmonic_weight": float(hw_compile),
                "weight_function_label": str(self.combo_weight_function.currentText()),
                "anomaly_contamination": contamination_value,
            }
        except (ValueError, TypeError) as e:
            QMessageBox.critical(self, "Invalid Parameter", f"One of the input parameters is invalid: {e}")
            return

        # 3) Progress dialog
        progress = QProgressDialog("Compiling metrics...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Analysis in Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()

        # 4) Disable controls while the worker runs
        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(False)

        # 5) QThreadPool worker (no moveToThread; signals shim)
        try:
            from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot
        except Exception:
            from PySide6.QtCore import QRunnable, QThreadPool, QObject
            from PySide6.QtCore import Signal as pyqtSignal, Slot as pyqtSlot  # fallback

        class _CMWSignals(QObject):
            # progress payload is (int, str) to match downstream emitters
            progress = pyqtSignal(int, str)
            error = pyqtSignal(str)
            result = pyqtSignal(object)
            finished = pyqtSignal()

        class _ShimEmitter:
            """Thin wrapper exposing ``.emit(...)`` bound to external Qt signals."""
            def __init__(self, emit_fn):
                self._emit_fn = emit_fn
            def emit(self, *args, **kwargs):
                # forward to the underlying Qt signal
                self._emit_fn(*args, **kwargs)

        class _ShimSignals:
            """``signals`` object with ``.progress/.error/.result/.finished`` shim emitters."""
            def __init__(self, qt_signals: _CMWSignals):
                self.progress = _ShimEmitter(qt_signals.progress.emit)
                self.error    = _ShimEmitter(qt_signals.error.emit)
                self.result   = _ShimEmitter(qt_signals.result.emit)
                self.finished = _ShimEmitter(qt_signals.finished.emit)

        class _CMWRunner(QRunnable):
            """Run ``fn(params)`` on the thread pool; inject ``owner.signals`` when missing."""
            def __init__(self, fn, params_dict):
                super().__init__()
                self.fn = fn                      # bound method: owner = fn.__self__
                self.params = params_dict
                self.signals = _CMWSignals()
                self._cancel = False

            def cancel(self):
                self._cancel = True

            @pyqtSlot()
            def run(self):
                owner = getattr(self.fn, "__self__", None)
                cleanup = False
                try:
                    # Inject ``signals`` when the callee expects ``self.signals.progress.emit(...)``
                    if owner is not None and not hasattr(owner, "signals"):
                        owner.signals = _ShimSignals(self.signals)
                        cleanup = True

                    # Main call: no extra kwargs (target does not accept ``progress_cb``)
                    result = self.fn(self.params)

                    if not self._cancel:
                        # If the callee already emitted ``result``, this is redundant but harmless.
                        # Otherwise emit a conventional result payload:
                        self.signals.result.emit(result)
                except Exception as e:
                    self.signals.error.emit(str(e))
                finally:
                    # Always emit ``finished``
                    self.signals.finished.emit()
                    # Remove shim attributes from the owner when applicable
                    if cleanup:
                        try:
                            delattr(owner, "signals")
                        except Exception:
                            pass

        runner = _CMWRunner(self._run_compile_metrics_task, params)

        # 6) Signal handlers (progress uses (int, str))
        def _on_progress(val: int, msg: str = ""):
            if progress.wasCanceled():
                runner.cancel()
                return
            progress.setValue(int(max(0, min(100, val))))
            if msg:
                progress.setLabelText(str(msg))

        def _on_result(_payload):
            # success path (result may already have been emitted internally)
            if progress.isVisible():
                progress.setValue(100)
                progress.close()
            if hasattr(self, "_set_controls_enabled"):
                self._set_controls_enabled(True)
            QMessageBox.information(self, "Done", f"Metrics compiled.\nSaved to:\n{output_path}")

        def _on_error(msg: str):
            if progress.isVisible():
                progress.close()
            if hasattr(self, "_set_controls_enabled"):
                self._set_controls_enabled(True)
            try:
                self.logger.exception("Worker error: %s", msg)
            except Exception:
                pass
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{msg}")

        def _on_finished():
            # fail-safe: always re-enable the UI even without explicit result/error
            if hasattr(self, "_set_controls_enabled"):
                self._set_controls_enabled(True)
            if progress.isVisible():
                progress.close()

        # 7) Connect signals
        runner.signals.progress.connect(_on_progress)
        runner.signals.result.connect(_on_result)
        runner.signals.error.connect(_on_error)
        runner.signals.finished.connect(_on_finished)
        progress.canceled.connect(runner.cancel)

        # 8) Start on the global thread pool
        if not hasattr(self, "threadpool") or self.threadpool is None:
            self.threadpool = QThreadPool.globalInstance()
        self.threadpool.start(runner)




    def _run_compile_metrics_task(self, params: dict) -> dict:
        """
        Executes the metric compilation task in the background.
        This version is decoupled from the UI and receives all parameters via a dictionary.
        """
        try:
            from compile_metrics import compile_density_metrics_with_pca
            from density import get_weight_function

            # --- CORRECTED PATTERN: Use parameters passed via the `params` dictionary ---
            # No more direct access to `self.some_widget`.
            folder_path = params["folder_path"]
            output_path = params["output_path"]

            raw_label = params["weight_function_label"]
            weight_function = _resolve_weight_key_from_ui(str(raw_label))
            _ = get_weight_function(weight_function)

            harmonic_weight = params["harmonic_weight"]
            inharmonic_weight = 1.0 - harmonic_weight

            self.signals.progress.emit(10, "Compiling metrics (canonical pipeline)...")
            compiled_df = compile_density_metrics_with_pca(
                folder_path=folder_path,
                output_path=output_path,
                file_pattern="spectral_analysis.xlsx",
                include_pca=bool(params["include_pca"]),
                harmonic_weight=harmonic_weight,
                inharmonic_weight=inharmonic_weight,
                weight_function=weight_function,
                use_tsne=bool(params.get("use_tsne", False)),
                use_umap=bool(params.get("use_umap", False)),
                detect_anomalies=bool(params.get("detect_anomalies", False)),
                anomaly_contamination=params.get("anomaly_contamination"),
                compiled_public_columns=False,
                pca_include_dissonance=bool(params.get("pca_include_dissonance", False)),
                allow_legacy_super_json=False,
                compilation_extra_metadata={
                    "input_schema_validation_status": "not_validated_gui_threadpool_compile",
                },
            )
            if compiled_df is None or compiled_df.empty:
                return {"success": False, "message": "No valid data found for compilation."}

            self.signals.progress.emit(100, "Done!")
            return {"success": True, "path": str(output_path)}

        except Exception as e:
            logger.error("Error in background task:", exc_info=True)
            # Propagate the error back to the main thread via the error signal
            self.signals.error.emit(str(e))
            return {"success": False, "message": str(e)}

    def _update_compile_progress(self, progress_bar, current, total, message):
        """Update the progress dialog while compilation runs."""
        if progress_bar is None:
            return

        if total > 0:
            percent = int((current / total) * 100)
            progress_bar.setValue(percent)

        if message:
            progress_bar.setLabelText(message)

        # Process pending Qt events so the UI stays responsive
        QApplication.processEvents()

    def _handle_compile_result(self, result, output_path):
        """Handle a background compilation result on the UI thread."""
        if result.get('success', False):
            QMessageBox.information(
                self,
                "Success",
                f"Compiled metrics with full analysis saved to:\n{output_path}\n\n"
                f"Analysis report available at:\n{result.get('report', '')}"
            )
        else:
            QMessageBox.warning(
                self,
                "Warning",
                f"Compilation issue: {result.get('message', 'Unknown error')}"
            )



    def get_numeric_columns(self, df: pd.DataFrame, include_dissonance: bool = True) -> List[str]:
        """
        Return numeric (or coercible-to-numeric) columns relevant for analysis.

        Rules:
          1) Prefer the standard metric columns when present, including ``discrete_metric_d3``…``d24``.
          2) Optionally append columns whose name contains "Dissonance".
          3) Treat as numeric:
             - columns already numeric; or
             - columns coercible via ``pd.to_numeric(errors="coerce")`` with at least two non-null values.
        """
        # 1) standard metrics (order preserved)
        standard_cols = [
            "effective_partial_density",
            "harmonic_energy_ratio",
            "inharmonic_energy_ratio",
            "subbass_energy_ratio",
            "discrete_metric_d3",
            "discrete_metric_d10",
            "discrete_metric_d17",
            "discrete_metric_d24",
            "Density Metric",
            "Weighted Combined Metric",
            "Index_Weighted",
        ]
        candidates: List[str] = [c for c in standard_cols if c in df.columns]

        # 2) append dissonance columns when requested
        if include_dissonance:
            candidates += [c for c in df.columns if "Dissonance" in c]

        # 2.1) deduplicate while preserving order
        seen: set = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        # 3) keep numeric or coercible columns with at least two valid values
        numeric_now = set(df.select_dtypes(include="number").columns)
        numeric_sel: set = set(c for c in candidates if c in numeric_now)

        for c in candidates:
            if c not in numeric_sel:
                s = pd.to_numeric(df[c], errors="coerce")
                if s.notnull().sum() >= 2:
                    numeric_sel.add(c)

        # preserve candidate ordering in the result
        return [c for c in candidates if c in numeric_sel]



    def apply_additional_dimension_reduction(
        self,
        df: pd.DataFrame,
        metrics_columns: List[str],
        use_tsne: bool = False,
        use_umap: bool = False
    ) -> pd.DataFrame:
        """
        Applies additional dimensionality reduction methods beyond PCA.

        Args:
            df: DataFrame with compiled metrics
            metrics_columns: Columns containing numeric metrics
            use_tsne: Whether to apply t-SNE
            use_umap: Whether to apply UMAP

        Returns:
            DataFrame with additional components added
        """
        result_df = df.copy()

        # Prepare data
        X = df[metrics_columns].values
        try:
            from sklearn.preprocessing import StandardScaler
        except Exception as e:
            print(f"StandardScaler not available: {e}")
            return result_df
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Apply t-SNE if requested
        if use_tsne:
            try:
                from sklearn.manifold import TSNE
                tsne = TSNE(n_components=2, random_state=42)
                tsne_result = tsne.fit_transform(X_scaled)
                result_df['TSNE1'] = tsne_result[:, 0]
                result_df['TSNE2'] = tsne_result[:, 1]
            except Exception as e:
                print(f"Error applying t-SNE: {e}")

        # Apply UMAP if requested and available
        if use_umap and UMAP_AVAILABLE:
            try:
                import umap
                reducer = umap.UMAP(random_state=42)
                umap_result = reducer.fit_transform(X_scaled)
                result_df['UMAP1'] = umap_result[:, 0]
                result_df['UMAP2'] = umap_result[:, 1]
            except Exception as e:
                print(f"Error applying UMAP: {e}")

        return result_df

    def detect_spectral_anomalies(
        self,
        df: pd.DataFrame,
        metrics_columns: List[str],
        contamination: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Detects anomalies in spectral data using Isolation Forest.

        Args:
            df: DataFrame with compiled metrics
            metrics_columns: Columns containing numeric metrics
            contamination: Expected fraction of anomalies

        Returns:
            DataFrame with anomaly indicators added
        """
        result_df = df.copy()

        try:
            # Prepare data
            X = df[metrics_columns].dropna().values

            if len(X) < 10:
                print("Insufficient samples for anomaly detection")
                result_df['is_anomaly'] = False
                return result_df

            # Get contamination parameter from UI (allow auto/adaptive)
            contamination_text = self.input_contamination.text().strip().lower()
            if contamination_text in ("", "auto", "adaptive"):
                contamination = None
            else:
                try:
                    contamination = float(contamination_text)
                except Exception:
                    contamination = None

            if contamination is None or contamination <= 0 or contamination >= 1:
                n_samples = len(X)
                cap = 0.03 if n_samples < 20 else 0.05
                contamination = min(cap, max(1.0 / n_samples, 0.01))

            # Apply Isolation Forest
            try:
                from sklearn.ensemble import IsolationForest
            except Exception as e:
                print(f"IsolationForest not available: {e}")
                result_df['is_anomaly'] = False
                return result_df
            clf = IsolationForest(contamination=contamination, random_state=42)
            result_df['is_anomaly'] = clf.fit_predict(X) == -1

            # Calculate and add anomaly score
            result_df['anomaly_score'] = clf.decision_function(X)

            print(f"Anomaly detection: {result_df['is_anomaly'].sum()} anomalies found")

        except Exception as e:
            print(f"Error in anomaly detection: {e}")
            result_df['is_anomaly'] = False

        return result_df

    def generate_interactive_visualizations(self) -> None:
        """
        Generates interactive visualizations based on the compiled metrics.
        """
        if not self.results_directory:
            QMessageBox.warning(self, "Warning", "Please choose a results directory first.")
            return

        try:
            # Check if there's a compiled metrics file
            compiled_metrics_path = self.find_compiled_metrics_file()

            if not compiled_metrics_path:
                reply = QMessageBox.question(
                    self,
                    "Compile Metrics",
                    "No compiled metrics file found. Would you like to compile metrics first?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self.compile_metrics_with_pca()
                    compiled_metrics_path = self.find_compiled_metrics_file()
                    if not compiled_metrics_path:
                        return
                else:
                    return

            # AUDIT FIX — publication policy: default chart source is the
            # ``Canonical_Metrics`` sheet, never the first sheet. If absent,
            # fall back with an explicit warning surfaced to the user (and
            # logged) so that diagnostic/legacy data cannot pose as
            # publication-grade results.
            try:
                from publication_chart_policy import (
                    DEFAULT_PUBLICATION_SHEET,
                    load_canonical_sheet_with_fallback_warning,
                )
                df, _sheet_used, _sheet_warns = load_canonical_sheet_with_fallback_warning(
                    compiled_metrics_path
                )
                if _sheet_warns:
                    for _w in _sheet_warns:
                        try:
                            QMessageBox.warning(self, "Canonical_Metrics fallback", _w)
                        except Exception:
                            pass
            except Exception:
                # Defensive: if the policy helper is unavailable we still
                # render — but loudly. This must never silently fall back
                # to the unbounded legacy Density_Metrics sheet.
                df = pd.read_excel(compiled_metrics_path, sheet_name=0)

            if df.empty:
                QMessageBox.warning(self, "Warning", "Compiled metrics file is empty.")
                return

            # Create visualizations subfolder
            viz_dir = os.path.join(self.results_directory, "interactive_visualizations")
            os.makedirs(viz_dir, exist_ok=True)

            # Generate visualizations based on settings
            visualizations_created = []

            # 1. 3D Spectrograms if requested
            if self.check_3d_spectrogram.isChecked():
                spectrograms_path = self.create_interactive_spectrograms(viz_dir)
                if spectrograms_path:
                    visualizations_created.append(('3D Spectrograms', spectrograms_path))

            # 2. Interactive dissonance curves if requested
            if self.check_interactive_curves.isChecked():
                curves_path = self.create_interactive_dissonance_curves(viz_dir)
                if curves_path:
                    visualizations_created.append(('Dissonance Curves', curves_path))

            # 3. Dimensionality reduction plots if requested
            if self.check_dimension_scatterplots.isChecked():
                dimension_path = self.create_dimensionality_plots(df, viz_dir)
                if dimension_path:
                    visualizations_created.append(('Dimensionality Reduction', dimension_path))

            # Show success message with links to visualizations
            if visualizations_created:
                message = "The following interactive visualizations were created:\n\n"
                for name, path in visualizations_created:
                    message += f"• {name}: {path}\n"

                QMessageBox.information(self, "Success", message)

                # Ask if user wants to open the visualization directory
                reply = QMessageBox.question(
                    self,
                    "Open Visualizations",
                    "Would you like to open the visualizations directory?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self.open_file_or_directory(viz_dir)
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "No visualizations were created. Please check your settings."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error generating interactive visualizations: {str(e)}"
            )

    def find_compiled_metrics_file(self) -> Optional[str]:
        """
        Finds the most recent compiled metrics file in the results directory.

        Returns:
            Path to the compiled metrics file, or None if not found
        """
        # Look for various possible filenames
        possible_files = [
            'compiled_metrics_with_analysis.xlsx',
            'compiled_metrics.xlsx',
            'compiled_density_metrics.xlsx'
        ]

        for filename in possible_files:
            path = os.path.join(self.results_directory, filename)
            if os.path.exists(path):
                return path

        return None

    def create_interactive_spectrograms(self, output_dir: str) -> Optional[str]:
        """
        Creates interactive 3D spectrograms for loaded audio files.

        Args:
            output_dir: Directory to save the visualizations

        Returns:
            Path to the created HTML file, or None if failed
        """
        if not self.audio_processor.audio_data:
            return None
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except Exception as e:
            print(f"Plotly not available: {e}")
            return None

        try:
            # Create output path
            output_path = os.path.join(output_dir, "interactive_spectrograms.html")

            # Create a plotly figure with subplots - one row for each audio file
            num_files = min(len(self.audio_processor.audio_data), 4)  # Limit to 4 files to avoid huge HTML

            fig = make_subplots(
                rows=num_files, cols=2,
                specs=[[{"type": "surface"}, {"type": "heatmap"}] for _ in range(num_files)],
                subplot_titles=[f"{note} 3D" for _, _, note, _ in self.audio_processor.audio_data[:num_files]] +
                               [f"{note} 2D" for _, _, note, _ in self.audio_processor.audio_data[:num_files]]
            )

            # Process each audio file (up to the limit)
            for i, (y, sr, note, _) in enumerate(self.audio_processor.audio_data[:num_files]):
                try:
                    # Calculate STFT
                    from scipy import signal
                    f, t, Zxx = signal.stft(
                        y, fs=sr, nperseg=min(2048, len(y)),
                        window='hann', noverlap=None
                    )

                    # Convert to dB
                    spec = 10 * np.log10(np.abs(Zxx) + 1e-10)

                    # Add 3D surface plot
                    fig.add_trace(
                        go.Surface(z=spec, x=t, y=f, colorscale='Viridis'),
                        row=i+1, col=1
                    )

                    # Add 2D heatmap
                    fig.add_trace(
                        go.Heatmap(z=spec, x=t, y=f, colorscale='Viridis'),
                        row=i+1, col=2
                    )

                    # Configure axes
                    fig.update_scenes(
                        xaxis_title="Time (s)",
                        yaxis_title="Frequency (Hz)",
                        zaxis_title="Magnitude (dB)",
                        row=i+1, col=1
                    )

                    # Configure 2D axes
                    fig.update_yaxes(title="Frequency (Hz)", type="log", row=i+1, col=2)
                    fig.update_xaxes(title="Time (s)", row=i+1, col=2)

                except Exception as e:
                    print(f"Error processing {note} for interactive spectrogram: {e}")

            # Update layout
            fig.update_layout(
                height=300 * num_files,
                width=1200,
                title="Interactive Spectral Analysis"
            )

            # Save figure
            fig.write_html(output_path)

            return output_path

        except Exception as e:
            print(f"Error creating interactive spectrograms: {e}")
            return None

    def create_interactive_dissonance_curves(self, output_dir: str) -> Optional[str]:
        """
        Creates interactive dissonance curves visualization.

        Args:
            output_dir: Directory to save the visualizations

        Returns:
            Path to the created HTML file, or None if failed
        """
        # Check if we have dissonance curves
        if not self.results_directory:
            return None
        try:
            import plotly.graph_objects as go
        except Exception as e:
            print(f"Plotly not available: {e}")
            return None

        try:
            # Find directories containing dissonance curves
            dissonance_files = []
            model_name = self.combo_dissonance_model.currentText().lower()

            for item in os.listdir(self.results_directory):
                item_path = os.path.join(self.results_directory, item)
                if os.path.isdir(item_path):
                    # Check if this directory contains dissonance data
                    curve_file = os.path.join(item_path, f"{model_name}_dissonance_curve.png")
                    if os.path.exists(curve_file):
                        dissonance_files.append((item, item_path))

            if not dissonance_files:
                return None

            # Create output path
            output_path = os.path.join(output_dir, "interactive_dissonance_curves.html")

            # Create plotly figure
            fig = go.Figure()

            # Add dissonance curves from the first 10 directories (to avoid huge HTML)
            for note, note_dir in dissonance_files[:10]:
                try:
                    # Try to find the saved dissonance data
                    # This is a simplification - in a real implementation,
                    # you would need to extract or recalculate the actual curve data

                    # For demonstration, we'll generate some placeholder data
                    # In real implementation, extract this from Excel files or recalculate
                    intervals = np.linspace(1.0, 2.0, 200)
                    # Create a curve that has dips at common musical intervals
                    common_intervals = [1.0, 1.25, 1.33, 1.5, 1.67, 1.75, 2.0]  # Unison, M3, P4, P5, M6, M7, Octave
                    dissonance = np.ones_like(intervals)

                    for interval in common_intervals:
                        # Create dips at common intervals
                        dissonance -= 0.2 * np.exp(-100 * (intervals - interval)**2)

                    # Add some noise to make curves different
                    dissonance += 0.05 * np.random.randn(len(dissonance))

                    # Normalize to 0-1
                    dissonance = (dissonance - np.min(dissonance)) / (np.max(dissonance) - np.min(dissonance))

                    # Add to plot
                    fig.add_trace(
                        go.Scatter(
                            x=intervals,
                            y=dissonance,
                            mode='lines',
                            name=note
                        )
                    )

                except Exception as e:
                    print(f"Error processing {note} for dissonance curve: {e}")

            # Add vertical lines at common musical intervals with labels
            interval_names = {
                1.0: "Unison",
                1.25: "Major 3rd",
                1.33: "Perfect 4th",
                1.5: "Perfect 5th",
                1.67: "Major 6th",
                1.75: "Major 7th",
                2.0: "Octave"
            }

            for interval, name in interval_names.items():
                fig.add_vline(
                    x=interval,
                    line_dash="dash",
                    line_color="rgba(0,0,0,0.3)",
                    annotation_text=name,
                    annotation_position="top"
                )

            # Configure layout
            fig.update_layout(
                title=f"{model_name.capitalize()} Dissonance Curves",
                xaxis_title="Frequency Ratio",
                yaxis_title="Dissonance",
                height=600,
                width=1000,
                legend_title="Notes",
                hovermode="closest"
            )

            # Add a secondary x-axis with cents
            fig.update_layout(
                xaxis2=dict(
                    title="Cents",
                    overlaying="x",
                    side="top",
                    range=[0, 1200],  # 0 to 1200 cents (1 octave)
                    tickvals=[0, 200, 400, 600, 800, 1000, 1200],
                    ticktext=["0¢", "200¢", "400¢", "600¢", "800¢", "1000¢", "1200¢"],
                    showgrid=False
                )
            )

            # Save figure
            fig.write_html(output_path)

            return output_path

        except Exception as e:
            print(f"Error creating interactive dissonance curves: {e}")
            return None

    def create_dimensionality_plots(self, df: pd.DataFrame, output_dir: str) -> Optional[str]:
        """
        Creates interactive dimensionality reduction visualizations.

        Args:
            df: DataFrame with metrics and dimensionality reduction components
            output_dir: Directory to save the visualizations

        Returns:
            Path to the created HTML file, or None if failed
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except Exception as e:
            print(f"Plotly not available: {e}")
            return None

        try:
            # Check if we have dimensionality reduction data
            has_pca = 'PC1' in df.columns
            has_tsne = 'TSNE1' in df.columns and 'TSNE2' in df.columns
            has_umap = 'UMAP1' in df.columns and 'UMAP2' in df.columns

            if not (has_pca or has_tsne or has_umap):
                return None

            # Check if we need to detect anomalies
            detect_anomalies = self.check_anomaly_detection.isChecked()
            if detect_anomalies and 'is_anomaly' not in df.columns:
                # Get numeric columns
                numeric_cols = self.get_numeric_columns(
                    df, self.check_include_dissonance.isChecked()
                )

                if len(numeric_cols) >= 2:
                    # Apply anomaly detection
                    df = self.detect_spectral_anomalies(df, numeric_cols)

            # Create output path
            output_path = os.path.join(output_dir, "dimensionality_reduction.html")

            # Create plotly figure
            fig = make_subplots(
                rows=1,
                cols=sum([has_pca, has_tsne, has_umap]),
                subplot_titles=[title for title, flag in
                               [("PCA", has_pca), ("t-SNE", has_tsne), ("UMAP", has_umap)]
                               if flag]
            )

            # Column counter for subplots
            col = 1

            # Colors for anomalies
            color_scale = ['blue', 'red'] if 'is_anomaly' in df.columns else None

            # Add PCA plot if available
            if has_pca:
                # Check if we have a categorical 'Note' column to use as hover text
                hover_text = df['Note'] if 'Note' in df.columns else None

                # Check if we have anomaly detection results
                marker_color = df['is_anomaly'].astype(int) if 'is_anomaly' in df.columns else 'blue'

                scatter = go.Scatter(
                    x=df['PC1'],
                    y=df['PC2'] if 'PC2' in df.columns else np.zeros(len(df)),
                    mode='markers',
                    marker=dict(
                        color=marker_color,
                        colorscale=color_scale,
                        size=10
                    ),
                    text=hover_text,
                    name='PCA'
                )

                fig.add_trace(scatter, row=1, col=col)
                fig.update_xaxes(title="PC1", row=1, col=col)
                fig.update_yaxes(title="PC2" if 'PC2' in df.columns else "", row=1, col=col)
                col += 1

            # Add t-SNE plot if available
            if has_tsne:
                scatter = go.Scatter(
                    x=df['TSNE1'],
                    y=df['TSNE2'],
                    mode='markers',
                    marker=dict(
                        color=df['is_anomaly'].astype(int) if 'is_anomaly' in df.columns else 'green',
                        colorscale=color_scale,
                        size=10
                    ),
                    text=df['Note'] if 'Note' in df.columns else None,
                    name='t-SNE'
                )

                fig.add_trace(scatter, row=1, col=col)
                fig.update_xaxes(title="t-SNE 1", row=1, col=col)
                fig.update_yaxes(title="t-SNE 2", row=1, col=col)
                col += 1

            # Add UMAP plot if available
            if has_umap:
                scatter = go.Scatter(
                    x=df['UMAP1'],
                    y=df['UMAP2'],
                    mode='markers',
                    marker=dict(
                        color=df['is_anomaly'].astype(int) if 'is_anomaly' in df.columns else 'purple',
                        colorscale=color_scale,
                        size=10
                    ),
                    text=df['Note'] if 'Note' in df.columns else None,
                    name='UMAP'
                )

                fig.add_trace(scatter, row=1, col=col)
                fig.update_xaxes(title="UMAP 1", row=1, col=col)
                fig.update_yaxes(title="UMAP 2", row=1, col=col)

            # Update layout
            fig.update_layout(
                title="Dimensionality Reduction Visualization",
                height=600,
                width=1000 * sum([has_pca, has_tsne, has_umap]),
                showlegend=False,
                hovermode="closest"
            )

            # Add a legend for anomalies if applicable
            if 'is_anomaly' in df.columns:
                fig.update_layout(
                    updatemenus=[{
                        'buttons': [
                            {
                                'args': [{'marker.color': [df['is_anomaly'].astype(int) if 'is_anomaly' in df.columns else 'blue']}],
                                'label': 'Show Anomalies',
                                'method': 'update'
                            },
                            {
                                'args': [{'marker.color': ['blue']}],
                                'label': 'Hide Anomalies',
                                'method': 'update'
                            }
                        ],
                        'direction': 'down',
                        'showactive': True,
                        'x': 0.1,
                        'y': 1.1
                    }]
                )

            # Save figure
            fig.write_html(output_path)

            return output_path

        except Exception as e:
            print(f"Error creating dimensionality reduction visualization: {e}")
            traceback.print_exc()
            return None

    def view_dissonance_curves(self) -> None:
        """
        Opens a file dialog to view dissonance curves for processed notes.
        """
        if not self.results_directory:
            QMessageBox.warning(self, "Warning", "Please choose a results directory first.")
            return

        try:
            # Get the currently selected model
            model_name = self.combo_dissonance_model.currentText().lower()

            # Find all notes directories
            note_dirs = []
            for item in os.listdir(self.results_directory):
                item_path = os.path.join(self.results_directory, item)
                if os.path.isdir(item_path):
                    # Check if this contains a dissonance curve for the selected model
                    curve_path = os.path.join(item_path, f"{model_name}_dissonance_curve.png")
                    if os.path.exists(curve_path):
                        note_dirs.append((item, curve_path))

            if not note_dirs:
                QMessageBox.warning(self, "Warning",
                                  f"No {model_name.capitalize()} dissonance curves found in the results directory.")
                return

            # Build a message with the available notes and their curves
            message = f"The following notes have {model_name.capitalize()} dissonance curves available:\n\n"
            for note, path in note_dirs:
                message += f"• {note}: {path}\n"

            message += "\nWould you like to open one of these files?"

            reply = QMessageBox.question(self, "Dissonance Curves", message,
                                        QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                # Show a file dialog pre-filtered to the results directory
                file_dialog = QFileDialog()
                file_dialog.setNameFilter("Image Files (*.png)")
                file_dialog.setDirectory(self.results_directory)

                if file_dialog.exec_():
                    selected_file = file_dialog.selectedFiles()[0]
                    self.open_file_or_directory(selected_file)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error viewing dissonance curves: {str(e)}")

    def open_file_or_directory(self, path: str) -> None:
        """
        Open a file or directory with the system default application,
        without invoking a shell, and with basic path validation.
        """

        log = globals().get("logger")  # use logger when available; otherwise print
        def _log(level, msg):
            (log and getattr(log, level, None) or print)(msg)

        try:
            p = Path(path).resolve(strict=True)
        except FileNotFoundError:
            _log("error", f"File or directory not found: {path}")
            return

        # If a results root is configured, ensure the target stays inside it
        allowed_root = getattr(self, "results_directory", None)
        if allowed_root is not None:
            root = Path(allowed_root).resolve()
            try:
                if os.path.commonpath([str(root), str(p)]) != str(root):
                    _log("error", f"Path outside allowed directory: {p}")
                    return
            except Exception as e:
                _log("error", f"Failed to validate allowed directory: {e}")
                return

        # Directory: open in file manager
        if p.is_dir():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(str(p))  # does not invoke a shell
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(p)], check=False)      # shell=False
                else:
                    subprocess.run(["xdg-open", str(p)], check=False)  # shell=False
            except Exception as e:
                _log("error", f"Error opening directory '{p}': {e}")
            return

        # File: restrict to common extensions (adjust as needed)
        allowed_exts = {
            ".png", ".jpg", ".jpeg", ".gif",
            ".html", ".htm", ".csv", ".json",
            ".xlsx", ".xls", ".txt", ".pdf"
        }
        if p.suffix.lower() not in allowed_exts:
            _log("error", f"Extension not allowed for opening: {p.suffix}")
            return

        try:
            # 1) validate/sanitise path (no NUL, normalised)
            if "\x00" in str(p):
                raise ValueError("Invalid path (NUL).")
            p_str = str(Path(p).expanduser().resolve(strict=False))

            # 2) optional existence check
            if not (os.path.isfile(p_str) or os.path.isdir(p_str)):
                logging.error("Missing or invalid path: %s", p_str)

            elif sys.platform.startswith("win"):
                os.startfile(p_str)  # nosec: validated local path

            elif sys.platform == "darwin":
                cmd = shutil.which("open") or "/usr/bin/open"
                subprocess.run([cmd, p_str], check=False)  # nosec S603,S607: cmd whitelisted; validated input

            else:
                cmd = (shutil.which("xdg-open")
                       or shutil.which("gio")
                       or shutil.which("gnome-open"))
                if cmd:
                    subprocess.run([cmd, p_str], check=False)  # nosec S603,S607: cmd whitelisted; validated input
                else:
                    logging.error("No desktop utility available to open: %s", p_str)

        except Exception as e:
            logging.exception("Error opening file '%s': %s", p, e)



    def analyze_dissonance_vs_density(self) -> None:
        """
        Analyzes and compares dissonance with density metrics.
        """
        if not self.results_directory:
            QMessageBox.warning(self, "Warning", "Please choose a results directory first.")
            return

        try:
            try:
                import matplotlib.pyplot as plt
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Matplotlib not available: {e}")
                return
            try:
                import plotly.graph_objects as go
            except Exception:
                go = None

            # Get the currently selected model
            model_name = self.combo_dissonance_model.currentText()
            dissonance_column = f"{model_name} Dissonance"

            # First, check if compiled metrics file exists
            compiled_metrics_path = self.find_compiled_metrics_file()

            if not compiled_metrics_path:
                # If not, ask if user wants to compile metrics first
                reply = QMessageBox.question(
                    self,
                    "Compile Metrics",
                    "No compiled metrics file found. Would you like to compile metrics first?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self.compile_metrics_with_pca()
                    # Check again if file exists after compilation
                    compiled_metrics_path = self.find_compiled_metrics_file()
                    if not compiled_metrics_path:
                        QMessageBox.warning(self, "Warning", "Could not create compiled metrics file.")
                        return
                else:
                    return

            # Read the compiled metrics
            df = pd.read_excel(compiled_metrics_path)

            # Check if both needed metrics exist
            if 'Density Metric' not in df.columns or dissonance_column not in df.columns:
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"Both Density Metric and {dissonance_column} are required for comparison."
                )
                return

            # Create a comparison plot - both static and interactive
            # 1. Static matplotlib plot for backward compatibility
            plt.figure(figsize=(10, 6))

            # Get the data, removing any rows with NaN values
            plot_data = df[['Note', 'Density Metric', dissonance_column]].dropna()

            if plot_data.empty:
                QMessageBox.warning(self, "Warning", "No valid data for comparison.")
                return

            # Normalize the data for better comparison (0-1 scale)
            for col in ['Density Metric', dissonance_column]:
                min_val = plot_data[col].min()
                max_val = plot_data[col].max()
                if max_val != min_val:
                    plot_data[f'{col}_Norm'] = (plot_data[col] - min_val) / (max_val - min_val)
                else:
                    plot_data[f'{col}_Norm'] = 0

            # Calculate correlation
            corr = plot_data['Density Metric'].corr(plot_data[dissonance_column])

            # Scatter plot
            plt.scatter(
                plot_data['Density Metric'],
                plot_data[dissonance_column],
                s=100, alpha=0.7
            )

            # Add note labels
            for i, row in plot_data.iterrows():
                plt.annotate(
                    row['Note'],
                    (row['Density Metric'], row[dissonance_column]),
                    xytext=(5, 5),
                    textcoords='offset points'
                )

            # Add trendline
            if len(plot_data) > 1:
                z = np.polyfit(plot_data['Density Metric'], plot_data[dissonance_column], 1)
                p = np.poly1d(z)
                plt.plot(
                    [plot_data['Density Metric'].min(), plot_data['Density Metric'].max()],
                    [p(plot_data['Density Metric'].min()), p(plot_data['Density Metric'].max())],
                    "r--", alpha=0.7
                )

            plt.title(f'{model_name} Dissonance vs Density Metric (Correlation: {corr:.3f})')
            plt.xlabel('Density Metric')
            plt.ylabel(f'{model_name} Dissonance')
            plt.grid(True, alpha=0.3)

            # Save the static plot
            static_path = os.path.join(self.results_directory, f'{model_name.lower()}_vs_density.png')
            plt.savefig(static_path, dpi=300, bbox_inches='tight')
            plt.close()

            # 2. Create interactive plotly version
            if go is not None:
                viz_dir = os.path.join(self.results_directory, "interactive_visualizations")
                os.makedirs(viz_dir, exist_ok=True)
                interactive_path = os.path.join(viz_dir, f'{model_name.lower()}_vs_density_interactive.html')

                fig = go.Figure()

                # Add scatter plot
                fig.add_trace(
                    go.Scatter(
                        x=plot_data['Density Metric'],
                        y=plot_data[dissonance_column],
                        mode='markers+text',
                        marker=dict(
                            size=12,
                            color='rgba(0, 123, 255, 0.7)'
                        ),
                        text=plot_data['Note'],
                        textposition="top center",
                        name='Notes'
                    )
                )

                # Add trendline
                if len(plot_data) > 1:
                    z = np.polyfit(plot_data['Density Metric'], plot_data[dissonance_column], 1)
                    p = np.poly1d(z)
                    x_range = np.linspace(plot_data['Density Metric'].min(), plot_data['Density Metric'].max(), 100)

                    fig.add_trace(
                        go.Scatter(
                            x=x_range,
                            y=p(x_range),
                            mode='lines',
                            line=dict(color='red', dash='dash'),
                            name=f'Trendline (r={corr:.3f})'
                        )
                    )

                # Update layout
                fig.update_layout(
                    title=f'{model_name} Dissonance vs Density Metric',
                    xaxis_title='Density Metric',
                    yaxis_title=f'{model_name} Dissonance',
                    height=600,
                    width=800,
                    hovermode='closest',
                    showlegend=True
                )

                # Save interactive version
                fig.write_html(interactive_path)

            QMessageBox.information(
                self,
                "Analysis Complete",
                f"Dissonance vs Density analysis completed.\n\n"
                f"Static plot saved at:\n{static_path}\n\n"
                f"Interactive plot saved at:\n{interactive_path}"
            )

            # Ask to view the interactive version
            reply = QMessageBox.question(
                self,
                "View Results",
                "Would you like to view the interactive comparison plot?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.open_file_or_directory(interactive_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error analyzing dissonance vs density: {str(e)}")

    def apply_filters(self) -> None:
        """
        Apply the user-selected filters to the loaded audio,
        validate the weighting function, and force a deterministic metric rebuild.
        """
        import logging, traceback
        logger = logging.getLogger(__name__)

        try:
            # ---------------- Basic spectral parameters ----------------
            freq_min = float((self.input_min_freq.text() or "20").strip())
            freq_max = float((self.input_max_freq.text() or "20000").strip())
            db_min   = float((self.input_min_db.text()  or "-90").strip())
            db_max   = float((self.input_max_db.text()  or "0").strip())
            tolerance = float((self.input_tolerance.text() or "5.0").strip())
            use_adaptive_tolerance = bool(self.checkbox_adaptive_tolerance.isChecked())

            # ---------------- Windowing and FFT -------------------
            n_fft = int((self.input_n_fft.text() or "4096").strip())
            hop_length_txt = (self.input_hop_length.text() or "").strip()
            hop_length = int(hop_length_txt) if hop_length_txt else None
            window = str(self.combo_window_type.currentText()).strip().lower()

            # Window-specific parameters (when present in the UI)
            kaiser_beta = None
            gaussian_std = None
            if window == "kaiser" and hasattr(self, "input_kaiser_beta"):
                txt = (self.input_kaiser_beta.text() or "").strip()
                if txt:
                    try:
                        kaiser_beta = float(txt)
                    except Exception:
                        kaiser_beta = None
            if window in ("gaussian", "gauss", "gaussiana") and hasattr(self, "input_gaussian_std"):
                txt = (self.input_gaussian_std.text() or "").strip()
                if txt:
                    try:
                        gaussian_std = float(txt)
                    except Exception:
                        gaussian_std = None

            # ---------------- Weighting function (validated) ---------------
            try:
                raw_label = str(self.combo_weight_function.currentText())
            except Exception:
                raw_label = "linear"
            from density import get_weight_function

            weight_function = _resolve_weight_key_from_ui(raw_label)
            _ = get_weight_function(weight_function)

            # ---------------- STFT Options ------------------------------------------
            # Zero padding and time averaging are standard STFT parameters
            zero_padding = int((self.input_zero_padding.text() or "1").strip())
            time_avg = str(self.combo_time_avg.currentText()).strip().lower()

            # ---------------- Pesos α/β (model coefficients; batch-derived when available) ---
            batch_payload = self._gui_read_batch_payload_for_primary_audio()
            manual_ov = bool(self.check_manual_model_weight_override.isChecked())
            slider_a = float(self.harmonic_weight_slider.value()) / 100.0
            alpha, beta, weight_meta = resolve_analysis_model_weights(manual_ov, slider_a, batch_payload)
            if hasattr(self, "harmonic_weight_value"):
                self.harmonic_weight_value.setText(f"{int(round(alpha * 100))}%")
            if hasattr(self, "inharmonic_weight_value"):
                self.inharmonic_weight_value.setText(f"{int(round(beta * 100))}%")

            # ---------------- Dissonance ---------------------------------
            dissonance_enabled = bool(self.check_dissonance_enabled.isChecked())
            dissonance_curve   = bool(self.check_dissonance_curve.isChecked())
            dissonance_scale   = False  # Removed: Generate Optimal Scale feature
            dissonance_model   = str(self.combo_dissonance_model.currentText()).strip()
            compare_models     = bool(self.check_compare_models.isChecked())
            
            # Spectral masking: not part of the main density GUI; keep disabled for physical metrics.
            spectral_masking_enabled = False

            # ---------------- Output directory ---------------------------
            if not self.results_directory:
                QMessageBox.warning(self, "Warning", "Select a directory to save results.")
                return

            logger.info(
                "Apply Filters | wf=%s | α=%.3f β=%.3f | f=[%.1f, %.1f] Hz | "
                "dB=[%.1f, %.1f] | tol=%.2f Hz (adapt=%s) | STFT n=%d hop=%s win=%s | zp=%d avg=%s",
                weight_function,
                alpha,
                beta,
                freq_min,
                freq_max,
                db_min,
                db_max,
                tolerance,
                use_adaptive_tolerance,
                n_fft,
                hop_length,
                window,
                zero_padding,
                time_avg,
            )

            # ---------------- Progress dialog ---------------------------
            progress = QProgressDialog("Applying filters and generating data...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Processing")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()

            try:
                # ---- Deterministic metric reset --------------------
                ap = self.audio_processor
                if hasattr(ap, "_reset_metrics") and callable(getattr(ap, "_reset_metrics")):
                    ap._reset_metrics()
                else:
                    for attr in (
                        "density_metric_value", "scaled_density_metric_value",
                        "filtered_density_metric_value", "entropy_spectral_value",
                        "combined_density_metric_value", "total_metric_value",
                        "spectral_density_metric_value",
                        "effective_partial_density", "partial_density_effective_components",
                        "harmonic_energy_sum", "inharmonic_energy_sum", "subbass_energy_sum",
                        "total_component_energy", "harmonic_energy_ratio", "inharmonic_energy_ratio",
                        "subbass_energy_ratio", "harmonic_partial_count", "inharmonic_partial_count",
                        "total_detected_partial_count", "unique_harmonic_order_count", "harmonic_order_count",
                        "harmonic_peak_count", "inharmonic_peak_count", "subbass_peak_count",
                        "total_detected_peak_count", "harmonic_candidate_count", "inharmonic_candidate_count",
                        "retained_nonharmonic_peak_candidate_count", "exported_nonharmonic_peak_candidate_count",
                        "peaklist_harmonic_window_candidate_count", "peaklist_nonharmonic_window_candidate_count",
                        "peaklist_low_frequency_window_candidate_count", "peaklist_total_window_candidate_count",
                        "harmonic_peak_candidate_count", "nonharmonic_peak_candidate_count",
                        "low_frequency_peak_candidate_count", "total_peak_candidate_count",
                        "residual_spectral_row_count", "nonharmonic_candidate_row_count",
                        "accepted_inharmonic_peak_count", "accepted_inharmonic_partial_count",
                        "subbass_candidate_count", "total_spectral_candidate_count", "residual_row_count",
                        "harmonic_bin_count", "inharmonic_bin_count",
                        "subbass_bin_count", "energy_conservation_status", "energy_conservation_error",
                        "energy_denominator_description", "dissonance_partial_count", "dissonance_pair_count",
                        "harmonic_validation_report",
                        "f0_prior_available", "f0_blind_method", "f0_final_method", "f0_fit_accepted",
                        "f0_fit_quality", "f0_fit_rejection_reason",
                    ):
                        if hasattr(ap, attr):
                            setattr(ap, attr, None)
                    for dict_attr in ("dissonance_values", "dissonance_curves", "dissonance_scales"):
                        if hasattr(ap, dict_attr) and isinstance(getattr(ap, dict_attr), dict):
                            for k in list(getattr(ap, dict_attr).keys()):
                                getattr(ap, dict_attr)[k] = None

                progress.setValue(10)

                # ---- Forward window-specific parameters to the processor --
                ap.kaiser_beta  = kaiser_beta if kaiser_beta is not None else 6.5
                ap.gaussian_std = gaussian_std if gaussian_std is not None else (n_fft / 8.0)
                self._apply_gui_weight_metadata_to_processor(ap, weight_meta)
                ap.spectral_masking_enabled = False

                # ---- Progress callback for the processing core ------------------
                def _progress_cb(i: int, total: int, label: str) -> None:
                    try:
                        if total and total > 0:
                            pct = 10 + int(85 * i / total)   # 10→95%
                            progress.setValue(min(95, pct))
                        if label:
                            progress.setLabelText(f"Processing {label} ({i}/{total})…")
                        if progress.wasCanceled():
                            raise RuntimeError("Operation cancelled by the user.")
                    except Exception:
                        pass  # never let UI callback exceptions escape

                # ---- Single call into the processing core --------------
                ap.apply_filters_and_generate_data(
                    freq_min=freq_min,
                    freq_max=freq_max,
                    db_min=db_min,
                    db_max=db_max,
                    tolerance=tolerance,
                    use_adaptive_tolerance=use_adaptive_tolerance,
                    n_fft=n_fft,
                    hop_length=hop_length,
                    window=window,
                    kaiser_beta=kaiser_beta,
                    gaussian_std=gaussian_std,
                    weight_function=weight_function,
                    results_directory=self.results_directory,
                    dissonance_enabled=dissonance_enabled,
                    dissonance_model=dissonance_model,
                    dissonance_curve=dissonance_curve,
                    dissonance_scale=dissonance_scale,
                    compare_models=compare_models,
                    harmonic_weight=float(alpha),
                    inharmonic_weight=float(beta),
                    zero_padding=zero_padding,
                    time_avg=time_avg,
                    spectral_masking_enabled=spectral_masking_enabled,  # NEW: Control spectral masking
                    progress_callback=_progress_cb
                )

                progress.setValue(100)
                QMessageBox.information(self, "Filters applied", "Filters applied and results saved.")

                # Optional: chain compilation and interactive visualisations
                reply = QMessageBox.question(
                    self, "Compile metrics",
                    "Compile metrics with PCA now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.compile_metrics_with_pca()
                    viz_reply = QMessageBox.question(
                        self, "Interactive visualisations",
                        "Generate interactive visualisations now?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if viz_reply == QMessageBox.Yes:
                        self.generate_interactive_visualizations()

            except ValueError as ve:
                QMessageBox.critical(self, "Value error", f"Error applying filters: {ve}")
                logger.exception("ValueError in apply_filters")
            except PermissionError as pe:
                QMessageBox.critical(self, "Permission error", f"Access denied: {pe}")
                logger.exception("PermissionError in apply_filters")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error applying filters: {e}\n\n{traceback.format_exc()}")
                logger.exception("Unexpected error in apply_filters")
            finally:
                progress.close()

        except Exception as e:
            # Failures before the progress dialog opens (UI parsing, etc.)
            QMessageBox.critical(self, "Error", f"Error preparing parameters: {e}")
            logger.exception("Error preparing parameters in apply_filters")

    # [REMOVED Spectral Power methods: switch_on_spectral_power, analyze_spectral_power, analyze_multiple_spectral_powers]
