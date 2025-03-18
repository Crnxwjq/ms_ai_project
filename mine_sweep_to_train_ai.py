#mine_sweep_to_train_ai.py
import time
import gymnasium as gym
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from tqdm import tqdm
import random
import os

class SimpleMineSweeper:
    def __init__(self, rows=None, cols=None, mines=None):
        # 随机生成地图尺寸和雷的数量
        self.rows = random.randint(10, 50) if rows is None else rows
        self.cols = random.randint(10, 50) if cols is None else cols
        self.mines = random.randint(int(self.rows * self.cols * 0.05), int(self.rows * self.cols * 0.2)) if mines is None else mines
        self.reset()

    def reset(self):
        self.board = np.zeros((self.rows, self.cols), dtype=np.int8)
        self.revealed = np.zeros((self.rows, self.cols), dtype=bool)
        self.flags = np.zeros((self.rows, self.cols), dtype=bool)
        self.game_over = False
        self.win = False

        # 在地图上随机放置雷
        mine_positions = random.sample(range(self.rows * self.cols), self.mines)
        for pos in mine_positions:
            x, y = divmod(pos, self.cols)
            self.board[x, y] = -1  # -1 表示雷

        # 为每个空格计算周围雷的数量
        for x in range(self.rows):
            for y in range(self.cols):
                if self.board[x, y] == -1:
                    continue
                count = sum(self.board[nx, ny] == -1 for nx, ny in self.get_neighbors(x, y))
                self.board[x, y] = count

        # 将地图放置到50x50的框架内，左上角为小地图位置
        self.full_board = np.full((50, 50), -2, dtype=np.int8)  # -2表示未揭示的格子
        self.full_board[:self.rows, :self.cols] = self.board

        # 生成“地图边界”
        self.boundary = np.zeros((50, 50), dtype=bool)
        self.boundary[:self.rows, :self.cols] = True  # 将小地图的范围标记为边界

    def get_neighbors(self, x, y):
        return [(x+dx, y+dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx, dy) != (0, 0) and 0 <= x+dx < self.rows and 0 <= y+dy < self.cols]

    def reveal(self, x, y):
        # 检查是否为非法格子（边界或已揭示）
        if not self.boundary[x, y] or self.revealed[x, y] or self.flags[x, y] or self.game_over:
            return False
        self.revealed[x, y] = True
        if self.board[x, y] == -1:
            self.game_over = True
        elif self.board[x, y] == 0:
            for nx, ny in self.get_neighbors(x, y):
                if not self.revealed[nx, ny]:
                    self.reveal(nx, ny)
        return True

    def flag(self, x, y):
        if not self.revealed[x, y]:
            self.flags[x, y] = not self.flags[x, y]

    def check_win(self):
        if self.game_over:
            return False
        return np.sum(self.revealed) == (self.rows * self.cols - self.mines)

    def is_boundary(self, x, y):
        return not self.boundary[x, y]  # 判断是否是地图外的格子

# 环境封装
class MineSweeperEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super().__init__()
        self.game = SimpleMineSweeper()
        self.observation_space = spaces.Box(low=-2, high=8,
                                            shape=(50, 50),
                                            dtype=np.int8)
        self.action_space = spaces.MultiDiscrete([50, 50, 2])  # 50x50的地图
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game.reset()
        return self.get_state(), {}

    def get_state(self):
        state = np.full((50, 50), -2, dtype=np.int8)
        for x in range(self.game.rows):
            for y in range(self.game.cols):
                if self.game.revealed[x, y]:
                    state[x, y] = self.game.board[x, y]
                elif self.game.flags[x, y]:
                    state[x, y] = -1
        return state

    def step(self, action):
        x, y, action_type = action
        reward = 0
        done = False

        # 检查是否操作了非法格子
        if self.game.is_boundary(x, y):
            reward = -50  # 处罚
            done = True
            return self.get_state(), reward, done, False, {}

        if self.game.revealed[x, y] or self.game.flags[x, y]:
            reward = -50
            done = True
            return self.get_state(), reward, done, False, {}

        if action_type == 0:  # 揭示
            if not self.game.reveal(x, y):
                reward = -50
                done = True
            else:
                reward = 1
        elif action_type == 1:  # 插旗
            self.game.flag(x, y)
            reward = 5 if self.game.board[x, y] == -1 else -10

        if self.game.check_win():
            reward = 50
            done = True

        return self.get_state(), reward, done, False, {}
    

# **多进程环境**
def make_env():
    return lambda: MineSweeperEnv()

# 修改计算平均每局步数和训练速度的逻辑
if __name__ == "__main__":
    num_envs = 20  # 训练时并行的环境数
    env = SubprocVecEnv([make_env() for _ in range(num_envs)])

    model_path = "minesweeper_ppo.zip"
    
    # 如果已有训练模型，加载继续训练
    if os.path.exists(model_path):
        print("加载已有模型继续训练...")
        model = PPO.load(model_path, env=env)
    else:
        print("创建新模型...")
        model = PPO("MlpPolicy", env, verbose=0)

    total_rounds = 1000
    timesteps_per_round = 1000

    print("开始训练扫雷 AI...")
    start_time = time.time()
    last_update_time = start_time
    completed_rounds = 0
    initial_timesteps = model.num_timesteps  # 记录初始训练步数
    pbar = tqdm(total=total_rounds, desc="训练进度", unit="局")

    while completed_rounds < total_rounds:
        # 训练一轮
        model.learn(total_timesteps=timesteps_per_round)
        
        # 更新当前步数
        new_timesteps = model.num_timesteps
        trained_steps = new_timesteps - initial_timesteps  # 计算实际训练步数
        initial_timesteps = new_timesteps  # 更新步数

        # 手动更新完成的局数
        completed_rounds += num_envs  # 记录完成的局数

        # 计算每局步数和训练速度
        current_time = time.time()
        if current_time - last_update_time >= 10:
            elapsed = current_time - start_time
            speed = trained_steps / elapsed  # 训练速度：步数 / 时间
            avg_steps = trained_steps / completed_rounds  # 平均每局步数
            pbar.set_postfix({'训练速度': f'{speed:.2f} 步/秒', '平均每局步数': f'{avg_steps:.2f}'})
            last_update_time = current_time

        pbar.update(num_envs)

    pbar.close()
    model.save(model_path)
    print("训练完成，模型已保存！")
