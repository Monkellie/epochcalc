import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QFileDialog, QGridLayout, QFrame, QDialog, QDialogButtonBox, QScrollArea, QComboBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImageReader, QIcon

# Global variables for image viewer
image_paths = []  # Store image paths
selected_images = set()  # Store selected image paths
image_cache = {}  # Cache to store preloaded images

# Limit the number of images to display at once
MAX_IMAGES_TO_DISPLAY = 50

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))  # Directory where the code is located

# Create a "themes" directory inside the current directory if it doesn't exist
themes_dir = os.path.join(SCRIPT_DIR, "themes")
if not os.path.exists(themes_dir):
    os.makedirs(themes_dir)

# Define folder names related to dataset
DATASET_FOLDER_NAMES = ['AI', 'Dataset', 'DATASETS']

class EpochCalculator(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the layout for epoch calculator
        self.layout = QVBoxLayout()

        # Labels and inputs for the epoch calculator
        self.images_label = QLabel("Number of Images:")
        self.images_entry = QLineEdit(self)

        self.repeats_label = QLabel("Repeats:")
        self.repeats_entry = QLineEdit(self)

        self.batch_label = QLabel("Batch Size:")
        self.batch_entry = QLineEdit(self)

        self.steps_label = QLabel("Target Steps:")
        self.steps_entry = QLineEdit(self)
        self.steps_entry.setText("2000")  # Set default steps to 2000

        self.result_label = QLabel("Optimal Epochs: ")

        self.layout.addWidget(self.images_label)
        self.layout.addWidget(self.images_entry)
        self.layout.addWidget(self.repeats_label)
        self.layout.addWidget(self.repeats_entry)
        self.layout.addWidget(self.batch_label)
        self.layout.addWidget(self.batch_entry)
        self.layout.addWidget(self.steps_label)
        self.layout.addWidget(self.steps_entry)
        self.layout.addWidget(self.result_label)

        self.setLayout(self.layout)

        # Connect input fields to dynamically update the result
        self.images_entry.textChanged.connect(self.calculate_epochs)
        self.repeats_entry.textChanged.connect(self.calculate_epochs)
        self.batch_entry.textChanged.connect(self.calculate_epochs)
        self.steps_entry.textChanged.connect(self.calculate_epochs)

    def calculate_epochs(self):
        try:
            images = int(self.images_entry.text()) if self.images_entry.text() else 0
            repeats = int(self.repeats_entry.text()) if self.repeats_entry.text() else 0
            batch = int(self.batch_entry.text()) if self.batch_entry.text() else 0
            steps = int(self.steps_entry.text()) if self.steps_entry.text() else 2000  # Default to 2000 steps

            if images > 0 and repeats > 0 and batch > 0:
                total_epochs = (steps * batch) / (images * repeats)
                self.result_label.setText(f"Optimal Epochs: {total_epochs:.2f}")
            else:
                self.result_label.setText("Enter valid positive integers.")
        except ValueError:
            self.result_label.setText("Invalid input. Enter integers only.")

    def update_image_count(self, image_count):
        """ Method to update the number of images entry. """
        self.images_entry.setText(str(image_count))


class ImageLoaderThread(QThread):
    # Signal to send the loaded image paths and a completion flag
    image_loaded_signal = pyqtSignal(list, bool)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        # Load the images in the background
        loaded_image_paths = [
            os.path.join(self.directory, f)
            for f in os.listdir(self.directory)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ]
        
        # Limit the number of images if necessary
        if len(loaded_image_paths) > MAX_IMAGES_TO_DISPLAY:
            loaded_image_paths = loaded_image_paths[:MAX_IMAGES_TO_DISPLAY]
            self.image_loaded_signal.emit(loaded_image_paths, False)
        else:
            self.image_loaded_signal.emit(loaded_image_paths, True)


class ImageViewer(QWidget):
    def __init__(self):
        super().__init__()

        # Window settings
        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 1024, 768)

        # Layout
        self.layout = QVBoxLayout()

        self.header = QHBoxLayout()
        self.browse_button = QPushButton("Select Directory")
        self.browse_button.clicked.connect(self.browse_directory)

        self.image_count_label = QLabel("Total Images Found: 0")

        self.header.addWidget(self.browse_button)
        self.header.addWidget(self.image_count_label)

        # Scrollable image grid layout
        self.image_frame = QFrame(self)
        self.grid_layout = QGridLayout(self.image_frame)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_frame)

        self.layout.addLayout(self.header)
        self.layout.addWidget(self.scroll_area)

        self.setLayout(self.layout)

        # Initialize the image paths
        self.image_paths = []

    def browse_directory(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory", SCRIPT_DIR)  # Use SCRIPT_DIR as the base
        if folder_path:
            self.load_images(folder_path)

    def load_images(self, directory):
        """ Load images and handle errors with valid directory check. """
        if not os.path.exists(directory):
            self.image_count_label.setText("Error: Directory does not exist.")
            return

        # Check if the directory contains any subdirectories that match dataset names
        matching_dirs = self.find_matching_dataset_dirs(directory)

        if matching_dirs:
            # If matching directories are found, show a dialog to select one
            self.show_directory_selector_dialog(matching_dirs)
        else:
            # If no matching directories, load images from the selected directory
            self.start_loading_images(directory)

    def find_matching_dataset_dirs(self, directory):
        """ Find directories matching the dataset names (AI, Dataset, DATASETS, etc.). """
        return [d for d in os.listdir(directory) 
                if os.path.isdir(os.path.join(directory, d)) and any(d.lower() == name.lower() for name in DATASET_FOLDER_NAMES)]

    def show_directory_selector_dialog(self, directories):
        """ Show a dialog to select one of the matching directories. """
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Dataset Folder")
        dialog_layout = QVBoxLayout()

        combo_box = QComboBox(dialog)
        combo_box.addItems(directories)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.on_directory_selected(combo_box.currentText()))
        button_box.rejected.connect(dialog.reject)

        dialog_layout.addWidget(combo_box)
        dialog_layout.addWidget(button_box)

        dialog.setLayout(dialog_layout)
        dialog.exec_()

    def on_directory_selected(self, selected_directory):
        """ Handle the directory selection from the dialog. """
        full_path = os.path.join(SCRIPT_DIR, selected_directory)
        self.start_loading_images(full_path)

    def start_loading_images(self, directory):
        """ Start loading images from the selected directory. """
        # Clear the previous images
        self.image_paths.clear()
        self.clear_image_layout()

        # Start the image loading in a separate thread
        self.loader_thread = ImageLoaderThread(directory)
        self.loader_thread.image_loaded_signal.connect(self.update_images)
        self.loader_thread.start()

    def update_images(self, image_paths, all_loaded):
        """ Update UI after loading images. """
        self.image_paths = image_paths
        if not all_loaded:
            self.image_count_label.setText(f"Too many images. Displaying {MAX_IMAGES_TO_DISPLAY} images.")
        else:
            self.image_count_label.setText(f"Total Images Found: {len(self.image_paths)}")

        # Update the image count in the EpochCalculator
        main_window.epoch_calculator.update_image_count(len(self.image_paths))

        # Display images
        self.display_images()

    def load_and_cache_image(self, img_path):
        """ Cache images to avoid reloading multiple times using QImageReader. """
        if img_path not in image_cache:
            try:
                reader = QImageReader(img_path)
                reader.setAutoTransform(True)
                image = reader.read()
                if image.isNull():
                    raise Exception("Failed to load image")

                # Force resize to 1920x1080 while maintaining aspect ratio
                scaled_image = image.scaled(1920, 1080, Qt.KeepAspectRatio)
                pixmap = QPixmap.fromImage(scaled_image)
                image_cache[img_path] = pixmap
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                return QPixmap()  # Return empty pixmap in case of error
        return image_cache[img_path]

    def display_images(self):
        """ Display images dynamically in a grid layout. """
        row, col = 0, 0
        for img_path in self.image_paths:
            pixmap = self.load_and_cache_image(img_path)
            if pixmap.isNull():
                continue  # Skip images that failed to load

            img_label = QLabel(self)
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.mousePressEvent = lambda event, path=img_path: self.view_full_image(path)

            self.grid_layout.addWidget(img_label, row, col)

            col += 1
            if col >= 5:  # 5 images per row
                col = 0
                row += 1

        self.image_frame.adjustSize()

    def clear_image_layout(self):
        """ Clear the previous images from the layout. """
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def view_full_image(self, img_path):
        """ View the full image in a new window. """
        img_label = QLabel()
        img_pixmap = QPixmap(img_path)
        img_label.setPixmap(img_pixmap)
        img_label.setAlignment(Qt.AlignCenter)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Full View - {os.path.basename(img_path)}")
        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(img_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        dialog_layout.addWidget(button_box)

        dialog.setLayout(dialog_layout)
        dialog.exec_()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Epoch Calculator with Image Viewer")
        self.setGeometry(100, 100, 1024, 768)

        # Set the icon for the window
        self.setWindowIcon(QIcon('F:/Tools/Epoch Calc/heart_icons/default.ico'))  # Add your icon path here

        # Set up the main layout
        self.layout = QVBoxLayout()

        # Create a tab widget to hold both image viewer and epoch calculator
        self.tabs = QTabWidget()

        # Add the Epoch Calculator tab
        self.epoch_calculator = EpochCalculator()
        self.tabs.addTab(self.epoch_calculator, "Epoch Calculator")

        # Add the Image Viewer tab
        self.image_viewer = ImageViewer()
        self.tabs.addTab(self.image_viewer, "Image Viewer")

        # Add the import theme button below
        self.import_theme_button = QPushButton("Import Custom Theme")
        self.import_theme_button.clicked.connect(self.import_theme)

        self.layout.addWidget(self.import_theme_button)
        self.layout.addWidget(self.tabs)

        # Set up the central widget and layout
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def import_theme(self):
        """ Import a custom CSS theme from file. """
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Theme", themes_dir, "CSS Files (*.css)")
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    custom_css = file.read()
                self.apply_custom_theme(custom_css)
            except Exception as e:
                print(f"Error importing theme: {e}")

    def apply_custom_theme(self, custom_css):
        """ Apply custom CSS theme. """
        self.setStyleSheet(custom_css)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
