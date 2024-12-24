
from model import Model
from algorithm import DQN  # from parl.algorithms import DQN  # parl >= 1.3.1
from agent import Agent
from env import Env
from agent import flag
from agent import flag_temp
from env import ContainerNumber
from env import NodeNumber

# LEARN_FREQ = 6  # learning frequency
# MEMORY_SIZE = 10000  # size of replay memory
# MEMORY_WARMUP_SIZE = 2000  
# BATCH_SIZE = 30 
LEARNING_RATE = 0.001
GAMMA = 0.9  

# sc_comm = 0
# sc_var = 0
# flag1 = 1
# ep = 0 
# allCost = [[],[],[],[],[],[]]
# test_reward = 0
# test_evareward = 0



# evaluate agent
def evaluate(env, agent):
    global sc_comm,sc_var
    eval_totalCost = []

    for i in range(1):
        env.prepare()
        obs = env.update()
        for o in range(ContainerNumber * NodeNumber):
            flag_temp[o] = 0
            flag[o] = 0
        while True:
            action = agent.predict(obs) 
            obs, cost, done, _, _ = env.step(action)
            eval_totalCost.append(cost)
            if done:
                break
    return eval_totalCost


def main():
    global sc_comm,sc_var 
    env = Env()
    action_dim = ContainerNumber * NodeNumber 
    obs_shape = ContainerNumber * 3 + NodeNumber * (ContainerNumber + 2)   
    model = Model(act_dim=action_dim)
    algorithm = DQN(model, act_dim=action_dim, gamma=GAMMA, lr=LEARNING_RATE)
    agent = Agent(
        algorithm,
        obs_dim=obs_shape,
        act_dim=action_dim,
        e_greed=0.2,  
        e_greed_decrement=1e-6) 
    # load model
    save_path = './dqn_model.ckpt'
    agent.restore(save_path)
    eval_totalCost = evaluate(env, agent)   
    print(eval_totalCost, env.action_queue, env.node_state_queue, env.container_state_queue)
    ResultScore = []
    action_data = env.action_queue[2:]
    sorted_data = sorted(action_data, key=lambda x: x[1])
    for action in sorted_data:
        values = [0] * NodeNumber
        idex = action[0]
        values[idex] = 100
        ResultScore.append(values)
    print(ResultScore)



if __name__ == '__main__':
    main()
