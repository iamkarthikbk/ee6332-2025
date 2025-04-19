import cvxpy as cp
import numpy as np

# Number of gates
N = 6

# Gate sizing variables (must be positive)
gate_sizes = cp.Variable(N, pos=True)

# Variable for total path delay (must be positive)
my_T = cp.Variable(pos=True)

# Logical and parasitic efforts (all ones)
g = [1] * N
p = [1] * N

# Load capacitance and intrinsic delay
c_load = 100
tau = 5

gate_size_max = 64

# Constraints
constraints = []
# Path delay constraint (expanded as per the GPkit code)
constraints.append(my_T >=
    (g[1] * gate_sizes[1] / gate_sizes[0]) + p[0] +
    (g[2] * gate_sizes[2] / gate_sizes[1]) + p[1] +
    (g[3] * gate_sizes[3] / gate_sizes[2]) + p[2] +
    (g[4] * gate_sizes[4] / gate_sizes[3]) + p[3] +
    (g[5] * gate_sizes[5] / gate_sizes[4]) + p[4] +
    (c_load / gate_sizes[5]) + p[5]
)
# First gate is minimum size
constraints.append(gate_sizes[0] == 1)
# Min/max gate size
constraints += [gate_sizes[i] >= 1 for i in range(N)]
constraints += [gate_sizes[i] <= gate_size_max for i in range(N)]

# Objective: minimize my_T (the path delay)
prob = cp.Problem(cp.Minimize(my_T), constraints)
prob.solve(gp=True)

# Extract results
T_wall = my_T.value
gate_sizes_val = gate_sizes.value

print(f'T_wall = {round(T_wall, 2)}')
print(f'T_wall (ps) = {round(T_wall * tau, 2)}')
print(f'Gate Sizes: {list(np.round(gate_sizes_val, 4))}')
