import copy
import random

# -- Configurations --
SIMPLE_STATE = True
STAND_SOFT_17 = False
CAN_SPLIT = True
CAN_DOUBLE = True
BLACKJACK_PAYRATE = 1.5
BET = 1
# -- Configurations --

HIT = 0
STAND = 1
DOUBLE = 2
SPLIT = 3

ranks = [
    "ace",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "jack",
    "queen",
    "king",
]
suits = [
    "clubs",
    "spades",
    "diamonds",
    "hearts",
]

NUM_DECK = 4

cards = []
for rank in ranks:
    for suit in suits:
        cards.append((rank, suit))

'''
    State representation: (user_sum, user_has_Ace, dealer_first)
        - user_sum: sum of user's cards' value, where A counts as 1. Possible values are 2 to 20
        - user_has_Ace: whether user has at least one Ace. Possible values are 0 and 1
        - dealer_first: the first card's value of dealer, where A counts as 1. Possible values are 1 to 10
'''
# Special states
WIN_STATE = (0,0,1)
LOSE_STATE = (0,0,0)
DRAW_STATE = (1,0,1)
BLACKJACK_STATE = (1,1,1)

states = []
states.append(WIN_STATE)
states.append(LOSE_STATE)
states.append(DRAW_STATE)
states.append(BLACKJACK_STATE)
for user_sum in range(2,21):
    for user_has_Ace in range(0,2):
        for dealer_first in range(1,11):
            if SIMPLE_STATE:
                states.append((user_sum, user_has_Ace, dealer_first))
            else:
                for n in range(2**10):
                    s = (user_sum, user_has_Ace, dealer_first,
                        n >> 9 & 0x1,
                        n >> 8 & 0x1,
                        n >> 7 & 0x1,
                        n >> 6 & 0x1,
                        n >> 5 & 0x1,
                        n >> 4 & 0x1,
                        n >> 3 & 0x1,
                        n >> 2 & 0x1,
                        n >> 1 & 0x1,
                        n & 0x1)
                    states.append(s)

def get_amt(card):
    rank, _ = card
    if rank == "ace":
        return 1
    elif rank in ["jack", "queen", "king"]:
        return 10
    # else    
    return int(rank)

