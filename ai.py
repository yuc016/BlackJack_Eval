import copy
import random

from game import Game, states, BET, WIN_STATE, LOSE_STATE, DRAW_STATE, BLACKJACK_STATE, SIMPLE_STATE, CAN_SPLIT, CAN_DOUBLE, HIT, STAND, DOUBLE, SPLIT

DISCOUNT = 0.97 #This is the gamma value for all value calculations
FAST_LEARN = True

class Agent:
    def __init__(self):
        # For Q-learning values
        self.Q_values = {}      # Dictionary storing the Q-Learning [HIT, STAND] values of each state
        self.double_values = {} # Dictionary storing the DOUBLE values of each state
        self.split_values = {}  # Dictionary storing the SPLIT values of each state
        self.N_Q = {}           # Dictionary storing the number of samples of each state

        self.hitQ = 0
        self.standQ = 0
        self.doubleQ = 0
        self.splitQ = 0

        # Initialization of the values
        for s in states:
            self.Q_values[s] = [0,0] # First element is the Q value of "Hit", second element is the Q value of "Stand"
            self.double_values[s] = 70
            self.split_values[s] = 70
            self.N_Q[s] = 0

        self.simulator = Game()

    # Learning rate for Q-Learning
    @staticmethod
    def alpha(n):
        return 10.0/(9 + n)

    # Explore vs. Exploit probability
    @staticmethod
    def epsilon(n):
        return 1
        return 40000/(39999 + n)
    
    def Q_run(self, num_simulation, tester=False):
        # Perform num_simulation rounds of simulations of gameplay
        for simulation in range(num_simulation):
            self.simulator.reset()

            state = self.simulator.state
            reward = self.simulator.check_reward()
            while True:
                epsilon = self.epsilon(self.N_Q[state])
                action = self.pick_action(state, epsilon)
                n_state, n_reward = self.simulator.simulate_one_step(action)
                self.N_Q[state] += 1
                if n_state == None:
                    self.Q_values[state][action] += (reward - self.Q_values[state][action]) * self.alpha(self.N_Q[state])
                    break
                else:
                    sample = reward + DISCOUNT * max(self.Q_values[n_state])
                    self.Q_values[state][action] += (sample - self.Q_values[state][action]) * self.alpha(self.N_Q[state])
                reward = n_reward
                state = n_state
            
            if FAST_LEARN and simulation % (num_simulation / 10) == 0:
                print(simulation * 100 / num_simulation, "%")

        if SIMPLE_STATE:
            for s in states:
                self.double_values[s] = 70
                self.double_values[s] = self.calculate_double_value(s)
                self.split_values[s] = 70
                # Split happens when sum is even and if sum is 2, dealer has ace
                if int(s[0]) % 2 == 0 and int(s[1]) != 1 and int(s[0]) > 2 or int(s[0]) == 2 and int(s[1]) == 1:
                    self.split_values[s] = self.calculate_split_value(s)

    def pick_action(self, s, epsilon):
        if random.random() < epsilon:
            # Make random choice (explore)
            return random.randint(0,1)
        else:
            # Make rational choice (exploit)
            if self.Q_values[s][HIT] > self.Q_values[s][STAND]:
                return HIT
            return STAND

    def autoplay_decision(self, state, can_double, can_split):
        return self.ai_decision(state, can_double, can_split)

    def ai_decision(self, state, can_double, can_split):
        self.doubleQ = float("-inf")
        self.splitQ = float("-inf")
        if can_double:
            if SIMPLE_STATE:
                self.doubleQ = self.double_values[state]
            else:
                self.doubleQ = self.calculate_double_value(state)
        if can_split:
            if SIMPLE_STATE:
                self.splitQ = self.calculate_split_value(state)
            else:
                raise NotImplemented

        self.hitQ, self.standQ = self.Q_values[state][HIT], self.Q_values[state][STAND]

        actions = {HIT:self.hitQ, STAND:self.standQ, DOUBLE:self.doubleQ, SPLIT:self.splitQ}
        return max(actions, key=actions.get)
    
    def random_decision(self):
        if random.random() < 0.5:
            return HIT
        return STAND
    
    def simple_decision(self, sum):
        if sum < 17:
            return HIT
        return STAND

    def print_decision_value(self):
        print("HIT: ", self.hitQ)
        print("STAND: ", self.standQ)
        print("DOUBLE: ", self.doubleQ)
        print("SPLIT: ", self.splitQ)

    # Inaccuacy: Consider 21 a win, but can still be a push
    def calculate_double_value(self, state):
        if state == WIN_STATE or state == LOSE_STATE or state == DRAW_STATE or state == BLACKJACK_STATE:
            return 0

        # If double value for the state is previously calculated and saved
        if self.double_values[state] != 70:
            return self.double_values[state]

        sum = 0
        count = 0

        if SIMPLE_STATE:
            new_state = (state[0] + 1, 1, *(state[2:]))
            if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                sum += BET * 1.8
            # stand value of the next state
            else:
                sum += self.Q_values[new_state][STAND] * 2

            for i in range(2, 14):
                i = min(10, i)
                new_state = (state[0] + i, *(state[1:]))
                if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                    sum += BET * 1.8
                elif new_state in states:
                    sum += self.Q_values[new_state][STAND] * 2
                # busted
                else:
                    sum -= BET * 2

            return sum / 13

        # Iterate through each possible next card value
        # Ace
        if state[4] == 1:
            new_state = (state[0] + 1, 1, *(state[2:]))
            # 21 considered win
            if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                sum += BET * 2
            # stand value of the next state
            else:
                sum += self.Q_values[new_state][STAND] * 2
            count += 1
            

        # 2-9
        for i in range(5, len(state) - 1):
            if state[i] == 1:
                new_state = (state[0] + i-3, *(state[1:]))
                if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                    sum += BET * 2
                elif new_state in states:
                    sum += self.Q_values[new_state][STAND] * 2
                # busted
                else:
                    sum -= BET * 2
                count += 1
            
        
        # 10-valued cards
        if state[13] == 1:
            for x in range(4):
                new_state = (state[0] + 10, *(state[1:]))
                if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                    sum += BET * 2
                elif new_state in states:
                    sum += self.Q_values[new_state][STAND] * 2
                else:
                    sum -= BET * 2
                count += 1

        if count == 0:
            return 0

        self.double_values[state] = sum / count
        return self.double_values[state]

    # Inaccuacy: Consider 21 a win, but can still be a push
    def calculate_split_value(self, state):
        if state == WIN_STATE or state == LOSE_STATE or state == DRAW_STATE or state == BLACKJACK_STATE:
            return 0

        # If split value for the state is previously calculated and saved
        if self.split_values[state] != 70:
            return self.split_values[state]

        sum = 0

        if SIMPLE_STATE:
            new_state = (state[0] / 2 + 1, 1, state[2])
            if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                sum += BET * 0.8
            # max value of the next state
            else:
                if CAN_DOUBLE:
                    sum += max(self.Q_values[new_state][STAND], 
                            self.Q_values[new_state][HIT], 
                            self.calculate_double_value(new_state))
                else:
                    sum += max(self.Q_values[new_state][STAND], 
                            self.Q_values[new_state][HIT])

            for i in range(2, 14):
                i = min(10, i)
                new_state = (state[0] / 2 + i, *(state[1:]))
                if new_state[0] == 21 or (new_state[0] == 11 and new_state[1] == 1):
                    sum += BET * 0.8
                elif new_state in states:
                    if CAN_DOUBLE:
                        sum += max(self.Q_values[new_state][STAND], 
                                self.Q_values[new_state][HIT], 
                                self.calculate_double_value(new_state))
                    else:
                        sum += max(self.Q_values[new_state][STAND], 
                                self.Q_values[new_state][HIT])
                else:
                    sum -= BET

            return sum / 13 * 2
        
        raise ErrorNotImplmented

    def save(self, filename):
        with open(filename, "w") as file:
            # for table in [self.MC_values, self.TD_values, self.Q_values, self.S_MC, self.N_MC, self.N_TD, self.N_Q]:
            for table in [self.Q_values, self.double_values, self.split_values, self.N_Q]:
                for key in table:
                    key_str = str(key).replace(" ", "")
                    entry_str = str(table[key]).replace(" ", "")
                    file.write(f"{key_str} {entry_str}\n")
                file.write("\n")

    def load(self, filename):
        with open(filename) as file:
            text = file.read()
            Q_values_text, doubleQ_text, splitQ_text, NQ_text, _ = text.split("\n\n")
            
            def extract_key(key_str):
                return tuple([int(x) for x in key_str[1:-1].split(",")])
            
            for table, text in zip(
                [self.Q_values, self.double_values, self.split_values, self.N_Q], 
                [Q_values_text, doubleQ_text, splitQ_text, NQ_text]
            ):
                for line in text.split("\n"):
                    key_str, entry_str = line.split(" ")
                    key = extract_key(key_str)
                    table[key] = eval(entry_str)

    @staticmethod
    def tester_print(i, n, name):
        print(f"\r  {name} {i + 1}/{n}", end="")
        if i == n - 1:
            print()

    def calculate_bet_amount(self, true_count):
        if true_count < 0:
            return 0
        # return true_count
        return min(100, true_count * 10 + 25)