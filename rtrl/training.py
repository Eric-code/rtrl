from copy import deepcopy
from dataclasses import dataclass

import pandas as pd
import numpy as np

import rtrl.sac
from pandas import DataFrame, Timestamp

from rtrl.testing import Test
from rtrl.util import pandas_dict, cached_property
from rtrl.wrappers import StatsWrapper
from rtrl.envs import GymEnv, RootEnv


@dataclass(eq=0)
class Training:
  Env: type = RootEnv  # GymEnv
  Test: type = Test
  Agent: type = rtrl.sac.Agent
  epochs: int = 2
  rounds: int = 2  # number of rounds per epoch
  steps: int = 2000  # number of steps per round
  stats_window: int = None  # default = steps, should be at least as long as a single episode
  seed: int = 0  # seed is currently not used
  num_agents: int = 3

  def __post_init__(self):
    self.epoch = 0
    with self.Env() as env:
      # print("Environment:", self.env)
      # noinspection PyArgumentList
      # self.agent = self.Agent(env.observation_space, env.action_space)
      self.agents = [self.Agent(env.observation_space, env.action_space) for _ in range(self.num_agents)]

  def run_epoch(self):
    stats = []
    with StatsWrapper(self.Env(seed_val=self.seed+self.epoch), window=self.stats_window or self.steps) as env:
      for rnd in range(self.rounds):
        print(f"=== epoch {self.epoch}/{self.epochs} ".ljust(20, '=') + f" round {rnd}/{self.rounds} ".ljust(50, '='))
        stats += self.run_round(env),
        print(stats[-1].add_prefix("  ").to_string(), '\n')

    self.epoch += 1
    return stats

  def run_round(self, env):
    t0 = pd.Timestamp.utcnow()
    stats_training = []

    # test runs in parallel to the training process
    # test = self.Test(
    #   Env=self.Env,
    #   actor=self.agent.model,
    #   steps=self.stats_window or self.steps,
    #   base_seed=self.seed+self.epochs
    # )

    for step in range(self.steps):
        for index in range(self.num_agents):
            action, training_stats = self.agents[index].act(*env.transition, train=True)
            stats_training += training_stats
            env.step(action)

    return pandas_dict(
      **env.stats(),
      round_time=Timestamp.utcnow() - t0,
      # **test.stats().add_suffix("_test"),  # this blocks until the tests have finished
      # round_time_total=Timestamp.utcnow() - t0,
      **DataFrame(stats_training).mean(skipna=True)
    )
