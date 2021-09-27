"""
Copyright (c). All Rights Reserved.
<Reinforcement Learning and Control> (Year 2020)
Intelligent Driving Lab (iDLab), Tsinghua University

by Shengbo Eben Li & Haitong Ma

Description: Chapter 8: RL example for lane keeping problem in a curve road;
             Approximate dynamic programming with structured policy

Update Date: 2021-09-06, Haitong Ma: Rewrite code formats
"""
import dynamics
import numpy as np
import torch
import time
import os
from network import Actor, Critic
from config import DynamicsConfig
from datetime import datetime
from solver import Solver
from utils import step_relative
from plot import plot_comparison, plot_phase_plot
from config import GeneralConfig

def simulation(methods, log_dir, simu_dir):
    '''

    Args:
        methods: list, methods to simulate
        log_dir: str, name of log dir
        simu_dir: str, name of log dir

    Returns:

    '''
    config = GeneralConfig()
    S_DIM = config.STATE_DIM
    A_DIM = config.ACTION_DIM
    policy = Actor(S_DIM, A_DIM)
    value = Critic(S_DIM, A_DIM)
    config = DynamicsConfig()
    solver=Solver()
    load_dir = log_dir
    policy.load_parameters(load_dir)
    value.load_parameters(load_dir)
    statemodel_plt = dynamics.VehicleDynamics()
    plot_length = config.SIMULATION_STEPS

    # Open-loop reference
    x_init = config.x_init_s
    op_state, op_control = solver.openLoopMpcSolver(x_init, config.NP_TOTAL)
    np.savetxt(os.path.join(simu_dir, 'Open_loop_control.txt'), op_control)
    np.savetxt(os.path.join(simu_dir, 'Open_loop_state.txt'), op_state)

    for method in methods:
        cal_time = 0
        state = torch.tensor([x_init])
        state.requires_grad_(False)
        x_ref = statemodel_plt.reference_trajectory(state[:, -1])
        state_r = state.detach().clone()
        state_r[:, 0:4] = state_r[:, 0:4] - x_ref

        state_history = state.detach().numpy()
        control_history = []

        if methods != 'OP': print('\nCALCULATION TIME:')
        for i in range(plot_length):
            if method == 'ADP':
                time_start = time.time()
                u = policy.forward(state_r[:, 0:4])
                cal_time += time.time() - time_start
            elif method.startswith('MPC'):
                pred_steps = int(method.split('-')[1])
                x = state_r.tolist()[0]
                time_start = time.time()
                _, control = solver.mpcSolver(x, pred_steps)
                cal_time += time.time() - time_start
                u = np.array(control[0], dtype='float32').reshape(-1, config.ACTION_DIM)
                u = torch.from_numpy(u)
            else:
                u = np.array(op_control[i], dtype='float32').reshape(-1, config.ACTION_DIM)
                u = torch.from_numpy(u)

            state, state_r, _ =step_relative(statemodel_plt, state, u)
            state_history = np.append(state_history, state.detach().numpy(), axis=0)
            control_history = np.append(control_history, u.detach().numpy())



        if method == 'ADP':
            print(" ADP: {:.3f}".format(cal_time) + "s")
            np.savetxt(os.path.join(simu_dir, 'ADP_state.txt'), state_history)
            np.savetxt(os.path.join(simu_dir, 'ADP_control.txt'), control_history)
        elif method.startswith('MPC'):
            pred_steps = method.split('-')[1]
            state_fname, control_fname = 'MPC_' + pred_steps + '_state.txt', \
                                       'MPC_' + pred_steps + '_control.txt'
            print(" MPC {} steps: {:.3f}".format(pred_steps, cal_time) + "s")
            np.savetxt(os.path.join(simu_dir, state_fname), state_history)
            np.savetxt(os.path.join(simu_dir, control_fname), control_history)

        # else:
        #     np.savetxt(os.path.join(simu_dir, 'Open_loop_state.txt'), state_history)

    plot_comparison(simu_dir, methods)
    plot_phase_plot(['ADP', 'MPC-5', 'MPC-10', 'MPC-30'], log_dir, simu_dir, data='Phase plot')
    plot_phase_plot(['ADP', 'MPC-5', 'MPC-10', 'MPC-30'], log_dir, simu_dir, data='Lat position')
    plot_phase_plot(['ADP', 'MPC-5', 'MPC-10', 'MPC-30'], log_dir, simu_dir, data='Head angle')
    plot_phase_plot(['ADP', 'MPC-5', 'MPC-10', 'MPC-30'], log_dir, simu_dir, data='Control')


if __name__ == '__main__':
    log_dir = "Results/2021-0922-1139"
    METHODS = ['ADP', 'MPC-5', 'MPC-10', 'MPC-30', 'OP'] #
    simu_dir = log_dir + "-Simu"
    os.makedirs(simu_dir, exist_ok=True)
    simulation(METHODS, log_dir, simu_dir)
