# mine_sweep.py
import sys
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                             QVBoxLayout, QHBoxLayout, QPushButton, QSpinBox,
                             QLabel, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QTime
from mine_sweep_logical_ai import MineSweeperLogicalAI
from mine_sweep_training_ai import MineSweeperTrainingAI

class MineButton(QPushButton):
    leftClicked = pyqtSignal(int, int)
    rightClicked = pyqtSignal(int, int)
    middleClicked = pyqtSignal(int, int)

    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.is_revealed = False
        self.is_flag = False
        self.number = 0
        self.setFixedSize(30, 30)
        self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.leftClicked.emit(self.x, self.y)
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(self.x, self.y)
        
        # Check for middle click (both buttons pressed)
        if event.buttons() == (Qt.LeftButton | Qt.RightButton):
            self.middleClicked.emit(self.x, self.y)

    def set_revealed(self, number):
        self.is_revealed = True
        self.is_flag = False
        self.number = number
        self.setText(str(number) if number != 0 else "")
        self.update_style()

    def set_flag(self, flag):
        if not self.is_revealed:
            self.is_flag = flag
            self.setText("🚩" if flag else "")
            self.update_style()

    def update_style(self):
        if self.is_revealed:
            color_map = {
                1: "blue", 2: "green", 3: "red",
                4: "darkblue", 5: "brown", 6: "cyan",
                7: "black", 8: "gray"
            }
            color = color_map.get(self.number, "black")
            self.setStyleSheet(f"""
                background-color: white;
                color: {color};
                border: 1px solid #ccc;
            """)
        else:
            self.setStyleSheet("""
                background-color: #bbb;
                border: 1px solid #999;
            """)

