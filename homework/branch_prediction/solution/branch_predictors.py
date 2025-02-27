from random import paretovariate
from random import random

def next_branch_outcome_loop():
    alpha = 2
    outcome = paretovariate(alpha)
    outcome = outcome > 2
    return outcome

def next_branch_outcome_random():
    outcome = random()
    outcome = outcome > 0.5
    return outcome

class Predictor:
    
    def __init__(self):
        self.state = 0
    
    def next_predict(self):
        """
        Use this method to return the prediction based off of the current
        state.
        """
        raise NotImplementedError("Implement this method")
        
    def incorrect_predict(self):
        """
        Use this method to set the next state if an incorrect predict
        occurred. (self.state = next_state)
        """
        raise NotImplementedError("Implement this method")
        
    def correct_predict(self):
        """
        Use this method to set the next state if an incorrect predict
        occurred. (self.state = next_state)
        """
        raise NotImplementedError("Implement this method")
    
class OneBitPredictor(Predictor):
    
    def next_predict(self):
        ## If state is 0, predict not taken (False)
        ## If state is 1, predict taken (True)
        return bool(self.state)
        
    def incorrect_predict(self):
        ## Flip the state (0 -> 1 or 1 -> 0) on incorrect prediction
        self.state = 1 - self.state
        
    def correct_predict(self):
        ## Keep the same state on correct prediction
        pass

class TwoBitPredictor(Predictor):
    
    def next_predict(self):
        ## States 0-1 predict not taken, 2-3 predict taken
        return self.state >= 2
        
    def incorrect_predict(self):
        ## Move state toward the opposite prediction, but don't immediately switch
        ## For incorrect prediction, move one step toward the actual outcome
        if(self.next_predict()): 
            self.state = max(0, self.state - 1)
        else: 
            self.state = min(3, self.state + 1)
        
    def correct_predict(self):
        ## Increase confidence in current prediction
        if(self.next_predict()): 
            self.state = min(3, self.state + 1)
        else: 
            self.state = max(0, self.state - 1)

class NBitPredictor(Predictor):
    
    def __init__(self, n=3):
        super().__init__()
        self.n = n
        self.max_state = (1 << n) - 1  ## 2^n - 1
        self.threshold = 1 << (n - 1)  ## 2^(n-1)
    
    def next_predict(self):
        ## If state is >= threshold, predict taken
        ## Otherwise predict not taken
        return self.state >= self.threshold
        
    def incorrect_predict(self):
        ## Move state toward the opposite prediction
        if(self.next_predict()): 
            self.state = max(0, self.state - 1)
        else: 
            self.state = min(self.max_state, self.state + 1)
        
    def correct_predict(self):
        ## Increase confidence in current prediction
        if(self.next_predict()): 
            self.state = min(self.max_state, self.state + 1)
        else: 
            self.state = max(0, self.state - 1)

def test_predictor(predictor, branch_outcome_func, num_iterations=10000):
    """
    Test a predictor with a branch outcome function.
    Returns the prediction accuracy.
    """
    correct_predictions = 0
    
    for _ in range(num_iterations):
        prediction = predictor.next_predict()
        
        actual_outcome = branch_outcome_func()
        
        if(prediction == actual_outcome):
            correct_predictions += 1
            predictor.correct_predict()
        else:
            predictor.incorrect_predict()

    accuracy = correct_predictions / num_iterations
    return accuracy

def main():
    one_bit_random = OneBitPredictor()
    one_bit_random_accuracy = test_predictor(one_bit_random, next_branch_outcome_random)
    print(f"One Bit Predictor - Random Branch Accuracy: {one_bit_random_accuracy:.4f}")

    one_bit_loop = OneBitPredictor()
    one_bit_loop_accuracy = test_predictor(one_bit_loop, next_branch_outcome_loop)
    print(f"One Bit Predictor - Loop Branch Accuracy: {one_bit_loop_accuracy:.4f}")
    
    two_bit_random = TwoBitPredictor()
    two_bit_random_accuracy = test_predictor(two_bit_random, next_branch_outcome_random)
    print(f"Two Bit Predictor - Random Branch Accuracy: {two_bit_random_accuracy:.4f}")
    
    two_bit_loop = TwoBitPredictor()
    two_bit_loop_accuracy = test_predictor(two_bit_loop, next_branch_outcome_loop)
    print(f"Two Bit Predictor - Loop Branch Accuracy: {two_bit_loop_accuracy:.4f}")
    
    num_bits = 10

    n_bit_random = NBitPredictor(n=num_bits)
    n_bit_random_accuracy = test_predictor(n_bit_random, next_branch_outcome_random)
    print(f"{num_bits}-Bit Predictor - Random Branch Accuracy: {n_bit_random_accuracy:.4f}")
    
    n_bit_loop = NBitPredictor(n=num_bits)
    n_bit_loop_accuracy = test_predictor(n_bit_loop, next_branch_outcome_loop)
    print(f"{num_bits}-Bit Predictor - Loop Branch Accuracy: {n_bit_loop_accuracy:.4f}")

if(__name__ == "__main__"):
    main() 