# Branch Predictor Implementation

This solution implements and tests various branch predictors:
- One-bit predictor
- Two-bit predictor
- N-bit predictor (Extra Credit) (10-bit)

## Implementation Details

### One-Bit Predictor
- State: 0 or 1
- Prediction:
  - State 0: Predict not taken (False)
  - State 1: Predict taken (True)
- State Transition:
  - On incorrect prediction: Flip the state
  - On correct prediction: Keep the same state

### Two-Bit Predictor
- State: 0, 1, 2, or 3
- Prediction:
  - States 0-1: Predict not taken (False)
  - States 2-3: Predict taken (True)
- State Transition:
  - On incorrect prediction: Move one step toward the actual outcome
  - On correct prediction: Increase confidence (move toward 0 or 3)

### N-Bit Predictor (Extra Credit)
- State: 0 to 2^n - 1
- Prediction:
  - States 0 to 2^(n-1)-1: Predict not taken (False)
  - States 2^(n-1) to 2^n-1: Predict taken (True)
- State Transition:
  - Similar to two-bit predictor, but with more states

## Test Results
The implementation tests each predictor with two types of branch patterns:
1. Random branch outcomes (50% taken, 50% not taken)
2. Loop-like branch outcomes (behaviors resembling loops in actual code)

## Branch Prediction Analysis

### One-Bit Predictor
The one-bit predictor simply remembers the last branch outcome. When branches have predictable patterns (like in loops), this predictor can do well. It struggles with alternating patterns because it always predicts that the next branch will behave like the previous one.

### Two-Bit Predictor
The two-bit predictor adds "hysteresis" by requiring two consecutive mispredictions to change the prediction direction. This performs better for most real-world code with loops and conditional logic, as it doesn't immediately change its prediction after a single divergence from the pattern.

### N-Bit Predictor
The N-bit predictor extends the two-bit concept with more confidence levels, allowing it to better adapt to complex branch patterns. The higher the value of N, the more "memory" the predictor has of past branch behavior. Although this does seem to round out at higher values of N, it does not seem to be able to predict the outcome of the branch with 100% accuracy.