class MineSweeperGame(QWidget):
    ai_stop_callback = None
    
    def __init__(self):
        super().__init__()
        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        self.setLayout(self.grid)
        
        self.rows = 0
        self.cols = 0
        self.mine_num = 0
        self.mines = []
        self.numbers = []
        self.buttons = []
        self.flags = []
        self.revealed = []
        self.is_first_click = True
        self.game_over = False

        # 计时器相关
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.elapsed_time = QTime(0, 0)  # 记录游戏时间
        self.time_elapsed_callback = None  # 用于更新 UI 的回调函数

        # 剩余雷数回调
        self.mine_count_callback = None 

    def start_new_game(self, rows, cols, mine_num):
        # Clear previous game
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Initialize game state
        self.rows = rows
        self.cols = cols
        self.mine_num = min(mine_num, rows*cols-1)
        self.is_first_click = True
        self.game_over = False
        
        # Initialize arrays
        self.mines = [[False for _ in range(cols)] for _ in range(rows)]
        self.numbers = [[0 for _ in range(cols)] for _ in range(rows)]
        self.flags = [[False for _ in range(cols)] for _ in range(rows)]
        self.revealed = [[False for _ in range(cols)] for _ in range(rows)]
        
        # Create buttons
        self.buttons = []
        for x in range(rows):
            row = []
            for y in range(cols):
                btn = MineButton(x, y)
                btn.leftClicked.connect(self.handle_left_click)
                btn.rightClicked.connect(self.handle_right_click)
                btn.middleClicked.connect(self.handle_middle_click)
                self.grid.addWidget(btn, x, y)
                row.append(btn)
            self.buttons.append(row)

        self.elapsed_time = QTime(0, 0)
        self.timer.stop()  # 重新开始游戏时停止计时
        if self.time_elapsed_callback:
            self.time_elapsed_callback(self.elapsed_time.toString("mm:ss"))
        self.update_mine_count()

    def generate_mines(self, safe_x, safe_y):
        # Generate safe area
        safe_area = set()
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                x = safe_x + dx
                y = safe_y + dy
                if 0 <= x < self.rows and 0 <= y < self.cols:
                    safe_area.add((x, y))
        
        # Create list of possible mine positions
        all_positions = [(x, y) for x in range(self.rows) for y in range(self.cols)]
        safe_positions = [pos for pos in all_positions if pos not in safe_area]
        
        # Determine mine placements
        mine_count = min(self.mine_num, len(all_positions)-len(safe_area))
        mine_positions = random.sample(safe_positions, mine_count)
        
        # If we still need more mines, add from safe area (excluding first click)
        if mine_count < self.mine_num:
            remaining = self.mine_num - mine_count
            extra_positions = [pos for pos in safe_area if pos != (safe_x, safe_y)]
            mine_positions += random.sample(extra_positions, min(remaining, len(extra_positions)))
        
        # Place mines
        for x, y in mine_positions:
            self.mines[x][y] = True
        
        # Calculate numbers
        for x in range(self.rows):
            for y in range(self.cols):
                count = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        ny = y + dy
                        if 0 <= nx < self.rows and 0 <= ny < self.cols:
                            if self.mines[nx][ny]:
                                count += 1
                self.numbers[x][y] = count

    def handle_left_click(self, x, y):
        if self.game_over or self.flags[x][y]:
            return
        
        if self.is_first_click:
            self.generate_mines(x, y)
            self.is_first_click = False
            self.timer.start(1000)
        
        if self.mines[x][y]:
            self.game_over = True
            self.timer.stop()
            self.reveal_all()
            self.game_end()
            QMessageBox.information(self, "Game Over", "You hit a mine!")
            self.buttons[x][y].setText("💀")
            return
        
        self.reveal(x, y)
        
        if self.check_win():
            self.game_over = True
            self.timer.stop()
            self.game_end()
            QMessageBox.information(self, "Congratulations!", "You win!")

    def handle_right_click(self, x, y):
        if self.game_over or self.revealed[x][y]:
            return
        
        self.flags[x][y] = not self.flags[x][y]
        self.buttons[x][y].set_flag(self.flags[x][y])
        self.update_mine_count()

    def handle_middle_click(self, x, y):
        if self.game_over or not self.revealed[x][y]:
            return
        
        flag_count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx = x + dx
                ny = y + dy
                if 0 <= nx < self.rows and 0 <= ny < self.cols:
                    if self.flags[nx][ny]:
                        flag_count += 1
        
        if flag_count == self.numbers[x][y]:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx < self.rows and 0 <= ny < self.cols:
                        if not self.revealed[nx][ny] and not self.flags[nx][ny]:
                            if self.mines[nx][ny]:
                                self.game_over = True
                                self.reveal_all()
                                QMessageBox.information(self, "Game Over", "You hit a mine!")
                                return
                            self.reveal(nx, ny)
        
        if self.check_win():
            self.game_over = True
            QMessageBox.information(self, "Congratulations!", "You win!")

    def reveal(self, x, y):
        if self.revealed[x][y] or self.flags[x][y]:
            return
        
        self.revealed[x][y] = True
        self.buttons[x][y].set_revealed(self.numbers[x][y])
        
        if self.numbers[x][y] == 0:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx < self.rows and 0 <= ny < self.cols:
                        if not self.revealed[nx][ny]:
                            self.reveal(nx, ny)

    def check_win(self):
        for x in range(self.rows):
            for y in range(self.cols):
                if (not self.mines[x][y] and not self.revealed[x][y]) or self.buttons[x][y].text() == "💣":
                    return False
        return True

    def reveal_all(self):
        for x in range(self.rows):
            for y in range(self.cols):
                if self.mines[x][y]:
                    self.buttons[x][y].setText("💣")
                    self.buttons[x][y].setStyleSheet("""
                        background-color: red;
                        color: black;
                    """)

    def update_time(self):
        self.elapsed_time = self.elapsed_time.addSecs(1)
        if self.time_elapsed_callback:
            self.time_elapsed_callback(self.elapsed_time.toString("mm:ss"))

    def update_mine_count(self):
        remaining_mines = self.mine_num - sum(row.count(True) for row in self.flags)
        if self.mine_count_callback:
            self.mine_count_callback(remaining_mines)

    def game_end(self):
        if self.ai_stop_callback:
            self.ai_stop_callback()

    def get_unopened_unflagged_neighbors(self, x, y):
        unopened_unflagged = set()
        flagged_count = 0

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.rows and 0 <= ny < self.cols:
                    neighbor = self.buttons[nx][ny]
                    if not neighbor.is_revealed:
                        if neighbor.is_flag:
                            flagged_count += 1
                        else:
                            unopened_unflagged.add((nx, ny))

        return unopened_unflagged, flagged_count
    
    def get_remaining_mines(self):
        return self.mine_num - sum(row.count(True) for row in self.flags)
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minesweeper")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 顶部显示区域（时间 + 剩余雷数）
        self.info_layout = QHBoxLayout()
        self.time_label = QLabel("Time: 00:00")
        self.mine_label = QLabel("Mines: 0")
        self.info_layout.addWidget(self.time_label)
        self.info_layout.addWidget(self.mine_label)

        layout.addLayout(self.info_layout)

        # Settings
        settings = QHBoxLayout()
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(10)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 50)
        self.cols_spin.setValue(10)
        self.mines_spin = QSpinBox()
        self.mines_spin.setRange(1, 2500)
        self.mines_spin.setValue(15)
        
        self.start_btn = QPushButton("New Game")
        self.start_btn.clicked.connect(self.new_game)

        settings.addWidget(QLabel("Rows:"))
        settings.addWidget(self.rows_spin)
        settings.addWidget(QLabel("Cols:"))
        settings.addWidget(self.cols_spin)
        settings.addWidget(QLabel("Mines:"))
        settings.addWidget(self.mines_spin)
        settings.addWidget(self.start_btn)

        layout.addLayout(settings)

        # AI Controller
        ai_controller = QHBoxLayout()
        self.logical_ai_btn = QPushButton("Logical AI") 
        self.logical_ai_btn.clicked.connect(self.toggle_logical_ai) 
        self.logical_ai_probability_guess_btn = QCheckBox("With Probability Guess", self)
        self.logical_ai_probability_guess_btn.clicked.connect(self.ai_probability_guess_clicked)

        self.training_ai_btn = QPushButton("Training AI")
        self.training_ai_btn.clicked.connect(self.toggle_training_ai)

        ai_controller.addWidget(self.logical_ai_btn)
        ai_controller.addWidget(self.logical_ai_probability_guess_btn)
        ai_controller.addWidget(self.training_ai_btn)
        layout.addLayout(ai_controller)

        

        # Game area
        self.game = MineSweeperGame()
        self.game.time_elapsed_callback = self.update_time_display
        self.game.mine_count_callback = self.update_mine_display
        self.game.ai_stop_callback = self.stop_ai_callback
        
        layout.addWidget(self.game)

        self.logical_ai = MineSweeperLogicalAI(self.game)
        self.logical_ai.ai_stop_callback = self.stop_logical_ai_callback
        self.training_ai = MineSweeperTrainingAI(self.game)
        self.training_ai.ai_stop_callback = self.stop_training_ai_callback        

        self.update_mine_max()
        self.rows_spin.valueChanged.connect(self.update_mine_max)
        self.cols_spin.valueChanged.connect(self.update_mine_max)
        
        self.new_game()
    
    def toggle_logical_ai(self):
        if self.logical_ai_btn.text() == "Logical AI":
            if self.training_ai_btn.text() == "Training AI":
                self.logical_ai.start_ai()
                self.logical_ai_btn.setText("Stop Logical AI")
                self.info_layout.addWidget(QLabel("AI Playing ..."))
        else:
            self.logical_ai.stop_ai()
            self.logical_ai_btn.setText("Logical AI")
            # 移除“AI操作中”的显示
            for i in range(self.info_layout.count()):
                widget = self.info_layout.itemAt(i).widget()
                if widget and widget.text() == "AI Playing ...":
                    self.info_layout.removeWidget(widget)
                    widget.deleteLater()
    
    def toggle_training_ai(self):
        if self.training_ai_btn.text() == "Training AI":
            if self.logical_ai_btn.text() == "Logical AI":
                self.training_ai.start_ai()
                self.training_ai_btn.setText("Stop Training AI")
                self.info_layout.addWidget(QLabel("AI Playing ..."))
        else:
            self.training_ai.stop_ai()
            self.training_ai_btn.setText("Training AI")
            # 移除“AI操作中”的显示
            for i in range(self.info_layout.count()):
                widget = self.info_layout.itemAt(i).widget()
                if widget and widget.text() == "AI Playing ...":
                    self.info_layout.removeWidget(widget)
                    widget.deleteLater()

    def stop_logical_ai_callback(self):
        self.toggle_logical_ai()
    
    def stop_training_ai_callback(self):
        self.toggle_training_ai()

    def stop_ai_callback(self):
        if self.logical_ai_btn.text() == "Logical AI":
            self.stop_logical_ai_callback()
        else:
            self.stop_training_ai_callback()

    def update_time_display(self, time_str):
        self.time_label.setText(f"Time: {time_str}")

    def update_mine_display(self, mine_count):
        self.mine_label.setText(f"Mines: {mine_count}")

    def new_game(self):
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        mines = self.mines_spin.value()
        self.game.start_new_game(rows, cols, mines)
        self.update_mine_display(mines)  # 重新开始游戏时更新雷数
        if self.logical_ai_btn.text() == "Stop Logical AI":
            self.toggle_logical_ai()
        if self.training_ai_btn.text() == "Stop Training AI":
            self.toggle_training_ai()
    def update_mine_max(self):
        max_mines = self.rows_spin.value() * self.cols_spin.value() - 1
        self.mines_spin.setMaximum(max_mines)

    def ai_probability_guess_clicked(self):
        check_box = self.sender()
        self.logical_ai.probability_guess_on = check_box.isChecked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    