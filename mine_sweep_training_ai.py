# mine_sweep_training_ai.py
from stable_baselines3 import PPO
import numpy as np
from PyQt5.QtCore import QTimer

class MineSweeperTrainingAI:
    def __init__(self, game, model_path = "minesweeper_ppo"):
        self.game = game
        self.model = PPO.load(model_path)
        self.is_active = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_step)
        self.ai_stop_callback = None

    def start_ai(self):
        self.is_active = True
        self.timer.start(100)

    def stop_ai(self):
        self.is_active = False
        self.timer.stop()

    def get_action(self):
        state = self.get_state()
        action, _states = self.model.predict(state)
        return action

    def get_state(self):
        # 获取实际游戏的行列数
        rows = self.game.rows
        cols = self.game.cols

        # 50x50的状态矩阵
        state = np.full((50, 50), -2, dtype=np.int8)  # 默认值 -2 表示未被揭示且未插旗的格子（边界）

        # 填充实际游戏的小地图
        for x in range(rows):
            for y in range(cols):
                button = self.game.buttons[x][y]

                if button.is_revealed:
                    state[x, y] = button.number  # 已揭示格子的数字
                elif button.is_flag:
                    state[x, y] = -1  # 插旗的格子

        return state

    def play_step(self):
        if self.game.game_over:
            self.stop_ai()
            return

        action = self.get_action()
        x, y, action_type = action

        # 确保AI不会尝试操作地图边界外的格子
        if x >= self.game.rows or y >= self.game.cols:
            return

        if action_type == 0:
            self.game.handle_left_click(x, y)  # 左键点击
        elif action_type == 1:
            self.game.handle_right_click(x, y)  # 右键插旗


if __name__ == "__main__":
    print("这是扫雷的强化学习训练AI")
