import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
from os import path


class MadrlEnv(gym.Env):

    def __init__(self):
        self.action_low = -0.5
        self.action_high = 1.5
        self.action_space = spaces.Box(low=self.action_low, high=self.action_high, shape=(1,))
        self.observation_space = spaces.Box(low=0, high=10000, shape=(12,))

        self.seed()

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, u):

        self.state = [i * 0.1 for i in range(12)]
        reward = 1
        return self._get_obs(), reward, False, {}

    def reset(self):
        self.state = [i * 0.1 for i in range(12)]
        return self._get_obs()

    def _get_obs(self):
        return np.array(self.state)


