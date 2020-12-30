import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
from os import path
import subprocess


class MadrlEnv(gym.Env):

    def __init__(self):
        self.action_low = -0.5
        self.action_high = 1.5
        self.action_space = spaces.Box(low=self.action_low, high=self.action_high, shape=(2,))
        self.observation_space = spaces.Box(low=0, high=10000, shape=(12,))

        self.seed()
        self.count = 0
        self.num_eths = 3
        self.init_rate = 20000000
        self.rates = [self.init_rate for _ in range(self.num_eths)]

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, u):  # u是action
        # print(self.count, u[1], type(u[1]))
        self.rates[self.count] *= u[0]
        ratio = u[0]
        if ratio >= 0:
            self.rates[self.count] *= (1 + ratio * 0.025)
        else:
            self.rates[self.count] /= (1 - ratio * 0.025)

        if self.count == 2:
            self.count = -1
            p = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_rate=' + "'" + str(
                self.rates[0]) + ' ' + str(self.rates[1]) + ' ' + str(self.rates[2]) + "'"))

        self.state = [i * 0.1 for i in range(12)]
        reward = 1
        self.count += 1
        return self._get_obs(), reward, False, {}

    def reset(self):
        # cwnd = 15
        # p1 = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_pacing=1'))
        # p2 = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_cwnd_control=1'))
        # p3 = subprocess.getoutput('echo %s | sudo -S %s' % (
        #     "hebo", 'sudo sysctl -w net.ipv4.tcp_cwnd=' + "'" + str(cwnd) + ' ' + str(cwnd) + ' ' + str(cwnd) + "'"))
        # p = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_rate=' + "'" + str(
        #     self.rates[0]) + ' ' + str(self.rates[1]) + ' ' + str(self.rates[2]) + "'"))
        return self._get_obs()

    def _get_obs(self):
        # p = subprocess.getoutput(
        #     'sysctl net.ipv4.tcp_inflight net.ipv4.tcp_queue net.ipv4.tcp_cwnd net.ipv4.tcp_rtt net.ipv4.tcp_rate net.ipv4.tcp_deliverd')
        # outs = p.split('\n')
        # self.state = []
        # for index, out in enumerate(outs):
        #     if index == 4:
        #         a = out.split(' ')[2].split('\t')
        #         b = [int(a[0]) / 1000000, int(a[1]) / 1000000, int(a[2]) / 1000000]
        #         self.state.extend(b)
        #         prs = [int(a[0]), int(a[1]), int(a[2])]
        #     else:
        #         a = out.split(' ')[2].split('\t')
        #         if index == 3:
        #             b = [int(a[0]) / 1000, int(a[1]) / 1000, int(a[2]) / 1000]
        #         else:
        #             b = [int(a[0]), int(a[1]), int(a[2])]
        #         for i in b:
        #             self.state.append(i)
        # return np.array(self.state)

        self.state = [i * 0.1 for i in range(12)]
        return np.array(self.state)


