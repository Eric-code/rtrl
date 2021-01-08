import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
from os import path
import subprocess
import time


class MadrlEnv(gym.Env):

    def __init__(self):
        self.action_low = -0.5
        self.action_high = 1.5
        self.action_space = spaces.Box(low=self.action_low, high=self.action_high, shape=(2,))
        self.observation_space = spaces.Box(low=0, high=10000, shape=(6,))

        self.seed()
        self.count = 0
        self.all_state = []
        self.step_num = 0
        self.num_eths = 3
        self.init_rate = 20000000
        self.rates = [self.init_rate for _ in range(self.num_eths)]
        self.ratios = [0 for _ in range(self.num_eths)]
        self.period = 1000  # 单位:毫秒
        self.last_trigger_times = 0
        self.max_rate = 1000000000
        self.min_rate = 20000000
        self.period_rtts_n = [[] for _ in range(self.num_eths)]
        self.rtt_n = [0 for _ in range(self.num_eths)]
        self.pre_mean_period_rtts_n = [0 for _ in range(self.num_eths)]
        self.pre_deliverd_n = [0 for _ in range(self.num_eths)]
        self.deliverd_gain_n = [0 for _ in range(self.num_eths)]
        self.reward_n = [0 for _ in range(self.num_eths)]
        self.action_rate_n = [0 for _ in range(self.num_eths)]
        self.action_ratio_n = [0 for _ in range(self.num_eths)]

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, u):  # u是action
        self.step_num += 1
        action_rate = u[0] - 0.5
        action_ratio = u[1]
        self.action_rate_n[self.count] = round(action_rate, 2)
        self.action_ratio_n[self.count] = round(action_ratio, 2)
        if action_rate >= 0:
            self.rates[self.count] *= (1 + action_rate * 0.025)
        else:
            self.rates[self.count] /= (1 - action_rate * 0.025)
        self.rates[self.count] = max(self.rates[self.count], self.min_rate)
        self.rates[self.count] = min(self.rates[self.count], self.max_rate)
        self.rates[self.count] = int(self.rates[self.count])
        p = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_rate=' + "'" + str(
            self.rates[0]) + ' ' + str(self.rates[1]) + ' ' + str(self.rates[2]) + "'"))

        # if action_ratio <= 0:
        #     action_ratio = 0
        # elif action_ratio >= 1:
        #     action_ratio = 1
        # self.ratios[self.count] = action_ratio
        # p = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_ratio=' + "'" + str(
        #     self.ratios[0]) + ' ' + str(self.ratios[1]) + ' ' + str(self.ratios[2]) + "'"))  # 施加动作

        while True:
            self.state = self._get_obs()
            self.period_rtts_n[0].append(self.state[9])
            self.period_rtts_n[1].append(self.state[10])
            self.period_rtts_n[2].append(self.state[11])
            current_time = time.time() * 1000  # get millisecond timestamp

            if current_time > self.last_trigger_times + self.period / self.num_eths:  # trigger cc
                self.last_trigger_times = current_time
                states_n = [self.state[0::3], self.state[1::3], self.state[2::3]]
                mean_period_rtt = round(self.mean(self.period_rtts_n[self.count]), 3)
                self.rtt_n[self.count] = mean_period_rtt
                deliverd = self.state[15 + self.count]
                deliver_gain = deliverd - self.pre_deliverd_n[self.count]
                if deliver_gain < 0:
                    deliver_gain = deliverd
                reward = deliver_gain * 0.001 - mean_period_rtt + 20

                self.reward_n[self.count] = round(reward, 2)
                self.deliverd_gain_n[self.count] = deliver_gain
                self.period_rtts_n[self.count].clear()
                self.pre_deliverd_n[self.count] = deliverd
                break

        if self.count == 2:
            self.count = -1
            print(self.step_num, "|rates:", self.rates, "|action:", self.action_rate_n, "|rtt:", self.rtt_n, "|reward:",
                  self.reward_n, "|deliver_gain:", self.deliverd_gain_n)
        self.count += 1
        obs = states_n[self.count]
        obs[3] = self.rtt_n[self.count]
        obs = np.array(obs)
        return obs, reward, False, {}

        # reward = 1
        # return self._get_obs(), reward, False, {}

    def reset(self):
        cwnd = 15
        p1 = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_pacing=1'))
        p2 = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_cwnd_control=1'))
        p3 = subprocess.getoutput('echo %s | sudo -S %s' % (
            "hebo", 'sudo sysctl -w net.ipv4.tcp_cwnd=' + "'" + str(cwnd) + ' ' + str(cwnd) + ' ' + str(cwnd) + "'"))
        p = subprocess.getoutput('echo %s | sudo -S %s' % ("hebo", 'sudo sysctl -w net.ipv4.tcp_rate=' + "'" + str(
            self.rates[0]) + ' ' + str(self.rates[1]) + ' ' + str(self.rates[2]) + "'"))
        self.state = self._get_obs()
        return np.array(self.state[0::3])

    def _get_obs(self):
        p = subprocess.getoutput(
            'sysctl net.ipv4.tcp_inflight net.ipv4.tcp_queue net.ipv4.tcp_cwnd net.ipv4.tcp_rtt net.ipv4.tcp_rate net.ipv4.tcp_deliverd')
        outs = p.split('\n')
        states = []
        for index, out in enumerate(outs):
            if index == 4:
                a = out.split(' ')[2].split('\t')
                b = [int(a[0]) / 1000000, int(a[1]) / 1000000, int(a[2]) / 1000000]
                states.extend(b)
                prs = [int(a[0]), int(a[1]), int(a[2])]
            else:
                a = out.split(' ')[2].split('\t')
                if index == 3:
                    b = [int(a[0]) / 1000, int(a[1]) / 1000, int(a[2]) / 1000]
                else:
                    b = [int(a[0]), int(a[1]), int(a[2])]
                for i in b:
                    states.append(i)
        return states

        # self.state = [i * 0.1 for i in range(6)]
        # return np.array(self.state)

    def mean(self, x):
        if len(x) == 0:
            return 0
        return sum(x) / len(x)


