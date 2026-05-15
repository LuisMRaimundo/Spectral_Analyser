#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super Audio Analyzer - GUI Interface
====================================
PyQt5-based graphical user interface for the Super Audio Analyzer.

Features:
- Audio file selection
- 90-tier system configuration
- Parameter configuration
- Real-time analysis progress
- Results visualization
- Spectrogram display
- Export capabilities
"""

import sys
import os
import traceback
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

# PyQt5 imports
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QComboBox, QFileDialog, QMessageBox,
        QTabWidget, QGroupBox, QFormLayout, QSlider, QProgressBar,
        QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QScrollArea
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
    from PyQt5.QtGui import QFont, QPixmap, QImage
    PYQT5_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QLineEdit, QComboBox, QFileDialog, QMessageBox,
            QTabWidget, QGroupBox, QFormLayout, QSlider, QProgressBar,
            QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QScrollArea
        )
        from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, Slot as pyqtSlot
        from PySide6.QtGui import QFont, QPixmap, QImage
        PYQT5_AVAILABLE = True
    except ImportError:
        PYQT5_AVAILABLE = False
        print("ERROR: PyQt5 or PySide6 not available. Please install with: pip install PyQt5")
        sys.exit(1)

# Matplotlib for embedding plots
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("WARNING: matplotlib not available. Plots will not be embedded.")

# Import the super analyzer
try:
    from super_audio_analyzer import SuperAudioAnalyzer, _format_detection_method_label
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    print("ERROR: super_audio_analyzer.py not found. Please ensure it's in the same directory.")


class SuperAnalysisWorker(QThread):
    """Worker thread for running super analysis without freezing GUI."""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    
    def __init__(self, analyzer_params: Dict[str, Any]):
        super().__init__()
        self.analyzer_params = analyzer_params
    
    def run(self):
        """Run the super analysis in background thread."""
        try:
            self.status.emit("Initializing Super Analyzer...")
            self.progress.emit(5)
            
            # Create analyzer
            analyzer = SuperAudioAnalyzer(**self.analyzer_params)
            self.progress.emit(10)
            
            # Load audio
            self.status.emit("Loading audio file...")
            analyzer.load_audio()
            # Emit stereo detection status
            if analyzer.is_stereo:
                self.status.emit(f"STEREO audio detected ({analyzer.audio_channels} channels) - Processing averaged channels...")
            else:
                self.status.emit(f"MONO audio detected ({analyzer.audio_channels} channel) - Processing...")
            self.progress.emit(15)
            
            # Compute spectrogram
            self.status.emit("Computing spectrogram (STFT)...")
            analyzer.compute_spectrogram()
            self.progress.emit(25)
            
            # Detect fundamental frequency
            self.status.emit("Detecting fundamental frequency (multi-method)...")
            analyzer.detect_fundamental_frequency()
            self.progress.emit(40)
            
            # Separate harmonic/inharmonic
            self.status.emit("Separating harmonic and inharmonic components...")
            analyzer.separate_harmonic_inharmonic()
            self.progress.emit(55)
            
            # Calculate metrics
            self.status.emit("Calculating spectral metrics...")
            analyzer.calculate_spectral_metrics()
            self.progress.emit(70)
            
            # Dissonance analysis
            self.status.emit("Calculating dissonance metrics...")
            analyzer.calculate_dissonance_metrics()
            self.progress.emit(80)
            
            # Statistical analysis
            self.status.emit("Performing statistical analysis...")
            analyzer.perform_statistical_analysis()
            self.progress.emit(90)
            
            # Dimensionality reduction
            self.status.emit("Performing dimensionality reduction...")
            analyzer.perform_dimensionality_reduction()
            self.progress.emit(95)
            
            # Internal consistency checks
            self.status.emit("Running internal consistency checks...")
            analyzer.run_internal_consistency_checks()
            self.progress.emit(97)
            
            # Generate visualizations
            self.status.emit("Generating visualizations...")
            analyzer.generate_comprehensive_plots()
            self.progress.emit(99)
            
            # Save results
            self.status.emit("Saving results...")
            analyzer.save_results()
            self.progress.emit(100)
            
            self.status.emit("Super analysis complete!")
            self.finished.emit(analyzer.results)
            
        except Exception as e:
            error_msg = f"Error during super analysis: {str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class SuperAudioAnalyzerGUI(QMainWindow):
    """Main GUI window for Super Audio Analyzer."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Super Audio Analyzer - State-of-the-Art Edition')
        self.setGeometry(100, 100, 1600, 1000)
        
        # Data storage
        self.audio_file_path: Optional[Path] = None
        self.output_dir: Optional[Path] = None
        self.analysis_results: Optional[Dict[str, Any]] = None
        self.analyzer: Optional[SuperAudioAnalyzer] = None
        
        # Batch processing data storage
        self.batch_files_list: List[Path] = []
        self.batch_output_dir: Path = Path("batch_results")
        
        # Worker thread
        self.worker: Optional[SuperAnalysisWorker] = None
        
        # Initialize UI
        self.init_ui()
        
        # Set default output directory
        default_output = Path.home() / "SuperAudioAnalysis"
        default_output.mkdir(exist_ok=True)
        self.output_dir = default_output
        self.output_dir_label.setText(f"Output: {self.output_dir}")
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set style
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgb(245, 245, 250);
            }
            QPushButton {
                background-color: rgb(70, 130, 180);
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgb(100, 149, 237);
            }
            QPushButton:pressed {
                background-color: rgb(65, 105, 225);
            }
            QPushButton:disabled {
                background-color: rgb(200, 200, 200);
                color: rgb(100, 100, 100);
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgb(200, 200, 200);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Setup tabs
        self.setup_file_tab()
        self.setup_batch_tab()
        self.setup_parameters_tab()
        self.setup_analysis_tab()
        self.setup_results_tab()
        self.setup_visualization_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready - Super Audio Analyzer")
    
    def setup_file_tab(self):
        """Setup file selection tab."""
        file_tab = QWidget()
        layout = QVBoxLayout()
        file_tab.setLayout(layout)
        
        # Audio file selection
        audio_group = QGroupBox("Audio File Selection")
        audio_layout = QVBoxLayout()
        
        self.audio_file_label = QLabel("No audio file selected")
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet("padding: 10px; background-color: white; border: 1px solid gray; border-radius: 3px;")
        
        browse_audio_btn = QPushButton("Browse Audio File...")
        browse_audio_btn.clicked.connect(self.browse_audio_file)
        browse_audio_btn.setStyleSheet("background-color: rgb(34, 139, 34);")
        
        audio_layout.addWidget(self.audio_file_label)
        audio_layout.addWidget(browse_audio_btn)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Output directory selection
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout()
        
        self.output_dir_label = QLabel("Output: Not set")
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setStyleSheet("padding: 10px; background-color: white; border: 1px solid gray; border-radius: 3px;")
        
        browse_output_btn = QPushButton("Browse Output Directory...")
        browse_output_btn.clicked.connect(self.browse_output_directory)
        browse_output_btn.setStyleSheet("background-color: rgb(34, 139, 34);")
        
        output_layout.addWidget(self.output_dir_label)
        output_layout.addWidget(browse_output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        self.tabs.addTab(file_tab, "File Selection")
    
    def setup_batch_tab(self):
        """Setup batch processing tab."""
        batch_tab = QWidget()
        layout = QVBoxLayout()
        batch_tab.setLayout(layout)
        
        # Batch file selection
        batch_group = QGroupBox("Batch Processing (Up to 100 Files)")
        batch_layout = QVBoxLayout()
        
        info_label = QLabel(
            "Select multiple audio files to analyze in batch mode.\n"
            "Files will be processed in parallel for efficiency."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #E6F3FF; border: 1px solid #4A90E2; border-radius: 3px;")
        
        self.batch_files_label = QLabel("No files selected (0/100)")
        self.batch_files_label.setWordWrap(True)
        self.batch_files_label.setStyleSheet("padding: 10px; background-color: white; border: 1px solid gray; border-radius: 3px; min-height: 100px;")
        
        browse_batch_btn = QPushButton("Select Multiple Audio Files...")
        browse_batch_btn.clicked.connect(self.browse_batch_files)
        browse_batch_btn.setStyleSheet("background-color: rgb(34, 139, 34);")
        
        clear_batch_btn = QPushButton("Clear Selection")
        clear_batch_btn.clicked.connect(self.clear_batch_files)
        clear_batch_btn.setStyleSheet("background-color: rgb(220, 20, 60);")
        
        batch_layout.addWidget(info_label)
        batch_layout.addWidget(self.batch_files_label)
        batch_layout.addWidget(browse_batch_btn)
        batch_layout.addWidget(clear_batch_btn)
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        # Batch output directory
        batch_output_group = QGroupBox("Batch Output Directory")
        batch_output_layout = QVBoxLayout()
        
        self.batch_output_dir_label = QLabel("Output: batch_results/")
        self.batch_output_dir_label.setWordWrap(True)
        self.batch_output_dir_label.setStyleSheet("padding: 10px; background-color: white; border: 1px solid gray; border-radius: 3px;")
        
        browse_batch_output_btn = QPushButton("Browse Batch Output Directory...")
        browse_batch_output_btn.clicked.connect(self.browse_batch_output_directory)
        browse_batch_output_btn.setStyleSheet("background-color: rgb(34, 139, 34);")
        
        batch_output_layout.addWidget(self.batch_output_dir_label)
        batch_output_layout.addWidget(browse_batch_output_btn)
        batch_output_group.setLayout(batch_output_layout)
        layout.addWidget(batch_output_group)
        
        # Batch processing button
        self.batch_files_list = []
        self.batch_output_dir = Path("batch_results")
        
        run_batch_btn = QPushButton("Run Batch Analysis")
        run_batch_btn.clicked.connect(self.run_batch_analysis)
        run_batch_btn.setStyleSheet("background-color: rgb(100, 149, 237); font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(run_batch_btn)
        
        layout.addStretch()
        self.tabs.addTab(batch_tab, "Batch Processing")
    
    def browse_batch_files(self):
        """Browse for multiple audio files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files for Batch Processing",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*)"
        )
        
        if file_paths:
            # Limit to 100 files
            if len(file_paths) > 100:
                QMessageBox.warning(
                    self,
                    "Too Many Files",
                    f"Maximum 100 files supported. Selected first 100 files."
                )
                file_paths = file_paths[:100]
            
            self.batch_files_list = [Path(f) for f in file_paths]
            file_names = "\n".join([f.name for f in self.batch_files_list[:10]])
            if len(self.batch_files_list) > 10:
                file_names += f"\n... and {len(self.batch_files_list) - 10} more"
            
            self.batch_files_label.setText(f"Selected {len(self.batch_files_list)} files:\n{file_names}")
            self.batch_files_label.setStyleSheet("padding: 10px; background-color: #E6FFE6; border: 1px solid #4CAF50; border-radius: 3px; min-height: 100px;")
    
    def clear_batch_files(self):
        """Clear batch file selection."""
        self.batch_files_list = []
        self.batch_files_label.setText("No files selected (0/100)")
        self.batch_files_label.setStyleSheet("padding: 10px; background-color: white; border: 1px solid gray; border-radius: 3px; min-height: 100px;")
    
    def browse_batch_output_directory(self):
        """Browse for batch output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Batch Output Directory",
            str(self.batch_output_dir)
        )
        
        if dir_path:
            self.batch_output_dir = Path(dir_path)
            self.batch_output_dir_label.setText(f"Output: {self.batch_output_dir}")
    
    def get_analyzer_params(self):
        """Get analyzer parameters from GUI settings (without audio_path)."""
        return {
            'sample_rate': self.sample_rate_spin.value(),
            'use_90_tier': self.use_90_tier_check.isChecked(),
            'harmonic_tolerance': self.harmonic_tolerance_spin.value(),
            'harmonic_weight': self.harmonic_weight_spin.value() if not self.auto_extract_weights_check.isChecked() else 0.95,
            'inharmonic_weight': self.inharmonic_weight_spin.value() if not self.auto_extract_weights_check.isChecked() else 0.05,
            'window': self.window_combo.currentText(),
            'use_adaptive_tolerance': self.adaptive_tolerance_check.isChecked(),
            'auto_extract_weights': self.auto_extract_weights_check.isChecked()
        }
    
    def run_batch_analysis(self):
        """Run batch analysis on selected files."""
        print(f"DEBUG: run_batch_analysis called")
        print(f"DEBUG: batch_files_list = {getattr(self, 'batch_files_list', 'NOT SET')}")
        
        # Validate files are selected
        if not hasattr(self, 'batch_files_list'):
            print("DEBUG: batch_files_list attribute not found")
            self.batch_files_list = []
        
        if not self.batch_files_list:
            print("DEBUG: batch_files_list is empty")
            QMessageBox.warning(
                self,
                "No Files Selected",
                "Please select audio files for batch processing.\n\n"
                "Steps:\n"
                "1. Go to the 'Batch Processing' tab\n"
                "2. Click 'Select Multiple Audio Files...'\n"
                "3. Choose your audio files (up to 100)\n"
                "4. Click 'Run Batch Analysis'"
            )
            return
        
        print(f"DEBUG: Found {len(self.batch_files_list)} files")
        
        # Validate that all files exist
        missing_files = [f for f in self.batch_files_list if not f.exists()]
        if missing_files:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"The following files do not exist:\n" + "\n".join([str(f) for f in missing_files[:5]])
            )
            return
        
        # Validate files are readable
        invalid_files = []
        for f in self.batch_files_list:
            if not f.is_file():
                invalid_files.append(f)
        if invalid_files:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"The following are not valid files:\n" + "\n".join([str(f) for f in invalid_files[:5]])
            )
            return
        
        # Get parameters from parameters tab
        try:
            analyzer_params = self.get_analyzer_params()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Parameter Error",
                f"Error getting analyzer parameters:\n{str(e)}\n\n"
                "Please check the Parameters tab settings."
            )
            return
        
        # Check for config file
        config_file = None
        config_path = Path("batch_config.json")
        if config_path.exists():
            config_file = config_path
            logger.info(f"Found batch config file: {config_file}")
        
        # Create batch analyzer
        try:
            from batch_audio_analyzer import BatchAudioAnalyzer
            
            self.statusBar().showMessage(f"Initializing batch analysis for {len(self.batch_files_list)} files...")
            
            batch_analyzer = BatchAudioAnalyzer(
                audio_files=self.batch_files_list,
                output_dir=self.batch_output_dir,
                max_workers=None,  # Auto-detect
                config_file=config_file,  # Pass config file if exists
                **analyzer_params
            )
            
            self.statusBar().showMessage(f"Processing {len(self.batch_files_list)} files...")
            
            # Run batch analysis (this may take a while)
            results = batch_analyzer.run_batch_analysis()
            
            # Show results
            QMessageBox.information(
                self,
                "Batch Analysis Complete",
                f"Batch analysis completed!\n\n"
                f"Total files: {len(self.batch_files_list)}\n"
                f"Successful: {results['summary']['successful_count']}\n"
                f"Failed: {results['summary']['failed_count']}\n\n"
                f"Results saved to:\n{self.batch_output_dir}\n\n"
                f"Check the output directory for:\n"
                f"- batch_results.json (detailed results)\n"
                f"- batch_summary.xlsx (summary table - Excel format)\n"
                f"- batch_statistics.txt (statistics report)"
            )
            
            self.statusBar().showMessage(f"Batch analysis complete! Results in {self.batch_output_dir}")
            
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Could not import batch_audio_analyzer:\n{str(e)}\n\n"
                "Please ensure batch_audio_analyzer.py is in the same directory."
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Batch Analysis Error",
                f"Error during batch analysis:\n{str(e)}\n\n"
                f"Details:\n{error_details[:500]}"
            )
            logger.error(f"Batch analysis error: {error_details}")
    
    def setup_parameters_tab(self):
        """Setup parameters configuration tab."""
        params_tab = QWidget()
        layout = QVBoxLayout()
        params_tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        
        # 90-Tier System
        tier_group = QGroupBox("90-Tier Granular Clustering System")
        tier_layout = QFormLayout()
        
        self.use_90_tier_check = QCheckBox("Enable 90-Tier System")
        self.use_90_tier_check.setChecked(True)
        self.use_90_tier_check.setToolTip("Enable frequency-optimized 90-tier clustering system")
        tier_layout.addRow("90-Tier System:", self.use_90_tier_check)
        
        tier_group.setLayout(tier_layout)
        scroll_layout.addWidget(tier_group)
        
        # FFT Parameters
        fft_group = QGroupBox("FFT Parameters")
        fft_layout = QFormLayout()
        
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(8000, 192000)
        self.sample_rate_spin.setValue(44100)
        self.sample_rate_spin.setSingleStep(1000)
        fft_layout.addRow("Sample Rate (Hz):", self.sample_rate_spin)
        
        self.window_combo = QComboBox()
        self.window_combo.addItems(['blackmanharris', 'hann', 'hamming', 'bartlett', 'kaiser', 'gaussian'])
        self.window_combo.setCurrentText('blackmanharris')
        fft_layout.addRow("Window Function:", self.window_combo)
        
        fft_group.setLayout(fft_layout)
        scroll_layout.addWidget(fft_group)
        
        # Harmonic/Inharmonic Parameters
        harmonic_group = QGroupBox("Harmonic/Inharmonic Separation")
        harmonic_layout = QFormLayout()
        
        self.harmonic_tolerance_spin = QDoubleSpinBox()
        self.harmonic_tolerance_spin.setRange(0.001, 0.1)
        self.harmonic_tolerance_spin.setValue(0.02)
        self.harmonic_tolerance_spin.setSingleStep(0.01)
        self.harmonic_tolerance_spin.setDecimals(3)
        self.harmonic_tolerance_spin.setToolTip("Harmonic detection tolerance (relative, e.g., 0.02 = 2%)")
        harmonic_layout.addRow("Harmonic Tolerance:", self.harmonic_tolerance_spin)
        
        # Auto-extract weights option (recommended)
        self.auto_extract_weights_check = QCheckBox("Auto-Extract Weights from Energy Distribution")
        self.auto_extract_weights_check.setChecked(True)
        self.auto_extract_weights_check.setToolTip("Automatically extract harmonic/inharmonic weights from actual energy distribution (recommended). Weights reflect true spectral characteristics.")
        harmonic_layout.addRow("Auto-Extract Weights:", self.auto_extract_weights_check)
        
        # Manual weights (only shown if auto-extract is disabled)
        self.harmonic_weight_spin = QDoubleSpinBox()
        self.harmonic_weight_spin.setRange(0.0, 1.0)
        self.harmonic_weight_spin.setValue(0.95)
        self.harmonic_weight_spin.setSingleStep(0.01)
        self.harmonic_weight_spin.setDecimals(2)
        self.harmonic_weight_spin.setEnabled(False)  # Disabled by default (auto-extract enabled)
        harmonic_layout.addRow("Harmonic Weight (α) [Manual]:", self.harmonic_weight_spin)
        
        self.inharmonic_weight_spin = QDoubleSpinBox()
        self.inharmonic_weight_spin.setRange(0.0, 1.0)
        self.inharmonic_weight_spin.setValue(0.05)
        self.inharmonic_weight_spin.setSingleStep(0.01)
        self.inharmonic_weight_spin.setDecimals(2)
        self.inharmonic_weight_spin.setEnabled(False)  # Disabled by default
        harmonic_layout.addRow("Inharmonic Weight (β) [Manual]:", self.inharmonic_weight_spin)
        
        # Connect auto-extract checkbox to enable/disable manual weights
        self.auto_extract_weights_check.toggled.connect(self.on_auto_extract_changed)
        
        # Auto-sync weights (only when manual mode)
        self.harmonic_weight_spin.valueChanged.connect(self.sync_weights)
        self.inharmonic_weight_spin.valueChanged.connect(self.sync_weights)
        
        # Adaptive tolerance
        self.adaptive_tolerance_check = QCheckBox("Use Adaptive Tolerance")
        self.adaptive_tolerance_check.setChecked(True)
        self.adaptive_tolerance_check.setToolTip("Use psychoacoustic JND-based adaptive tolerance (1.5% of frequency)")
        harmonic_layout.addRow("Adaptive Tolerance:", self.adaptive_tolerance_check)
        
        harmonic_group.setLayout(harmonic_layout)
        scroll_layout.addWidget(harmonic_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.tabs.addTab(params_tab, "Parameters")
    
    def on_auto_extract_changed(self, checked: bool):
        """Enable/disable manual weight inputs based on auto-extract checkbox."""
        self.harmonic_weight_spin.setEnabled(not checked)
        self.inharmonic_weight_spin.setEnabled(not checked)
        if checked:
            self.harmonic_weight_spin.setToolTip("Disabled: Weights will be auto-extracted from energy distribution")
            self.inharmonic_weight_spin.setToolTip("Disabled: Weights will be auto-extracted from energy distribution")
        else:
            self.harmonic_weight_spin.setToolTip("Manual harmonic weight (0.0-1.0)")
            self.inharmonic_weight_spin.setToolTip("Manual inharmonic weight (0.0-1.0)")
    
    def sync_weights(self):
        """Sync harmonic and inharmonic weights to sum to 1.0."""
        if not self.auto_extract_weights_check.isChecked():
            harmonic = self.harmonic_weight_spin.value()
            inharmonic = self.inharmonic_weight_spin.value()
            total = harmonic + inharmonic
            
            if total > 1.0:
                self.harmonic_weight_spin.blockSignals(True)
                self.inharmonic_weight_spin.blockSignals(True)
                self.harmonic_weight_spin.setValue(harmonic / total)
                self.inharmonic_weight_spin.setValue(inharmonic / total)
                self.harmonic_weight_spin.blockSignals(False)
                self.inharmonic_weight_spin.blockSignals(False)
    
    def setup_analysis_tab(self):
        """Setup analysis execution tab."""
        analysis_tab = QWidget()
        layout = QVBoxLayout()
        analysis_tab.setLayout(layout)
        
        # Run button
        self.run_analysis_btn = QPushButton("Run Super Analysis")
        self.run_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(34, 139, 34);
                font-size: 16px;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: rgb(50, 205, 50);
            }
        """)
        self.run_analysis_btn.clicked.connect(self.run_analysis)
        layout.addWidget(self.run_analysis_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: rgb(70, 130, 180);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to analyze")
        self.status_label.setStyleSheet("padding: 10px; font-size: 12px; background-color: white; border: 1px solid gray; border-radius: 3px;")
        layout.addWidget(self.status_label)
        
        # Results preview
        results_preview_group = QGroupBox("Analysis Results Preview")
        results_preview_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 9))
        results_preview_layout.addWidget(self.results_text)
        
        results_preview_group.setLayout(results_preview_layout)
        layout.addWidget(results_preview_group)
        
        layout.addStretch()
        self.tabs.addTab(analysis_tab, "Analysis")
    
    def setup_results_tab(self):
        """Setup results display tab."""
        results_tab = QWidget()
        layout = QVBoxLayout()
        results_tab.setLayout(layout)
        
        # Results text area
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setFont(QFont("Courier", 9))
        layout.addWidget(self.results_display)
        
        # Export button
        export_btn = QPushButton("Export Results to File...")
        export_btn.clicked.connect(self.export_results)
        layout.addWidget(export_btn)
        
        self.tabs.addTab(results_tab, "Results")
    
    def setup_visualization_tab(self):
        """Setup visualization tab."""
        viz_tab = QWidget()
        layout = QVBoxLayout()
        viz_tab.setLayout(layout)
        
        if MATPLOTLIB_AVAILABLE:
            # Matplotlib canvas for embedded plots
            self.figure = Figure(figsize=(14, 10))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            # Refresh button
            refresh_btn = QPushButton("Refresh Visualizations")
            refresh_btn.clicked.connect(self.refresh_visualizations)
            layout.addWidget(refresh_btn)
        else:
            no_viz_label = QLabel("Matplotlib not available. Visualizations will be saved to files.")
            no_viz_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_viz_label)
        
        self.tabs.addTab(viz_tab, "Visualizations")
    
    def browse_audio_file(self):
        """Browse for audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.aif *.aiff);;All Files (*.*)"
        )
        
        if file_path:
            self.audio_file_path = Path(file_path)
            # Detect stereo/mono immediately
            try:
                import soundfile as sf
                info = sf.info(str(self.audio_file_path))
                channels = info.channels
                is_stereo = (channels == 2)
                format_info = f"STEREO ({channels} channels)" if is_stereo else f"MONO ({channels} channel)"
                self.audio_file_label.setText(
                    f"Selected: {self.audio_file_path.name}\n"
                    f"Path: {self.audio_file_path}\n"
                    f"Format: {format_info}"
                )
                self.statusBar().showMessage(
                    f"Audio file selected: {self.audio_file_path.name} - {format_info}"
                )
            except Exception as e:
                # Fallback if detection fails
                self.audio_file_label.setText(
                    f"Selected: {self.audio_file_path.name}\n"
                    f"Path: {self.audio_file_path}\n"
                    f"Format: Detection failed ({str(e)[:50]})"
                )
                self.statusBar().showMessage(f"Audio file selected: {self.audio_file_path.name}")
    
    def browse_output_directory(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_dir_label.setText(f"Output: {self.output_dir}")
            self.statusBar().showMessage(f"Output directory: {self.output_dir}")
    
    def run_analysis(self):
        """Run the super analysis (single file)."""
        # Validate inputs
        if not self.audio_file_path or not self.audio_file_path.exists():
            QMessageBox.warning(
                self, 
                "Error - Single File Analysis", 
                "Please select a valid audio file.\n\n"
                "This button is for SINGLE file analysis.\n\n"
                "For multiple files (batch processing):\n"
                "1. Go to the 'Batch Processing' tab\n"
                "2. Click 'Select Multiple Audio Files...'\n"
                "3. Choose your files\n"
                "4. Click 'Run Batch Analysis'"
            )
            return
        
        if not self.output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return
        
        # Disable run button
        self.run_analysis_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")
        
        # Prepare analyzer parameters
        analyzer_params = {
            'audio_path': str(self.audio_file_path),
            'output_dir': str(self.output_dir),
            'sample_rate': self.sample_rate_spin.value(),
            'use_90_tier': self.use_90_tier_check.isChecked(),
            'harmonic_tolerance': self.harmonic_tolerance_spin.value(),
            'harmonic_weight': self.harmonic_weight_spin.value() if not self.auto_extract_weights_check.isChecked() else 0.95,  # Ignored if auto-extract
            'inharmonic_weight': self.inharmonic_weight_spin.value() if not self.auto_extract_weights_check.isChecked() else 0.05,  # Ignored if auto-extract
            'window': self.window_combo.currentText(),
            'use_adaptive_tolerance': self.adaptive_tolerance_check.isChecked(),
            'auto_extract_weights': self.auto_extract_weights_check.isChecked()  # New parameter
        }
        
        # Create and start worker thread
        self.worker = SuperAnalysisWorker(analyzer_params)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()
    
    @pyqtSlot(dict)
    def on_analysis_complete(self, results: Dict[str, Any]):
        """Handle analysis completion."""
        self.analysis_results = results
        self.run_analysis_btn.setEnabled(True)
        self.statusBar().showMessage("Super analysis complete!")
        
        # Update results display
        self.display_results(results)
        
        # Update visualizations
        if MATPLOTLIB_AVAILABLE:
            self.refresh_visualizations()
        
        # Show completion message
        QMessageBox.information(
            self,
            "Super Analysis Complete",
            f"Super analysis completed successfully!\n\nResults saved to:\n{self.output_dir}\n\n"
            f"Files generated:\n"
            f"• super_analysis_results.json\n"
            f"• final_batch_summary.png\n"
            f"• diagnostic_report.png\n"
            f"• harmonic_components.csv\n"
            f"• inharmonic_components.csv\n"
            f"• complete_spectrum.csv\n"
            f"• metrics_summary.txt"
        )
    
    @pyqtSlot(str)
    def on_analysis_error(self, error_msg: str):
        """Handle analysis error."""
        self.run_analysis_btn.setEnabled(True)
        self.statusBar().showMessage("Super analysis failed!")
        
        QMessageBox.critical(self, "Super Analysis Error", error_msg)
        self.results_text.setText(f"ERROR:\n\n{error_msg}")
    
    def display_results(self, results: Dict[str, Any]):
        """Display analysis results in text format."""
        text = "="*80 + "\n"
        text += "SUPER AUDIO ANALYZER - RESULTS\n"
        text += "="*80 + "\n\n"
        
        # Metadata
        if 'metadata' in results:
            text += "METADATA\n"
            text += "-"*80 + "\n"
            for key, value in results['metadata'].items():
                text += f"{key:30s}: {value}\n"
            text += "\n"
        
        # Frequency analysis
        if 'frequency_analysis' in results:
            text += "FREQUENCY ANALYSIS\n"
            text += "-"*80 + "\n"
            freq_analysis = results['frequency_analysis']
            if 'fundamental_freq_hz' in freq_analysis:
                text += f"Fundamental Frequency: {freq_analysis['fundamental_freq_hz']:.2f} Hz\n"
            if 'security_margin_percent' in freq_analysis:
                text += f"Security Margin: {freq_analysis['security_margin_percent']:.1f}%\n"
            text += "\n"
        
        # Harmonic analysis
        if 'harmonic_analysis' in results:
            text += "HARMONIC ANALYSIS\n"
            text += "-"*80 + "\n"
            harm_analysis = results['harmonic_analysis']
            text += (
                "Harmonic classified spectral rows (bins/candidates, not partial counts): "
                f"{harm_analysis.get('n_components', 0)}\n"
            )
            if 'frequencies_hz' in harm_analysis and harm_analysis['frequencies_hz']:
                text += f"First 5 Harmonic Frequencies: {harm_analysis['frequencies_hz'][:5]}\n"
            text += "\n"
        
        # Inharmonic analysis
        if 'inharmonic_analysis' in results:
            text += "INHARMONIC ANALYSIS\n"
            text += "-"*80 + "\n"
            inharm_analysis = results['inharmonic_analysis']
            text += (
                "Inharmonic classified spectral rows (bins/candidates, not partial counts): "
                f"{inharm_analysis.get('n_components', 0)}\n"
            )
            text += "\n"
        
        # Spectral metrics
        if 'spectral_metrics' in results:
            text += "SPECTRAL METRICS\n"
            text += "-"*80 + "\n"
            metrics = results['spectral_metrics']
            for key, value in metrics.items():
                if isinstance(value, float):
                    text += f"{key:30s}: {value:.6f}\n"
                else:
                    text += f"{key:30s}: {value}\n"
            text += (
                "\nEnergy: harmonic_energy_percentage / inharmonic_energy_percentage are "
                "bin-based and used for exported batch metrics. "
                "harmonic_energy_percentage_peak_based / "
                "inharmonic_energy_percentage_peak_based are peak-based validation only "
                "unless explicitly configured otherwise.\n"
            )
            text += (
                "Density: harmonic_density / inharmonic_density / combined_density are "
                "legacy batch diagnostic scalars. The final public density/fatness "
                "descriptor is effective_partial_density in the compiled Density_Metrics "
                "workbook.\n\n"
            )
        
        # Dissonance metrics
        if 'dissonance_analysis' in results:
            text += "DISSONANCE METRICS\n"
            text += "-"*80 + "\n"
            dissonance = results['dissonance_analysis']
            for key, value in dissonance.items():
                if isinstance(value, float):
                    text += f"{key:30s}: {value:.6f}\n"
                else:
                    text += f"{key:30s}: {value}\n"
            text += "\n"
        
        # Statistical analysis
        if 'statistical_analysis' in results:
            text += "STATISTICAL ANALYSIS\n"
            text += "-"*80 + "\n"
            stats = results['statistical_analysis']
            for key, value in stats.items():
                if isinstance(value, dict):
                    text += f"\n{key}:\n"
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict):
                            text += f"  {subkey}:\n"
                            for k, v in subvalue.items():
                                if isinstance(v, float):
                                    text += f"    {k:20s}: {v:.6f}\n"
                                else:
                                    text += f"    {k:20s}: {v}\n"
                        elif isinstance(subvalue, float):
                            text += f"  {subkey:20s}: {subvalue:.6f}\n"
                        else:
                            text += f"  {subkey:20s}: {subvalue}\n"
            text += "\n"
        
        # Internal consistency checks (legacy key physical_validation ignored in display)
        icc = results.get("internal_consistency_checks")
        if icc:
            text += "INTERNAL CONSISTENCY CHECKS\n"
            text += "-" * 80 + "\n"
            text += f"Enabled: {icc.get('internal_consistency_enabled', False)}\n"
            text += f"Method: {icc.get('execution_method', 'n/a')}\n"
            for name, block in icc.get("results", {}).items():
                if isinstance(block, dict):
                    msg = block.get("consistency_check_message", "")
                    st = block.get("status", "")
                    text += f"  {name}: {st} — {msg[:120]}{'...' if len(str(msg)) > 120 else ''}\n"
            text += "\n"
        
        self.results_display.setText(text)
        self.results_text.setText(text)
    
    def refresh_visualizations(self):
        """Refresh visualization plots."""
        if not MATPLOTLIB_AVAILABLE or not self.analysis_results:
            return
        
        self.figure.clear()
        
        # Create subplots
        ax1 = self.figure.add_subplot(2, 3, 1)
        ax2 = self.figure.add_subplot(2, 3, 2)
        ax3 = self.figure.add_subplot(2, 3, 3)
        ax4 = self.figure.add_subplot(2, 3, 4)
        ax5 = self.figure.add_subplot(2, 3, 5)
        ax6 = self.figure.add_subplot(2, 3, 6)
        
        # Plot 1: Final batch summary text (canonical power-mass %)
        ax1.axis("off")
        if 'spectral_metrics' in self.analysis_results:
            metrics = self.analysis_results['spectral_metrics']
            lines = ["Final batch (linear power %)"]
            h_e = metrics.get("harmonic_power_percent", metrics.get("harmonic_energy_percentage"))
            i_e = metrics.get("inharmonic_residual_power_percent", metrics.get("inharmonic_energy_percentage"))
            if h_e is not None and i_e is not None:
                lines.append(f"  Harmonic: {float(h_e):.1f}%")
                lines.append(f"  Inharmonic residual (bins): {float(i_e):.1f}%")
            sb = metrics.get("subbass_noise_power_percent", metrics.get("subbass_energy_percentage_global"))
            ti = metrics.get("total_inharmonic_power_percent", metrics.get("total_inharm_energy_percentage_global"))
            if sb is not None:
                lines.append(f"  Subbass noise: {float(sb):.2f}%")
            if ti is not None:
                lines.append(f"  Total inharmonic (I+S): {float(ti):.1f}%")
            lines.append("")
            lines.append("Other scalars: see text results.")
            ax1.text(0.5, 0.5, "\n".join(lines), ha="center", va="center", fontsize=9, transform=ax1.transAxes)
            ax1.set_title("Batch summary", fontsize=9)
        else:
            ax1.text(0.5, 0.5, "No spectral metrics", ha="center", va="center", fontsize=9, transform=ax1.transAxes)
            ax1.set_title("Batch summary", fontsize=9)
        
        # Plot 2: Frequency detection methods
        if 'frequency_analysis' in self.analysis_results:
            freq_analysis = self.analysis_results['frequency_analysis']
            if 'detection_methods' in freq_analysis:
                methods = freq_analysis['detection_methods']
                method_names = []
                method_values = []
                for name, value in methods.items():
                    if value is not None:
                        extracted = None
                        if isinstance(value, dict):
                            extracted = value.get('f0', None)
                        elif isinstance(value, (int, float)):
                            extracted = float(value)
                        if extracted is not None:
                            method_names.append(name)
                            method_values.append(extracted)
                
                if method_names and method_values and len(method_names) == len(method_values):
                    disp = [_format_detection_method_label(n) for n in method_names]
                    x2 = list(range(len(disp)))
                    ax2.bar(x2, method_values, color='orange', alpha=0.7)
                    ax2.set_xticks(x2)
                    ax2.set_xticklabels(disp, rotation=45, ha='right', fontsize=7)
                    ax2.set_ylabel('Frequency (Hz)')
                    f_hz = freq_analysis.get('fundamental_freq_hz')
                    oct_note = ""
                    if freq_analysis.get('octave_correction_validation'):
                        oct_note = "\n(octave correction applied)"
                    if f_hz is not None:
                        ax2.axhline(
                            float(f_hz),
                            color='green',
                            linestyle='--',
                            linewidth=2,
                            label='final_f0_octave_corrected',
                        )
                        ax2.legend(fontsize=7, loc='best')
                    f0_line = (
                        f"Selected f0: {float(f_hz):.2f} Hz" if f_hz is not None else "Selected f0: N/A"
                    )
                    ax2.set_title(
                        f"Detector candidates (Hz){oct_note}\n{f0_line}",
                        fontsize=9,
                        fontweight='bold',
                    )
        
        # Plot 3: Three-class final batch pie (global H + I + S), when available
        if 'spectral_metrics' in self.analysis_results:
            metrics = self.analysis_results['spectral_metrics']
            if all(
                k in metrics
                for k in (
                    "harmonic_power_percent",
                    "inharmonic_residual_power_percent",
                    "subbass_noise_power_percent",
                )
            ):
                hp = float(metrics["harmonic_power_percent"])
                ip = float(metrics["inharmonic_residual_power_percent"])
                sp = float(metrics["subbass_noise_power_percent"])
                values = [hp, ip, sp]
                labels = ["Harmonic %", "Inharmonic residual %", "Subbass noise %"]
                colors = ["#2E6F9E", "#C44E52", "#8B6FAD"]
                if sum(values) > 0:
                    ax3.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
                    ax3.set_title("Final batch (global %)\nGUI preview", fontsize=9, fontweight="bold")
            elif "harmonic_energy_percentage" in metrics and "inharmonic_energy_percentage" in metrics:
                harm_energy_pct = metrics["harmonic_energy_percentage"]
                inharm_energy_pct = metrics["inharmonic_energy_percentage"]
                if harm_energy_pct >= 50.0:
                    values = [harm_energy_pct, inharm_energy_pct]
                    labels = ["Harmonic %", "Inharmonic %"]
                    colors = ["blue", "red"]
                else:
                    values = [harm_energy_pct, inharm_energy_pct]
                    labels = [
                        f"Harmonic ({harm_energy_pct:.1f}% !)",
                        f"Inharmonic ({inharm_energy_pct:.1f}%)",
                    ]
                    colors = ["red", "orange"]
                if sum(values) > 0:
                    ax3.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
                    ax3.set_title("Musical-band H vs I (legacy)", fontsize=9, fontweight="bold")
            else:
                # Fallback: Component count (less meaningful)
                n_harm = self.analysis_results.get('harmonic_analysis', {}).get('n_components', 0)
                n_inharm = self.analysis_results.get('inharmonic_analysis', {}).get('n_components', 0)
                if n_harm + n_inharm > 0:
                    ax3.pie(
                        [n_harm, n_inharm],
                        labels=['Harmonic rows (bins/candidates)', 'Inharmonic rows (bins/candidates)'],
                        autopct='%1.1f%%',
                        startangle=90,
                        colors=['blue', 'red'],
                    )
                    ax3.set_title(
                        'Harmonic vs inharmonic rows (count fallback)',
                        fontsize=9,
                        fontweight='bold',
                    )
        
        # Plot 4: Harmonic frequencies (if available)
        if 'harmonic_analysis' in self.analysis_results:
            harm_analysis = self.analysis_results['harmonic_analysis']
            if 'frequencies_hz' in harm_analysis and 'amplitudes' in harm_analysis:
                freqs = harm_analysis['frequencies_hz'][:20]  # First 20
                amps = harm_analysis['amplitudes'][:20]
                if freqs and amps:
                    ax4.stem(freqs, amps, basefmt=' ')
                    ax4.set_title(
                        'Harmonic components (first orders)',
                        fontsize=9,
                    )
                    ax4.set_xlabel('Frequency (Hz)')
                    ax4.set_ylabel('Amplitude')
        
        # Plot 5: Statistical summary
        if 'statistical_analysis' in self.analysis_results and 'harmonic_amplitudes' in self.analysis_results['statistical_analysis']:
            stats = self.analysis_results['statistical_analysis']['harmonic_amplitudes']
            stat_names = ['mean', 'std', 'min', 'median']
            stat_values = [float(stats.get(s, 0) or 0) for s in stat_names]
            ax5.bar(stat_names, stat_values, alpha=0.7, color='teal')
            ax5.set_title(
                f"Harmonic amplitude (linear)\nmax = {float(stats.get('max', 0) or 0):.4f} (not in bars)"
            )
            ax5.set_ylabel('Amplitude (linear)')
            ax5.tick_params(axis='x', rotation=45)
        
        # Plot 6: Dissonance (if available)
        if 'dissonance_analysis' in self.analysis_results:
            dissonance = self.analysis_results['dissonance_analysis']
            if dissonance:
                keys = list(dissonance.keys())
                values = [dissonance[k] for k in keys if isinstance(dissonance[k], (int, float))]
                if values:
                    ax6.bar(keys[:len(values)], values, alpha=0.7, color='purple')
                    ax6.set_title('Dissonance Metrics')
                    ax6.set_ylabel('Value')
                    ax6.tick_params(axis='x', rotation=45)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def export_results(self):
        """Export results to a text file."""
        if not self.analysis_results:
            QMessageBox.warning(self, "No Results", "No analysis results to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.results_display.toPlainText())
                QMessageBox.information(self, "Export Complete", f"Results exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{e}")


def main():
    """Main entry point for GUI application."""
    if not ANALYZER_AVAILABLE:
        QMessageBox.critical(
            None,
            "Import Error",
            "super_audio_analyzer.py not found.\n\n"
            "Please ensure super_audio_analyzer.py is in the same directory."
        )
        return 1
    
    app = QApplication(sys.argv)
    app.setApplicationName("Super Audio Analyzer")
    
    window = SuperAudioAnalyzerGUI()
    window.show()
    
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

