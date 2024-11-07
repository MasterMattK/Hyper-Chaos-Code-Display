from DolphinMemoryLib import Dolphin
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6 import QtGui
from PySide6.QtCore import *
import sys

class CodeItemWidget(QWidget):
    def __init__(self, code_name, time_called, duration, current_time):
        super().__init__()

        # Create main layout
        main_layout = QHBoxLayout(self)

        # Create a widget to contain the progress bar and label
        overlay_widget = QWidget()
        grid_layout = QGridLayout(overlay_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        grid_layout.setSpacing(0)

        # Create the progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                background-color: rgba(240, 240, 240, 100);
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                background-color: rgba(76, 175, 80, 200);
                width: 1px;
            }
        """)


        self.progress_bar.setRange(0, duration * 1000)
        self.progress_bar.setTextVisible(False)
        remaining_time = duration - (current_time - time_called)
        self.progress_bar.setValue(remaining_time * 1000)

        # Create the label to overlay on the progress bar
        self.name = QLabel(code_name)
        self.name.setAlignment(Qt.AlignCenter)  # Center the label
        self.name.setStyleSheet("background-color: rgba(255, 255, 255, 0); font-weight: bold; font-size: 16px; color: white")  # Make label background transparent

        # Add the progress bar and label to the grid layout
        grid_layout.addWidget(self.progress_bar, 0, 0)
        grid_layout.addWidget(self.name, 0, 0)  # Overlay label on the same grid cell

        # Create remaining time label
        self.remaining_time = QLabel(f"{remaining_time:.0f}")

        # Add overlay widget (with progress bar and label) and remaining time to the main layout
        main_layout.addWidget(overlay_widget)
        #main_layout.addWidget(self.remaining_time)

        # Optional: Adjust layout and widget styling
        main_layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(main_layout)

    def update(self, remaining_time):
        """ Update the progress bar value """
        self.progress_bar.setValue(remaining_time*1000)
        self.remaining_time.setText(f"{remaining_time:.0f}")


class ChaosModWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("background: transparent;")
        # Disable scrolling by hiding scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.active_codes = {} # Dictionary to store the active list items by code name

    def add_code_item(self, code_name, time_called, duration, current_time):
        if code_name in self.active_codes:
            # Update existing code item
            item_widget, _ = self.active_codes[code_name]
            
            remaining_time = duration - (current_time - time_called)
            item_widget.update(remaining_time)
        else:
            # Create the custom widget
            item_widget = CodeItemWidget(code_name, time_called, duration, current_time)

            # Create QListWidgetItem and set the custom widget
            list_item = QListWidgetItem(self)
            list_item.setSizeHint(item_widget.sizeHint())
            self.addItem(list_item)
            self.setItemWidget(list_item, item_widget)

            # Store the widget reference
            self.active_codes[code_name] = (item_widget, list_item)

        #self.adjust_size_to_contents()

    def update_code_item(self, code_name, time_called, duration, current_time):
        """ Update the remaining time of an existing code """
        if code_name in self.active_codes:
            remaining_time = duration - (current_time - time_called)
            item_widget, _ = self.active_codes[code_name]
            item_widget.update(remaining_time)

    def remove_code_item(self, code_name):
        if code_name in self.active_codes:
            item_widget, list_item = self.active_codes.pop(code_name)
            # Remove the item from the QListWidget
            row = self.row(list_item)
            self.takeItem(row)
            #self.adjust_size_to_contents()


    def adjust_size_to_contents(self):
        total_item_height = sum(self.sizeHintForRow(i) for i in range(self.count()))
        total_height = total_item_height + self.frameWidth() * 2

        width = self.sizeHintForColumn(0) + self.frameWidth() * 2

        self.setFixedHeight(total_height)
        self.setFixedWidth(width)
        self.parent().resize(self.sizeHint())  # Adjust the window size

    def mousePressEvent(self, event: QMouseEvent):
        # Ignore mouse press events to prevent selection
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Ignore mouse release events to prevent selection
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent):
        # Ignore mouse move events to prevent dragging
        event.ignore()

    def dragEnterEvent(self, event):
        # Ignore drag enter events to prevent dragging of items
        event.ignore()

    def dragMoveEvent(self, event):
        # Ignore drag move events to prevent dragging of items
        event.ignore()

    def dropEvent(self, event):
        # Ignore drop events to prevent dropping items
        event.ignore()


class CodeCheckerThread(QThread):
    update_code_signal = Signal(str, float, float, float)
    remove_code_signal = Signal(str)
    finished = Signal()

    def __init__(self, memory, code_container, code_list, current_time, code_count):
        super().__init__()
        self.memory = memory
        self.code_container = code_container
        self.code_list = code_list
        self.current_time = current_time
        self.code_count = code_count
        self.running = True

    def run(self):
        while self.running:
            for i in range(self.code_count):
                offset = i * MainWindow.CODE_SIZE
                is_active = (
                    self.memory.read_u8(self.code_list + offset + MainWindow.IS_ACTIVE_OFFSET) == 1
                )

                name = self.memory.read_string(self.code_list + offset + MainWindow.NAME_OFFSET)
                if is_active:
                    time_called = self.memory.read_f32(self.code_list + offset + MainWindow.TIME_CALLED_OFFSET)
                    duration = self.memory.read_f32(self.code_list + offset + MainWindow.DURATION_OFFSET)
                    current_time = self.memory.read_f32(self.current_time)
                    self.update_code_signal.emit(name, time_called, duration, current_time)
                else:
                    self.remove_code_signal.emit(name)

            self.msleep(50)  # To avoid hogging CPU resources

        self.finished.emit()

    def stop(self):
        self.running = False


class ToolBar(QWidget):
    close_button_clicked = Signal()
    minimize_button_clicked = Signal()
    maximize_button_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground)

        # Set the background color to gray
        self.setStyleSheet("background: #a3a29d; border-radius: 10px;")
        self.setMaximumHeight(35)

        style = self.style()

        # Create custom buttons for close, minimize, and maximize
        button_layout = QHBoxLayout()
        close_button = QPushButton()
        close_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        close_button.clicked.connect(lambda: self.close_button_clicked.emit())
        minimize_button = QPushButton()
        minimize_button.clicked.connect(lambda: self.minimize_button_clicked.emit())
        minimize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        maximize_button = QPushButton()
        maximize_button.clicked.connect(lambda: self.maximize_button_clicked.emit())
        maximize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))

        # Style buttons
        close_button.setStyleSheet("background: transparent; border: none;")
        minimize_button.setStyleSheet("background: transparent; border: none;")
        maximize_button.setStyleSheet("background: transparent; border: none;")

        spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        button_layout.addWidget(QLabel("SMS Chaos Code Display"))
        button_layout.addItem(spacer)
        button_layout.addWidget(minimize_button)
        button_layout.addWidget(maximize_button)
        button_layout.addWidget(close_button)

        self.setLayout(button_layout)


class Background(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("background: #cccbc8;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setBrush(QBrush(QColor(0, 0, 0, 100)))  # Semi-transparent color for the triangle
        painter.setPen(Qt.NoPen)

        # Draw the triangle in the bottom-right corner
        size = self.size()
        triangle_size = 20
        points = [
            QPoint(size.width() - triangle_size, size.height() - triangle_size),
            QPoint(size.width(), size.height() - triangle_size),
            QPoint(size.width() - triangle_size, size.height())
        ]
        painter.drawPolygon(points)


class MainWindow(QMainWindow):
    # codeContainer offsets
    CURRENT_CODE_COUNT_OFFSET = 0x0
    CODE_LIST_OFFSET = 0x4

    # Code size
    CODE_SIZE = 0x30

    # codeListOffsets
    CODE_ID_OFFSET = 0x0
    NAME_OFFSET = 0x1
    IS_ACTIVE_OFFSET = 0x1F
    RARITY_OFFSET = 0x20
    DURATION_OFFSET = 0x24
    TIME_CALLED_OFFSET = 0x28
    P_FUNC_OFFSET = 0x2C

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("SMS Chaos Code Display")

        self.setStyleSheet("""
            border: 0px;
            border-radius: 10px;
        """)

        status_label = QLabel()
        self.is_error = False

        self.memory = Dolphin()
        return_flag = self.memory.find_dolphin()
        if return_flag != Dolphin.ReturnFlags.SUCCESS:
            print("Unsuccessful in finding a dolphin instance! Returning...")
            status_label.setText("Could not find a dolphin instance! Restart this program once your game is running!")
            self.setCentralWidget(status_label)
            self.is_error = True
            return

        return_flag = self.memory.init_shared_memory("dolphin-emu."+str(self.memory.pid))
        if return_flag != Dolphin.ReturnFlags.SUCCESS:
            print("Unsuccessful in initializing shared memory! Returning...")
            status_label.setText("Could not find an SMS instance! Restart this program once your game is running!")
            self.setCentralWidget(status_label)
            self.is_error = True
            return
        
        self.chaos_ptrs = -1
        self.find_chaos_ptrs()

        if self.chaos_ptrs == -1:
            status_label.setText("The current game doesn't seem to be SMS Chaos! Restart this program once your game is running!")
            self.setCentralWidget(status_label)
            self.is_error = True
            return
        
        # read the vals from the struct
        self.code_container = self.memory.read_u32(self.chaos_ptrs + 4)
        self.current_time = self.memory.read_u32(self.chaos_ptrs + 8)

        # read the vals from the codeContainer
        self.current_code_count = self.memory.read_u32(self.code_container + self.CURRENT_CODE_COUNT_OFFSET)
        self.code_list = self.code_container + self.CODE_LIST_OFFSET

        # Set window to be transparent
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set the initial size of the window
        self.resize(300, 600)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.background_opacity_effect = QGraphicsOpacityEffect()
        self.toolbar_opacity_effect = QGraphicsOpacityEffect()
        self.background_opacity_effect.setOpacity(0.7)
        self.toolbar_opacity_effect.setOpacity(1)

        # Create animations for opacity change
        self.background_opacity_animation = QPropertyAnimation(self.background_opacity_effect, b"opacity")
        self.background_opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.background_opacity_animation.setDuration(500)  # 500ms duration
        self.toolbar_opacity_animation = QPropertyAnimation(self.toolbar_opacity_effect, b"opacity")
        self.toolbar_opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.toolbar_opacity_animation.setDuration(500)  # 500ms duration

        self.background_widget = Background(self)
        self.background_widget.setGraphicsEffect(self.background_opacity_effect)

        self.toolbar = ToolBar(self)
        self.toolbar.setGraphicsEffect(self.toolbar_opacity_effect)

        self.list_widget = ChaosModWidget(self)
        layout = QGridLayout()
        layout.addWidget(self.background_widget, 0, 0, 3, 1)
        layout.addWidget(self.toolbar, 0, 0)
        layout.addWidget(self.list_widget, 1, 0)
        container_widget = QWidget()
        container_widget.setLayout(layout)
        self.setCentralWidget(container_widget)

        self.toolbar.minimize_button_clicked.connect(self.showMinimized)
        self.toolbar.maximize_button_clicked.connect(self.showMaximized)

        # Enable mouse tracking to handle dragging
        enable_mouse_tracking(self)
        self._is_dragging = False
        self._drag_start_position = QPoint(0, 0)

        # Add a margin for detecting the resize area
        self._resize_margin = 10

        # For resizing
        self._is_resizing = False
        self._resize_start_position = QPoint(0, 0)
        self._resize_start_size = QSize(0, 0)

        # Initialize and start the worker thread
        self.thr = CodeCheckerThread(self.memory, self.code_container, self.code_list, self.current_time, self.current_code_count)
        self.thr.update_code_signal.connect(self.list_widget.add_code_item)
        self.thr.remove_code_signal.connect(self.list_widget.remove_code_item)
        self.toolbar.close_button_clicked.connect(self.thr.stop)
        self.thr.finished.connect(self.close)
        self.thr.start()

    # finds the address of the chaosPtrs struct which is initalized in the C++ code
    def find_chaos_ptrs(self):
        current_memory_address = self.memory.MEM_START
        while current_memory_address < self.memory.MEM_END:
            unique_string = self.memory.read_string_ptr(current_memory_address, 9)
            if unique_string == "CHAOS 1.0":
                print(f"Unique String: {unique_string}, Address: {hex(current_memory_address)}")
                self.chaos_ptrs = current_memory_address
                break
            current_memory_address += 4
        else:
            print("No address found!")

    def enterEvent(self, event: QEnterEvent):
        if not self.is_error:
            """When the mouse enters the window area."""
            self.background_opacity_animation.stop()
            self.background_opacity_animation.setStartValue(self.background_opacity_effect.opacity())
            self.background_opacity_animation.setEndValue(0.7)  # Opacity when mouse enters
            self.background_opacity_animation.start()
            self.toolbar_opacity_animation.stop()
            self.toolbar_opacity_animation.setStartValue(self.background_opacity_effect.opacity())
            self.toolbar_opacity_animation.setEndValue(1)  # Opacity when mouse leaves
            self.toolbar_opacity_animation.start()
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        if not self.is_error:
            """When the mouse leaves the window area."""
            self.background_opacity_animation.stop()
            self.background_opacity_animation.setStartValue(self.background_opacity_effect.opacity())
            self.background_opacity_animation.setEndValue(0.01)  # Opacity when mouse leaves
            self.background_opacity_animation.start()
            self.toolbar_opacity_animation.stop()
            self.toolbar_opacity_animation.setStartValue(self.background_opacity_effect.opacity())
            self.toolbar_opacity_animation.setEndValue(0)  # Opacity when mouse leaves
            self.toolbar_opacity_animation.start()
        return super().leaveEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        if self.is_error:
            return

        """Detect if we are starting to resize."""
        if event.button() == Qt.LeftButton:
            # Check if mouse is near the right or bottom edge for resizing
            if (event.position().x() >= self.background_widget.width() - self._resize_margin and 
                event.position().y() >= self.background_widget.height() - self._resize_margin):
                self._is_resizing = True
                self._resize_start_position = event.globalPosition().toPoint()
                self._resize_start_size = self.size()
            else:
                self._is_dragging = True
                self._drag_start_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_error:
            return

        size = self.size()
        triangle_size = 28
        if (event.position().x() >= size.width() - triangle_size and
            event.position().y() >= size.height() - triangle_size):
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.toolbar.rect().contains(event.position().toPoint()):
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)

        """Handle mouse movement for resizing or dragging."""
        if self._is_resizing:
            delta = event.globalPosition().toPoint() - self._resize_start_position
            new_size = self._resize_start_size + QSize(delta.x(), delta.y())
            self.resize(new_size.width(), new_size.height())
        elif self._is_dragging:
            delta = event.globalPosition().toPoint() - self._drag_start_position
            self._drag_start_position = event.globalPosition().toPoint()
            new_pos = self.pos() + delta
            self.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_error:
            return

        """End resizing or dragging."""
        if event.button() == Qt.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
            elif self._is_dragging:
                self._is_dragging = False


# for some reason in PySide6 you have to set mouse
# tracking on for every widget in the hierarchy
def enable_mouse_tracking(widget: QWidget):
    widget.setMouseTracking(True)
    for child in widget.findChildren(QWidget):
        enable_mouse_tracking(child)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())