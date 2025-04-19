#############################################################
# Author: ee24s053 Karthik B K
# Date: 20 March 2025
#
# This code is heavily modified by c3.7s+t
# This file does not have any commenting for the same reason.
#############################################################

import datetime
import re, sys
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

class Gate:
    def __init__(self, name, gate_type):
        self.name, self.gate_type, self.inputs, self.outputs = name, gate_type, [], []
    
    def add_input(self, gate):
        if gate not in self.inputs:
            self.inputs.append(gate)
            if self not in gate.outputs: gate.outputs.append(self)
    
    def add_output(self, gate):
        if gate not in self.outputs:
            self.outputs.append(gate)
            if self not in gate.inputs: gate.inputs.append(self)

class Net:
    def __init__(self, name, source=None, destinations=None):
        self.name, self.source, self.destinations, self.value = name, source, destinations or [], None
    
    def add_destination(self, gate):
        if gate not in self.destinations: self.destinations.append(gate)
    
    def set_source(self, gate):
        self.source = gate

class Circuit:
    def __init__(self):
        self.gates, self.nets, self.inputs, self.outputs = {}, {}, [], []
        self.gate_order = []
        
    def visualize_dag(self, output_file=None):
        G = nx.DiGraph()
        for gate_name, gate in self.gates.items():
            G.add_node(gate_name, type=gate.gate_type)
        for gate_name, gate in self.gates.items():
            for output_gate in gate.outputs:
                G.add_edge(gate_name, output_gate.name)
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue')
        nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='->', arrowsize=15)
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
        plt.title('Circuit DAG Visualization', fontsize=15)
        plt.axis('off')
        if output_file:
            plt.savefig(output_file, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            return output_file
        else:
            plt.tight_layout()
            plt.show()
            return None
    
    def add_gate(self, gate):
        self.gates[gate.name] = gate
        if gate.name not in self.gate_order:
            self.gate_order.append(gate.name)
    
    def add_net(self, net): self.nets[net.name] = net
    
    def connect(self, source_gate_name, dest_gate_name, net_name=None):
        source_gate, dest_gate = self.gates.get(source_gate_name), self.gates.get(dest_gate_name)
        if not source_gate or not dest_gate: raise ValueError(f"Cannot connect: gate not found")
        
        net_name = net_name or f"{source_gate_name}_to_{dest_gate_name}"
        if net_name not in self.nets:
            net = Net(net_name, source_gate, [dest_gate])
            self.add_net(net)
        else:
            net = self.nets[net_name]
            net.set_source(source_gate)
            net.add_destination(dest_gate)
        
        source_gate.add_output(dest_gate)
        dest_gate.add_input(source_gate)
        return net
    
    def set_input_gates(self, gate_names): self.inputs = gate_names
    
    def set_output_gates(self, gate_names): self.outputs = gate_names
    
    def get_fanouts(self):
        return {gate_name: [g.name for g in gate.outputs] for gate_name, gate in self.gates.items()}
    
    def get_longest_paths(self):
        sources = [gn for gn, g in self.gates.items() if not g.inputs]
        sinks = [gn for gn, g in self.gates.items() if not g.outputs]
        longest_paths, max_length = [], 0
        
        def find_paths(current, path, visited):
            nonlocal longest_paths, max_length
            visited.add(current); path.append(current)
            
            if current in sinks:
                path_length = len(path)
                if path_length > max_length: max_length, longest_paths = path_length, [path.copy()]
                elif path_length == max_length: longest_paths.append(path.copy())
            
            for next_gate in self.gates[current].outputs:
                if next_gate.name not in visited: find_paths(next_gate.name, path, visited)
            
            path.pop(); visited.remove(current)
        
        for source in sources: find_paths(source, [], set())
        return longest_paths, max_length

def parse(file_contents):
    circuit = Circuit()
    patterns = {
        'input': re.compile(r'input\s+([^;]+);'),
        'output': re.compile(r'output\s+([^;]+);'),
        'wire': re.compile(r'wire\s+([^;]+);'),
        'gate': re.compile(r'(not|nand|nor|xor|and|or|xnor)\s+(\w+)\s*\(([^)]+)\);', re.MULTILINE)
    }
    
    inputs = [inp.strip() for inp in patterns['input'].search(file_contents).group(1).split(',')] if patterns['input'].search(file_contents) else []
    outputs = [out.strip() for out in patterns['output'].search(file_contents).group(1).split(',')] if patterns['output'].search(file_contents) else []
    wires = [wire.strip() for wire in patterns['wire'].search(file_contents).group(1).split(',')] if patterns['wire'].search(file_contents) else []
    
    for signal_name in inputs + outputs + wires: circuit.add_net(Net(signal_name))
    
    for gate_match in patterns['gate'].finditer(file_contents):
        gate_type, gate_name = gate_match.group(1).upper(), gate_match.group(2)
        if not any(gate_name.lower().startswith(prefix) for prefix in ['nand', 'nor', 'not', 'xor', 'and', 'or', 'xnor']): continue
            
        ports = [port.strip() for port in gate_match.group(3).split(',')]
        output_port, input_ports = ports[0], ports[1:]
        
        gate = Gate(gate_name, gate_type)
        circuit.add_gate(gate)
        
        output_net = circuit.nets.get(output_port) or Net(output_port)
        if output_port not in circuit.nets: circuit.add_net(output_net)
        output_net.set_source(gate)
        
        for input_port in input_ports:
            input_net = circuit.nets.get(input_port) or Net(input_port)
            if input_port not in circuit.nets: circuit.add_net(input_net)
            input_net.add_destination(gate)
        
        if output_port in outputs and circuit.gates.get(output_port): circuit.connect(gate_name, output_port)
    
    for net_name, net in circuit.nets.items():
        if net.source and net.destinations:
            source_gate = net.source
            for dest_gate in net.destinations:
                if source_gate.name != dest_gate.name:
                    is_gate = lambda g: any(g.name.lower().startswith(p) for p in ['nand', 'nor', 'not', 'xor', 'and', 'or', 'xnor'])
                    if is_gate(source_gate) and is_gate(dest_gate): circuit.connect(source_gate.name, dest_gate.name, net_name)
    
    circuit.set_input_gates(inputs)
    circuit.set_output_gates(outputs)
    return circuit

def analyze_circuit(ckt):
    print(f"This file is automatically generated by Karthik's verilog parser on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nCircuit Analysis:\n=================")
    
    print("\nGates and Fanouts:")
    print("----------------")
    def get_gate_number(gate_name):
        try:
            parts = gate_name.split('_')
            if len(parts) < 2:
                return float('inf')
                
            num_part = parts[1]
            return int(num_part)
        except (IndexError, ValueError):
            return float('inf')
    
    fanouts = ckt.get_fanouts()
    for gate_name in sorted(fanouts.keys(), key=get_gate_number):
        gate_fanouts = fanouts[gate_name]
        print(f"Gate: {gate_name}\tFanouts: {', '.join(sorted(gate_fanouts, key=get_gate_number)) if gate_fanouts else 'None'}")

    print("\nLongest Paths:")
    print("-------------")
    longest_paths, max_length = ckt.get_longest_paths()
    
    if longest_paths:
        print(f"  Maximum path length: {max_length} nodes")
        print("  Longest paths:")
        def get_path_priority(path):
            if not path: return float('inf')
            return get_gate_number(path[0])
        
        sorted_paths = sorted(longest_paths, key=get_path_priority)
        for i, path in enumerate(sorted_paths):
            print(f"    Path {i+1}: {' -> '.join(path)}")
    else: print("  No paths found in the circuit.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error: Please provide a netlist file as an argument")
        sys.exit(1)
    
    try:
        with open(sys.argv[1], 'r') as f: file_contents = f.read()
        circuit = parse(file_contents)
        
        base_filename = sys.argv[1].split('.')[0]
        output_file = f"{base_filename}_dag.png"
        
        try:
            circuit.visualize_dag(output_file)
            print(f"DAG visualization saved to: {output_file}")
        except:
            pass
        
        analyze_circuit(circuit)
    except FileNotFoundError: print(f"Error: File '{sys.argv[1]}' not found"); sys.exit(1)
    except Exception as e: print(f"Error: {e}"); sys.exit(1)