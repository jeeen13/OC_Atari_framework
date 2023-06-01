import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__))))) # noqa
from ocatari.core import OCAtari, PositionHistoryGymWrapper
import gymnasium as gym
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.logger import configure
from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback, EveryNTimesteps, BaseCallback, CallbackList, EvalCallback
from pathlib import Path
from typing import Callable
from ocatari.utils import parser
from rtpt import RTPT


class RtptCallback(BaseCallback):
    def __init__(self, exp_name, max_iter, verbose=0):
        super(RtptCallback, self).__init__(verbose)
        self.rtpt = RTPT(name_initials="QD",
            experiment_name=exp_name,
            max_iterations=max_iter)
        self.rtpt.start()
        
    def _on_step(self) -> bool:
        self.rtpt.step()
        return True


def linear_schedule(initial_value: float) -> Callable[[float], float]:
    def func(progress_remaining: float) -> float:
        return progress_remaining * initial_value
    return func


def make_env(game: str, rank: int, seed: int = 0) -> Callable:
    def _init() -> gym.Env:
        env = PositionHistoryGymWrapper(OCAtari(game, mode="revised", hud=False, obs_mode=None))
        env = Monitor(env)
        env.reset(seed=seed + rank)
        return env

    set_random_seed(seed)
    return _init




# TODO: doublecheck evaluation, atm eval always on env seed0
def main():
    parser.add_argument("-g", "--game", type=str, required=True,
                        help="game to train (e.g. 'Pong')")
    parser.add_argument("-s", "--seed", type=int, required=True,
                        help="seed")
    parser.add_argument("-c", "--cores", type=int, required=True,
                        help="number of envs used")
    opts = parser.parse_args()


    env_str = "ALE/" + opts.game +"-v5"
    exp_name = opts.game + "-s" + str(opts.seed)
    n_envs = opts.cores
    n_eval_envs = 4
    n_eval_episodes = 4
    eval_env_seed = (opts.seed + 42) * 2 #different seeds for eval
    training_timestamps = 20_000_000
    checkpoint_frequency = 1_000_000
    eval_frequency = 500_000
    rtpt_frequency = 100_000
    log_path = Path("baseline_logs", exp_name)
    ckpt_path = Path("baseline_checkpoints", exp_name)
    log_path.mkdir(parents=True, exist_ok=True)
    ckpt_path.mkdir(parents=True, exist_ok=True)

    # check if compatible gym env
    env = PositionHistoryGymWrapper(OCAtari(env_str, mode="revised", hud=False, obs_mode=None))
    check_env(env)
    del env
    eval_env = SubprocVecEnv([make_env(game=env_str, rank=i, seed=eval_env_seed) for i in range(n_eval_envs)], start_method="fork")

    rtpt_iters = training_timestamps // rtpt_frequency
    eval_callback = EvalCallback(
        eval_env,
        n_eval_episodes=n_eval_episodes,
        best_model_save_path=str(ckpt_path),
        log_path=str(ckpt_path),
        eval_freq=max(eval_frequency // n_envs, 1),
        deterministic=True,
        render=False)

    checkpoint_callback = CheckpointCallback(
        save_freq= max(checkpoint_frequency // n_envs, 1),
        save_path=str(ckpt_path),
        name_prefix="model",
        save_replay_buffer=True,
        save_vecnormalize=False,)
    
    rtpt_callback = RtptCallback(
        exp_name=exp_name,
        max_iter=rtpt_iters)

    n_callback = EveryNTimesteps(
        n_steps=rtpt_frequency,
        callback=rtpt_callback)

    cb_list = CallbackList([checkpoint_callback, eval_callback, n_callback])
    env = SubprocVecEnv([make_env(game=env_str, rank=i, seed=opts.seed) for i in range(n_envs)], start_method="fork")

   

    new_logger = configure(str(log_path), ["stdout", "tensorboard"])

    # atari hyperparameters from the ppo paper:
    # https://arxiv.org/abs/1707.06347
    adam_step_size = 0.00025
    clipping_eps = 0.1
    model = PPO(
        "MlpPolicy",
        n_steps=128,
        learning_rate=linear_schedule(adam_step_size),
        n_epochs=3,
        batch_size=32*8,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=linear_schedule(clipping_eps),
        vf_coef=1,
        ent_coef=0.001,
        env=env,
        verbose=1)
    #model = DQN.load("pong_baseline")
    #model.set_env(env)
    #model.load_replay_buffer("pong_baseline_rb")
    #print(model.policy)
    model.set_logger(new_logger)
    #model.learn(total_timesteps=8_000_000, reset_num_timesteps=False)
    model.learn(total_timesteps=training_timestamps, callback=cb_list)


if __name__ == '__main__':
    main()