class Game:
    def __init__(self):
        self.winNum = 0
        self.loseNum = 0
        self.drawNum = 0
        self.blackjackNum = 0
        self.gameNum = 0
        self.profit = 0
        self.maxProfit = 0
        self.maxLoss = 0
        self.amountPlayed = 0
        self.bet = 0
        self.playing_cards = []
        self.card_counts = [0] * 10
        self.doubledown = False
        self.stand = False
        self.user_sum = 0
        self.userCards = []
        self.dealCards = []
        self.user_cards = 0
        self.dealer_first = None
        self.state = None
        self.user_A = 0
        self.__dealer_A = 0
        self.__dealer_sum = 0
        self.reset()

    def reset(self):
        # Restart the game
        self.userCards = []
        self.dealCards = []
        self.stand = False
        self.bet = BET
        self.doubledown = False
        self.init_cards(self.userCards, self.dealCards)

    # Generate new decks of playing cards
    def new_decks(self):
        # print("New deck..")
        self.playing_cards = []
        for rank in ranks:
            for suit in suits:
                for i in range(NUM_DECK):
                    self.playing_cards.append((rank, suit))
        
        for i in range(9):
            self.card_counts[i] = 4 * NUM_DECK
        self.card_counts[9] = 16 * NUM_DECK # Ten's value cards

    def remove_rank(self, rank_num):
        rank = ""
        if rank_num == 1:
            rank = "ace"
        else:
            rank = str(rank_num)

        to_remove = []
        if rank == "10":
            for r in ["jack", "queen", "king", "10"]:
                for suit in suits:
                    to_remove.append((r, suit))
        else:
            for suit in suits:
                to_remove.append((rank, suit))

        for card in to_remove:
            if card in self.playing_cards:
                self.playing_cards.remove(card)
                self.update_card_count(card)


    def update_card_count(self, card_removed):
        rank = card_removed[0]
        if rank == "ace":
            self.card_counts[0] -= 1
        elif rank == "jack" or rank == "queen" or rank == "king":
            self.card_counts[9] -= 1
        else:
            self.card_counts[int(rank)-1] -= 1
    
    def cards_sufficient(self):
        return len(self.playing_cards) > NUM_DECK * 52 // 6
        
    def init_cards(self, uList, dList):

        if not self.cards_sufficient():
            self.new_decks()

        # Generates two cards for dealer and user, one at a time for each.
        # Returns if card is Ace and the total amount of the cards per person.
        user_A = 0
        dealer_A = 0

        card_1, card_A = self.gen_card(uList)
        user_A += card_A
        card_2, card_A = self.gen_card(dList)
        dealer_A += card_A
        card_3, card_A = self.gen_card(uList)
        user_A += card_A
        card_4, card_A = self.gen_card(dList)
        dealer_A += card_A

        # Number of user's cards
        self.user_cards = 2
        # Sum of user's cards
        self.user_sum = get_amt(card_1) + get_amt(card_3)
        # Number of user's Aces
        self.user_A = user_A
        # Sum of dealer's cards (including hidden one)
        self.__dealer_sum = get_amt(card_2) + get_amt(card_4)
        # Number of all dealer's Aces (including hidden one)
        self.__dealer_A = dealer_A
        # The first card of dealer
        self.dealer_first = get_amt(card_2)

        # The state includes only information visible to the player
        self.state = self.make_state()

    def game_over(self):
        return self.stand or self.state == WIN_STATE or self.state == LOSE_STATE or self.state == DRAW_STATE or self.state == BLACKJACK_STATE

    def gen_card(self, xList):
        # Generate and remove an card to append to xList.
        # Return the card, and whether the card is an Ace
        cA = 0
        card = random.choice(self.playing_cards)
        self.playing_cards.remove(card)
        self.update_card_count(card)
        xList.append(card)
        if card[0] == 'ace':
            cA = 1
        return card, cA

    def make_state(self):
        # Calculate actual hands after counting A as 11 as needed
        actual_user_sum, user_A_active = self.calculate_hand(self.user_sum, self.user_A)
        actual_dealer_sum, _ = self.calculate_hand(self.__dealer_sum, self.__dealer_A)

        # If user gets 21, user wins unless dealer also gets 21
        dealer_bj = len(self.dealCards) == 2 and actual_dealer_sum == 21
        player_bj = self.user_cards == 2 and self.user_A
        if actual_user_sum == 21:
            # Call a stand for player, and don't make state again
            self.act_stand(False) 
            if player_bj:
                if dealer_bj:
                    return DRAW_STATE
                else:
                    return BLACKJACK_STATE
            else:
                if not actual_dealer_sum == 21:
                    return WIN_STATE
                else:
                    return DRAW_STATE
        
        if dealer_bj:
            return LOSE_STATE
        
        # If user busts, user loses
        if actual_user_sum > 21:
            return LOSE_STATE
        
        # If user stands, check results
        if self.stand:
            # User wins if dealer busts or dealer gets smaller results
            if actual_dealer_sum > 21 or actual_user_sum > actual_dealer_sum:
                return WIN_STATE
            elif actual_dealer_sum == actual_user_sum:
                return DRAW_STATE
            return LOSE_STATE

        # Otherwise, return the state representation (see line 36 for explaination)
        if self.user_A:
            user_has_Ace = 1
        else:
            user_has_Ace = 0
        
        has_card = [0] * 10
        for i in range(10):
            if self.card_counts[i] > 0:
                has_card[i] = 1

        if SIMPLE_STATE:
            return (self.user_sum, user_has_Ace, self.dealer_first)
        return (self.user_sum, user_has_Ace, self.dealer_first, *has_card)

    @staticmethod
    def calculate_hand(card_sum, card_A):
        A_active = 0
        if card_A > 0 and card_sum + 10 <= 21:
            A_active = 1
        
        actual_sum = card_sum + A_active * 10
        return actual_sum, A_active
        
    def act_hit(self):
        # Give player a card
        card, cA = self.gen_card(self.userCards)
        self.user_A += cA
        self.user_sum += get_amt(card)
        self.user_cards += 1
        
        # Make state based on the updated user cards
        self.state = self.make_state()

    def act_stand(self, will_make_state=True):
        # H17 rule: if dealer's cards contain A's, there is always one A that's counted as 11
        actual_dealer_sum, dealer_A_active = self.calculate_hand(self.__dealer_sum, self.__dealer_A)
        actual_user_sum, _ = self.calculate_hand(self.user_sum, self.user_A)

        if actual_dealer_sum != 21:
            # Dealer stops when it reaches 17
            # while actual_dealer_sum < actual_user_sum and actual_dealer_sum < 17:
            while True:
                if STAND_SOFT_17:
                    if actual_dealer_sum == 17 and not dealer_A_active:
                        break
                if actual_dealer_sum >= 17:
                    break
                card, cA = self.gen_card(self.dealCards)
                self.__dealer_A += cA
                self.__dealer_sum += get_amt(card)
                actual_dealer_sum, dealer_A_active = self.calculate_hand(self.__dealer_sum, self.__dealer_A)
        
        # Make state based on the updated cards
        self.stand = True
        if will_make_state:
            self.state = self.make_state()

    def act_double(self):
        if self.can_double():
            self.bet *= 2
            self.doubledown = True
            self.act_hit()
            if not self.game_over():
                self.act_stand()

    def act_split(self):
        if self.can_split():
            self.user_sum = get_amt(self.userCards[0])
            self.user_cards -= 1
            self.userCards.pop()
            self.state = self.make_state()

    def can_double(self):
        if CAN_DOUBLE and self.doubledown == True and len(self.userCards) == 2:
            return False
        return True
    
    def can_split(self):
        if CAN_SPLIT and len(self.userCards) == 2 and self.userCards[0][0] == self.userCards[1][0]:
            return True
        return False
    
    def check_reward(self):
        if not self.game_over():
            return 0
        if self.state == BLACKJACK_STATE:
            return BLACKJACK_PAYRATE
        if self.state == WIN_STATE:
            return 1
        if self.state == DRAW_STATE:
            return 0   
        return -1

    def update_stats(self):
        self.gameNum += 1
        self.amountPlayed += self.bet
        if self.state == WIN_STATE:
            self.winNum += 1
            self.profit += self.bet
        elif self.state == BLACKJACK_STATE:
            self.blackjackNum += 1
            self.profit += BLACKJACK_PAYRATE * BET
        elif self.state == DRAW_STATE:
            self.drawNum += 1
        elif self.state == LOSE_STATE:
            self.loseNum += 1
            self.profit -= self.bet
        
        if self.profit > self.maxProfit:
            self.maxProfit = self.profit
        if self.profit < self.maxLoss:
            self.maxLoss = self.profit
    
    def simulate_one_step(self, action):
        # If the current state is already terminal, return None
        if self.game_over():
            return None, self.check_reward()
        
        # Perform action based on the parameter
        if action == HIT:
            self.act_hit()
        elif action == STAND:
            self.act_stand()

        return self.state, self.check_reward()

    def print_counts(self):
        print(self.card_counts)

    def sync(self, game):
        self.loseNum = game.loseNum
        self.drawNum = game.drawNum
        self.winNum = game.winNum
        self.loseNum = game.loseNum
        self.drawNum = game.drawNum
        self.blackjackNum = game.blackjackNum
        self.gameNum = game.gameNum
        self.profit = game.profit
        self.amountPlayed = game.amountPlayed
        self.playing_cards = game.playing_cards
        self.card_counts = game.card_counts
        self.dealCards = game.dealCards
        self.__dealer_sum = game.__dealer_sum
        self.__dealer_A = game.__dealer_A