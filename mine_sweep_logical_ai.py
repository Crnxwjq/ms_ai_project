# mine_sweep_logical_ai.py
import random
from PyQt5.QtWidgets import QMessageBox 
from PyQt5.QtCore import QTimer

class MineSweeperLogicalAI:
    def __init__(self, game):
        self.game = game
        self.timer = QTimer()
        self.timer.timeout.connect(self.perform_ai_step)
        self.is_active = False
        self.probability_guess_on = False
        self.ai_stop_callback = None

        self.to_open = []
        self.to_flag = []

        self.danger_zone = set()  # 用于存储“危险区”格子

    def start_ai(self):
        self.is_active = True
        self.update_danger_zone()
        self.timer.start(100)  # 每 0.1 秒执行一次
    
    def stop_ai(self):
        self.is_active = False
        self.timer.stop()
        self.to_open = []
        self.to_flag = []
        self.danger_zone.clear()

    def perform_ai_step(self):
        if self.game.is_first_click:
            self.game.handle_left_click(random.randint(0, self.game.rows - 1), random.randint(0, self.game.cols - 1))
            self.update_danger_zone()
            return

        if self.game.game_over:
            self.stop_ai()
            return

        # **优先执行存储的操作**
        while self.to_flag:
            x, y = self.to_flag.pop(0)
            if not self.game.buttons[x][y].is_flag:
                self.game.handle_right_click(x, y)
                self.update_danger_zone()
                return  
            else:
                continue  

        while self.to_open:
            x, y = self.to_open.pop(0)
            if not self.game.buttons[x][y].is_revealed:
                self.game.handle_left_click(x, y)
                self.update_danger_zone()
                return  
            else:
                continue  

        # **如果执行存储的操作时全是重复的，则立即执行一次新的推理**
        self.infer_logic()

        # **如果 infer_logic 发现新的 to_open/to_flag，则立即执行一次 perform_ai_step**
        if self.to_open or self.to_flag:
            self.perform_ai_step()
        elif self.probability_guess_on:
            self.probability_guess()
        else:
            self.ai_stop_callback()
            QMessageBox.information(self.game, "AI Stop", "Could not find any completely safe cells!")

    def infer_logic(self):
        """推理逻辑，计算 to_open 和 to_flag，仅遍历危险区"""
        number_cells = list(self.danger_zone)  # 只遍历危险区中的数字格

        for (x, y) in number_cells:
            unopened, flagged = self.game.get_unopened_unflagged_neighbors(x, y)
            mines_num = self.game.buttons[x][y].number

            if len(unopened) == mines_num - flagged:
                self.to_flag.extend(unopened)
            if flagged == mines_num:
                self.to_open.extend(unopened)

        # **二格推理**
        for (x1, y1) in number_cells:
            U_A, flagged_A = self.game.get_unopened_unflagged_neighbors(x1, y1)
            num_A = self.game.buttons[x1][y1].number
            remaining_A = num_A - flagged_A

            for (x2, y2) in number_cells:
                if (x1, y1) == (x2, y2):
                    continue

                U_B, flagged_B = self.game.get_unopened_unflagged_neighbors(x2, y2)
                num_B = self.game.buttons[x2][y2].number
                remaining_B = num_B - flagged_B

                if U_A.issubset(U_B) and len(U_A) < len(U_B):
                    diff = list(U_B - U_A)
                    if remaining_A == remaining_B:
                        self.to_open.extend(diff)
                    elif remaining_B - remaining_A == len(diff):
                        self.to_flag.extend(diff)

                if U_B.issubset(U_A) and len(U_B) < len(U_A):
                    diff = list(U_A - U_B)
                    if remaining_B == remaining_A:
                        self.to_open.extend(diff)
                    elif remaining_A - remaining_B == len(diff):
                        self.to_flag.extend(diff)

        # **2-1 推理**
        for (x1, y1) in number_cells:
            for (x2, y2) in number_cells:
                if (x1, y1) == (x2, y2):
                    continue
                if abs(x1 - x2) > 1 or abs(y1 - y2) > 1:
                    continue

                num_A = self.game.buttons[x1][y1].number
                num_B = self.game.buttons[x2][y2].number

                U_A, flagged_A = self.game.get_unopened_unflagged_neighbors(x1, y1)
                U_B, flagged_B = self.game.get_unopened_unflagged_neighbors(x2, y2)

                remaining_A = num_A - flagged_A
                remaining_B = num_B - flagged_B

                common = U_A & U_B
                diff_A = list(U_A - U_B)
                diff_B = list(U_B - U_A)

                if len(common) == 2 and len(diff_A) == 1 and len(diff_B) == 1 and (remaining_A - remaining_B) == 1:
                    self.to_flag.extend(diff_A)
                    self.to_open.extend(diff_B)

    def update_danger_zone(self):
        """更新危险区：只包含未打开格子的邻居"""
        self.danger_zone.clear()
        for x in range(self.game.rows):
            for y in range(self.game.cols):
                if self.game.buttons[x][y].is_revealed and self.game.buttons[x][y].number > 0:
                    self.danger_zone.add((x, y))

    def probability_guess(self):
        """全局概率推测法：基于所有未开格子的多个数字格信息，选择概率最低的进行打开"""
        probability_map = {}  # 记录每个未开格的最小雷概率

        # **遍历所有未打开、未插旗的格子**
        for x in range(self.game.rows):
            for y in range(self.game.cols):
                button = self.game.buttons[x][y]
                if button.is_revealed or button.is_flag:
                    continue  # 只考虑未开且未插旗的格子

                surrounding_numbers = []  # 存放影响该格子的数字格

                # 找到所有影响该格子的数字格
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.game.rows and 0 <= ny < self.game.cols:
                            neighbor = self.game.buttons[nx][ny]
                            if neighbor.is_revealed and neighbor.number > 0:
                                surrounding_numbers.append((nx, ny))

                if not surrounding_numbers:
                    continue  # 该格子没有任何已知信息，跳过

                # 计算该格子的最坏概率
                min_prob = 1.0  # 初始设为最大概率
                for (nx, ny) in surrounding_numbers:
                    unopened, flagged = self.game.get_unopened_unflagged_neighbors(nx, ny)
                    remaining_mines = self.game.buttons[nx][ny].number - flagged
                    local_prob = remaining_mines / len(unopened) if unopened else 1.0  # 避免除零错误

                    # 取最大概率（保守策略）
                    min_prob = min(min_prob, local_prob)

                probability_map[(x, y)] = min_prob

        # **找到最小概率的格子**
        if probability_map:
            min_probability = min(probability_map.values())
            best_cells = [pos for pos, prob in probability_map.items() if prob == min_probability]

            # **随机选择一个最安全的格子进行打开**
            x, y = random.choice(best_cells)
            self.game.handle_left_click(x, y)

if __name__ == "__main__":
    print("这是扫雷的逻辑AI")